"""Exercise business rules, orchestration and the real repository checkpoints."""

from copy import deepcopy
from email.message import Message
from io import BytesIO
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from docx import Document
from pypdf import PdfWriter

from ai import draft_program, suggest_topology
from chat import apply_change, converse
from chat_stream import content_chunks, read_reply
from inputs import DesignError, boundary_from, read_brief, validate_program
from models import read_vocabulary
from review import audit, evaluate
from workflow import execute, result_from


EXAMPLE = Path(__file__).with_name("examples") / "l_shape.json"


def rectangle(xmin, ymin, xmax, ymax):
    return [[xmin, ymin], [xmax, ymin], [xmax, ymax], [xmin, ymax], [xmin, ymin]]


def sample():
    source = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    vocab = read_vocabulary()
    return boundary_from(source), validate_program(source["program"], vocab["types"]), vocab


def evaluation_fixture():
    layout = {
        "rooms": {"A": rectangle(-1, 6, 1, 8), "B": rectangle(1, 1, 3, 3), "C": rectangle(-3, 4, -1, 6)},
        "corridor": rectangle(-1, 0, 1, 6), "entry": [0, 0],
        "centerline": [[0, index] for index in range(1, 6)],
        "doors": [{"pair": ["A", "@corridor"], "line": [[-0.5, 6], [0.5, 6]]},
                  {"pair": ["B", "@corridor"], "line": [[1, 1.5], [1, 2.5]]},
                  {"pair": ["C", "@corridor"], "line": [[-1, 4], [-1, 5]]}],
    }
    program = {
        "rooms": [{"id": key, "name": key, "min_area_m2": 4, "max_area_m2": 4} for key in layout["rooms"]],
        "corridor_width_m": 2, "door_width_m": 1, "required_connections": [],
        "optional_connections": [], "forbidden_connections": [["A", "C"]],
        "sight_target": "A", "patient_route": ["@entry", "B"], "staff_route": ["C", "A"],
    }
    return layout, program


