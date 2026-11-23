"""Line-delimited progress on stdout; optional UTF-8 JSON handoff on disk."""

import argparse
import json
from pathlib import Path
import sys

from ai import api_config, draft_program
from chat import converse, interpret
from inputs import DesignError, boundary_from, read_brief, validate_program
from models import ROOT, read_vocabulary


def read_object(path):
    result = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(result, dict):
        raise DesignError(f"{path.name} must contain one JSON object")
    return result


def emit(value):
    print(json.dumps(value, ensure_ascii=False, allow_nan=False), flush=True)


def run_request(mode, source, brief, program, allow_api, output=None):
    vocabulary = read_vocabulary()
    state = {}
    if mode == "run":
        state["program"] = validate_program(program, vocabulary["types"])
    else:
        if not isinstance(brief, str) or len(brief) > 16000:
            raise DesignError("Provide task brief text with at most 16,000 characters")
        state["brief"] = brief.strip()
        user_message = source.get("message", "")
        if not isinstance(user_message, str) or len(user_message) > 2000:
            raise DesignError("Provide a chat message with at most 2,000 characters")
        if user_message.strip():
            state["user_message"] = user_message.strip()
    api = api_config(ROOT, requirements=mode == "propose") if allow_api else None
    if mode == "propose" and source.get("boundary") is None and state["brief"]:
        if not api:
            raise DesignError("提取空间清单需要授权使用模型。")
        emit({"kind": "stage", "stage": "task", "status": "running", "tools": ["draft_program"]})
        result = draft_program(api, None, state["brief"], vocabulary, state.get("user_message", ""))
        emit({"kind": "stage", "stage": "task", "status": "awaiting_confirmation", "room_count": len(result["rooms"])})
    else:
        from workflow import execute, result_from
        state["boundary"] = boundary_from(source)
        state = execute(state, vocabulary, api, confirmed=mode == "run", emit=emit)
        result = state["program"] if mode == "propose" else result_from(state)
    if output:
        with output.open("x", encoding="utf-8") as target:
            json.dump(result, target, ensure_ascii=False, allow_nan=False, indent=2)
            target.write("\n")
    if mode == "propose":
        emit({"kind": "result", "status": "draft", "draft": result})
        return 0
    emit({"kind": "result", "status": result["status"], "report": result})
    return 0 if result["layout"] else 2


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("propose", "run", "extract", "chat", "conversation"))
    parser.add_argument("--input", type=Path)
    parser.add_argument("--pipe", action="store_true", help="Read a single UTF-8 request from stdin")
    parser.add_argument("--brief", type=Path, help="Optional user-authorized .docx, .pdf or .txt for propose")
    parser.add_argument("--program", type=Path, help="Reviewed program for run, if not embedded in input")
    parser.add_argument("--allow-api", action="store_true", help="Authorize external API use for the selected inputs")
    parser.add_argument("--out", type=Path, help="Save the draft or final report to a new file")
    args = parser.parse_args(argv)
    if (args.mode == "propose" and args.program) or (args.mode == "run" and args.brief):
        parser.error("--program is for run; --brief is for propose")
    if args.pipe and (args.input or args.brief or args.program or args.out):
        parser.error("--pipe does not accept file options")
    if not args.pipe and (args.mode in ("extract", "chat", "conversation") or not args.input):
        parser.error("Use --input for file mode or --pipe for an in-memory request")
    try:
        if args.out and args.out.exists():
            raise DesignError("The output file already exists; choose a new path")
        if args.pipe:
            source = json.load(sys.stdin)
            if not isinstance(source, dict):
                raise DesignError("The backend request must be a JSON object")
            if args.mode == "extract":
                path = source.get("path")
                if not isinstance(path, str) or not path.strip():
                    raise DesignError("Choose a local task brief file")
                if source.get("report_progress") is True:
                    emit({"kind": "stage", "stage": "task", "status": "running", "tools": ["read_brief"]})
                brief = read_brief(path)
                if source.get("report_progress") is True:
                    emit({"kind": "stage", "stage": "task", "status": "completed"})
                emit({"kind": "result", "status": "extracted", "brief": brief})
                return 0
            if args.mode in ("chat", "conversation"):
                def chat_config():
                    if not args.allow_api:
                        raise DesignError("Chat interpretation requires approval to use the external API")
                    return api_config(ROOT, requirements=True)

                def publish(chunk):
                    emit({"kind": "text_delta", "text": chunk})

                if args.mode == "conversation":
                    result = converse(chat_config, source, publish)
                else:
                    config = chat_config()
                    emit({"kind": "stage", "stage": "task", "status": "running", "tools": ["读取项目空间清单"]})
                    vocabulary = read_vocabulary()
                    boundary = boundary_from(source)
                    emit({"kind": "stage", "stage": "task", "status": "running", "tools": ["解析清单请求"]})
                    result = interpret(config, boundary, source.get("program"), source.get("message"),
                                       vocabulary, publish)
                    emit({"kind": "stage", "stage": "task", "status": "completed"})
                emit({"kind": "result", "status": result["action"]} | result)
                return 0
            brief = source.get("brief", "")
            program = source.get("program")
        else:
            source = read_object(args.input)
            brief = read_brief(args.brief)
            program = read_object(args.program) if args.program else source.get("program")
        return run_request(args.mode, source, brief, program, args.allow_api, args.out)
    except (OSError, ValueError, RuntimeError) as exc:
        emit({"kind": "error", "status": "failed", "message": str(exc)})
        return 1


if __name__ == "__main__":
    sys.stdin.reconfigure(encoding="utf-8-sig")
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