class BackendTests(unittest.TestCase):
    def test_brief_before_boundary_drafts_without_scheduling_geometry(self):
        from run import run_request
        _, program, _ = sample()
        with patch("run.api_config", return_value=("test", "test", "test")), patch(
            "ai.ask_json", return_value=program
        ) as model, patch("run.emit") as emit, patch("workflow.execute") as schedule:
            run_request("propose", {}, "设置诊室与分诊室。", None, True)
        self.assertIsNone(model.call_args.args[2]["boundary_summary"])
        result = emit.call_args.args[0]
        self.assertEqual(result["draft"]["draft_source"], "brief_extraction")
        self.assertEqual(result["draft"]["rooms"][0]["id"], program["rooms"][0]["id"])
        schedule.assert_not_called()

    def test_capability_question_without_api_permission(self):
        for message in ("你可以做什么呢？", "你好！"):
            with self.subTest(message=message):
                process = subprocess.run(
                    [sys.executable, "-X", "utf8", str(EXAMPLE.parents[1] / "run.py"), "conversation", "--pipe"],
                    input=json.dumps({"message": message}), capture_output=True, encoding="utf8", check=True,
                    timeout=15,
                )
                delta, result = map(json.loads, process.stdout.splitlines())
                self.assertEqual(delta, {"kind": "text_delta", "text": result["message"]})
                self.assertEqual(result["action"], "message")
                self.assertIn("房间清单", result["message"])

    def test_conversation_only_sends_chat_text_after_preview(self):
        history = [{"user": "你好", "assistant": "你好呀"}]
        source = {"message": "阿萨", "history": history, "brief": "private", **json.loads(EXAMPLE.read_text(encoding="utf8"))}
        response = {"action": "message", "message": "你想聊什么？"}
        with patch("chat.stream_chat", return_value=response) as model:
            self.assertEqual(converse(lambda: None, source, print), response)
            self.assertEqual(model.call_args.args[2], {"message": "阿萨", "history": history})

    def test_chat_stream_publishes_words_before_final_result(self):
        updates = []

        def response():
            yield "TE"
            yield "XT\r"
            yield "\n这里有"
            self.assertEqual(updates, ["这里有"])
            yield "四间房。"

        result = read_reply(response(), updates.append)
        self.assertEqual(result, {"action": "message", "message": "这里有四间房。"})
        self.assertEqual(updates, ["这里有", "四间房。"])
        updates.clear()
        self.assertEqual(read_reply(['{"action":', '"generate"}'], updates.append), {"action": "generate"})
        self.assertEqual(updates, [])

    def test_unprefixed_conversational_answer_is_plain_text(self):
        chunks = []
        result = read_reply(["你刚才说的是", "儿童门诊。"], chunks.append)
        self.assertEqual(result, {"action": "message", "message": "你刚才说的是儿童门诊。"})
        self.assertEqual(chunks, [result["message"]])
        with self.assertRaises(ValueError):
            read_reply(['{"action":'], chunks.append)

    def test_chat_stream_requires_finished_model_response(self):
        packet = {"choices": [{"index": 0, "delta": {"content": "TEXT\n第一段"}}]}
        data = ("data: " + json.dumps(packet) + "\n\n").encode()
        finished = b'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n'
        for tail in (b"", finished):
            stream = BytesIO(data + tail)
            stream.headers = Message()
            stream.headers["Content-Type"] = "text/event-stream"
            updates = []
            if tail:
                self.assertEqual(read_reply(content_chunks(stream), updates.append)["message"], "第一段")
            else:
                with self.assertRaisesRegex(DesignError, "中断"):
                    read_reply(content_chunks(stream), updates.append)
            self.assertEqual(updates, ["第一段"])

    def test_boundary_rejects_self_intersection_and_accepts_sloped_entrance(self):
        with self.assertRaisesRegex(DesignError, "self-intersection"):
            boundary_from({"boundary": [[0, 0], [3, 3], [0, 3], [3, 0], [0, 0]]})
        sloped = boundary_from({"boundary": [[0, 0], [3, 4], [-1, 7], [-4, 3], [0, 0]], "entrance_edge": 0})
        self.assertEqual(sloped["local_ring"][0], [-2.5, 0])
        self.assertEqual(sloped["summary"]["area_m2"], 25)

    def test_document_extraction_distinguishes_no_brief_from_unreadable(self):
        self.assertEqual(read_brief(None), "")
        with TemporaryDirectory() as directory:
            word_path = Path(directory) / "brief.docx"
            document = Document()
            document.add_paragraph("分诊室")
            document.add_table(rows=1, cols=1).cell(0, 0).text = "8–10 m²"
            document.save(word_path)
            self.assertEqual(read_brief(word_path), "分诊室\n8–10 m²")
            pdf_path = Path(directory) / "blank.pdf"
            writer = PdfWriter()
            writer.add_blank_page(width=100, height=100)
            writer.write(pdf_path)
            with self.assertRaisesRegex(DesignError, "No brief text"):
                read_brief(pdf_path)

    def test_rhino_pipe_extract_returns_one_local_result(self):
        fixture = EXAMPLE.with_name("brief.txt")
        entry = EXAMPLE.parent.parent / "run.py"
        completed = subprocess.run(
            [sys.executable, "-B", "-X", "utf8", str(entry), "extract", "--pipe"],
            input=json.dumps({"path": str(fixture)}, ensure_ascii=False), capture_output=True,
            encoding="utf-8", timeout=30, check=True,
        )
        message = json.loads(completed.stdout)
        self.assertEqual(message["status"], "extracted")
        self.assertIn("分诊室1间", message["brief"])

    def test_chat_adds_one_room_without_changing_confirmed_requirements(self):
        _, program, vocab = sample()
        before = deepcopy(program)
        result = apply_change(program, {"action": "duplicate_room", "room_id": "C01", "count": 1,
                                        "corridor_width_m": 5}, vocab["types"])
        self.assertEqual(result["action"], "revision")
        self.assertEqual(program, before)
        draft = result["draft"]
        self.assertEqual({key: value for key, value in draft.items() if key != "rooms"},
                         {key: value for key, value in before.items() if key != "rooms"})
        self.assertEqual(draft["rooms"][:-1], before["rooms"])
        new_room = draft["rooms"][-1]
        self.assertEqual(new_room["type"], "consultation")
        self.assertEqual([new_room["min_area_m2"], new_room["max_area_m2"]], [12, 16])
        self.assertNotIn(new_room["id"], {room["id"] for room in before["rooms"]})

    def test_chat_cannot_write_or_remove_a_referenced_room(self):
        _, program, vocab = sample()
        for change in ({"action": "write"}, {"action": "remove_room", "room_id": "C01"}):
            with self.subTest(change=change):
                result = apply_change(program, change, vocab["types"])
                self.assertEqual(result["action"], "message")
                self.assertNotIn("draft", result)

    def test_advice_cannot_add_forbidden_edge_or_send_raw_geometry(self):
        boundary, program, _ = sample()
        program["optional_connections"].append(["C01", "S01"])
        prediction = {"access_scores": [{"pair": ["C01", "S01"], "score": 0.99},
                                        {"pair": ["C01", "T01"], "score": 0.4}]}
        response = {"preferred_pairs": [["R2", "R4"], ["R1", "R2"]], "near_entrance": ["R7"]}
        with patch("ai.ask_json", return_value=response) as api:
            advice = suggest_topology(("test", "test", "test"), boundary["summary"], program, prediction)
        self.assertEqual(advice["preferred_pairs"], [["C01", "T01"]])
        self.assertEqual(len(advice["rejected"]), 2)
        data = api.call_args.args[2]
        self.assertEqual(data["eligible_connections"], [{"pair": ["R2", "R1"], "score": 0.4}])
        self.assertNotIn("local_ring", data)
        self.assertNotIn("name", data["rooms"][0])

    def test_boundary_inference_retries_incomplete_draft(self):
        boundary, program, vocab = sample()
        draft_program_data = dict(program, required_connections=[], forbidden_connections=[])
        for invalid in (dict(draft_program_data, corridor_width_m=None),
                        dict(draft_program_data, required_connections=[["C01", "T01"]])):
            with self.subTest(invalid=invalid), patch("ai.ask_json", side_effect=[invalid, draft_program_data]) as api:
                draft = draft_program(("test", "test", "test"), boundary["summary"], "", vocab)
                self.assertEqual(draft["draft_source"], "model_inference")
                self.assertEqual(draft["corridor_width_m"], 2)
                self.assertEqual(draft["required_connections"], [])
                self.assertEqual(api.call_count, 2)
                self.assertIn("validation_feedback", api.call_args.args[2])

    def test_quality_gate_detects_missing_door_and_overlap(self):
        layout, program = evaluation_fixture()
        boundary = {"local_ring": rectangle(-5, 0, 5, 10)}
        self.assertTrue(audit(boundary, program, layout)["passed"])
        layout["doors"].pop()
        layout["rooms"]["C"] = rectangle(1, 1, 3, 3)
        issues = audit(boundary, program, layout)["issues"]
        self.assertIn("overlap", {item["code"] for item in issues})
        self.assertIn({"code": "missing_connection", "pair": ["@corridor", "C"]}, issues)

    def test_visibility_and_flow_come_from_actual_door_geometry(self):
        layout, program = evaluation_fixture()
        report = evaluate(program, layout)
        self.assertEqual(report["visibility"]["status"], "visible")
        self.assertEqual(report["flow_overlap"]["shared_length_m"], 0)
        program["patient_route"] = ["@entry", "A"]
        self.assertGreater(evaluate(program, layout)["flow_overlap"]["shared_length_m"], 0)
        layout["doors"].pop(0)
        report = evaluate(program, layout)
        self.assertEqual(report["visibility"]["status"], "blocked")
        self.assertIn("A", report["unreachable_rooms"])
        self.assertEqual(report["flow_overlap"]["status"], "not_evaluated")

    def test_unconfirmed_draft_stops_before_gcn(self):
        boundary, program, vocab = sample()
        with patch("workflow.infer") as infer:
            events = []
            state = execute({"boundary": boundary, "program": program}, vocab, None, confirmed=False, emit=events.append)
        infer.assert_not_called()
        self.assertNotIn("layout", state)
        self.assertEqual(events[-1]["status"], "awaiting_confirmation")

    def test_two_failed_attempts_leave_no_layout_or_evaluation(self):
        boundary, program, vocab = sample()
        prediction = {"access_scores": [], "layout_boxes_local_m": {}}
        with patch("workflow.infer", return_value=prediction), patch(
            "workflow.generate_layout", side_effect=DesignError("no geometric fit"),
        ) as generate:
            events = []
            state = execute({"boundary": boundary, "program": program}, vocab, None, confirmed=True, emit=events.append)
        self.assertEqual(generate.call_count, 2)
        report = result_from(state)
        self.assertIsNone(report["layout"])
        self.assertIsNone(report["evaluation"])
        self.assertEqual(report["status"], "no_layout_found")
        self.assertNotIn("evaluation", {event["stage"] for event in events})

    def test_genuine_checkpoints_generate_and_audit_l_shaped_example(self):
        boundary, program, vocab = sample()
        program["optional_connections"].extend(program["forbidden_connections"])
        events = []
        state = execute({"boundary": boundary, "program": deepcopy(program)}, vocab, None,
                        confirmed=True, emit=events.append)
        report = result_from(state)
        self.assertEqual(report["status"], "completed", report["attempts"])
        self.assertEqual(report["layout"]["entry"], [9, 0])
        self.assertEqual(report["evaluation"]["room_count"], 4)
        self.assertEqual(report["evaluation"]["unreachable_rooms"], [])
        self.assertEqual(len(report["prediction"]["access_scores"]), 6)
        self.assertEqual(len(report["prediction"]["models"]), 2)
        self.assertNotIn(["C01", "S01"], report["attempts"][-1]["realized_connections"])
        self.assertEqual({item["stage"] for item in events}, {"task", "gcn", "generation", "evaluation"})
        outputs = {event["stage"]: event for event in events if event["status"] == "completed"}
        self.assertEqual({tuple(row["pair"]) for row in outputs["gcn"]["candidates"]},
                         {tuple(pair) for pair in program["optional_connections"]} - {("C01", "S01")})
        self.assertIn({"pair": ["C01", "S01"], "requirement": "forbidden_connections", "door_present": False,
                       "passed": True}, outputs["evaluation"]["connection_checks"])
        self.assertEqual(outputs["generation"]["doors"], report["attempts"][-1]["realized_connections"])
        self.assertEqual(outputs["evaluation"]["routes"]["patient_route"]["endpoints"], program["patient_route"])

    def test_compact_retry_fits_a_larger_inferred_program_without_relaxing_areas(self):
        boundary, _, vocab = sample()
        types_and_areas = [("triage", 10, 14), ("hall", 28, 40), ("consultation", 12, 16),
                           ("treatment", 18, 26), ("staff_support", 10, 16)]
        rooms = [{"id": f"R{index}", "name": room_type, "type": room_type, "min_area_m2": low, "max_area_m2": high}
                 for index, (room_type, low, high) in enumerate(types_and_areas, 1)]
        program = validate_program({"rooms": rooms, "corridor_width_m": 1.5, "door_width_m": 1,
                                    "optional_connections": [[f"R{index}", f"R{index + 1}"] for index in range(1, 5)]},
                                   vocab["types"])
        state = execute({"boundary": boundary, "program": program}, vocab, None, confirmed=True,
                        emit=lambda event: None)
        report = result_from(state)
        self.assertEqual(report["status"], "completed", report["attempts"])
        self.assertEqual(report["evaluation"]["unreachable_rooms"], [])
        for room, item in zip(rooms, report["evaluation"]["rooms"], strict=True):
            self.assertLessEqual(room["min_area_m2"], item["area_m2"])
            self.assertLessEqual(item["area_m2"], room["max_area_m2"])


if __name__ == "__main__":
    unittest.main()
