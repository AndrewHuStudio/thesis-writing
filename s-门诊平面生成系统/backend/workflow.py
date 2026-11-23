"""Coordinate the four stages and publish observable progress."""

from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from langsmith import tracing_context

from ai import draft_program, suggest_topology
from inputs import DesignError
from layout import generate_layout
from models import infer
from review import audit, evaluate


class State(TypedDict, total=False):
    boundary: dict
    brief: str
    user_message: str
    program: dict
    prediction: dict
    advice: dict
    attempts: list
    layout: dict
    evaluation: dict


def events(stage, status, **summary):
    get_stream_writer()({"kind": "stage", "stage": stage, "status": status, **summary})


def build_graph(vocabulary, api):
    def task(state):
        events("task", "running", boundary=state["boundary"]["summary"])
        if "program" in state:
            program = state["program"]
        elif api:
            events("task", "running", tools=["draft_program"])
            program = draft_program(api, state["boundary"]["summary"], state.get("brief", ""), vocabulary,
                                    state.get("user_message", ""))
        else:
            raise DesignError("Drafting requires --allow-api; alternatively supply a confirmed program to run")
        events("task", "completed", room_count=len(program["rooms"]),
               rooms=[{"id": r["id"], "name": r["name"]} for r in program["rooms"]],
               required=program["required_connections"], forbidden=program["forbidden_connections"])
        return {"program": program, "brief": ""}

    def approval(state):
        if interrupt({"kind": "review_required", "room_count": len(state["program"]["rooms"])}) is not True:
            raise DesignError("A confirmed program is needed before running layout")
        return {}

    def gcn(state):
        events("gcn", "running", tools=["access_gcn", "boundary_layout_gcn"])
        prediction = infer(state["boundary"], state["program"], vocabulary)
        advice = {"source": "not_requested", "preferred_pairs": [], "near_entrance": [], "rejected": []}
        if api:
            try:
                events("gcn", "running", tools=["apiyi_layout_advice"])
                advice = suggest_topology(api, state["boundary"]["summary"], state["program"], prediction)
            except DesignError as exc:
                advice.update(source="failed", error=str(exc))
                events("gcn", "degraded", reason=str(exc))
        allowed = {tuple(pair) for pair in state["program"]["optional_connections"]}
        allowed.difference_update(map(tuple, state["program"]["forbidden_connections"]))
        allowed.difference_update(map(tuple, state["program"]["required_connections"]))
        candidates = sorted((row for row in prediction["access_scores"] if tuple(row["pair"]) in allowed),
                            key=lambda row: row["score"], reverse=True)
        prediction["eligible_candidates"] = candidates
        events("gcn", "completed", score_count=len(prediction["access_scores"]), candidates=candidates,
               advice_source=advice["source"])
        return {"prediction": prediction, "advice": advice}

    def generation(state):
        attempts = []
        for attempt in range(2):
            events("generation", "running", attempt=attempt + 1, tools=["corridor_search", "room_placement"])
            try:
                layout = generate_layout(state["boundary"], state["program"], state["prediction"], state["advice"], attempt)
                events("generation", "running", attempt=attempt + 1, tools=["geometry_audit"])
                result = audit(state["boundary"], state["program"], layout)
            except DesignError as exc:
                layout = None
                result = {"passed": False, "issues": [{"code": "search_failed", "detail": str(exc)}]}
            attempts.append(result | {"attempt": attempt + 1})
            if result["passed"]:
                events("generation", "completed", attempt=attempt + 1, room_count=len(layout["rooms"]),
                       doors=result["realized_connections"])
                return {"layout": layout, "attempts": attempts}
            events("generation", "retrying" if attempt == 0 else "failed", issues=result["issues"])
        return {"attempts": attempts}

    def evaluation(state):
        events("evaluation", "running", tools=["room_summary", "route_graph", "sight_line", "flow_overlap"])
        result = evaluate(state["program"], state["layout"])
        result["connection_checks"] = state["attempts"][-1]["connection_checks"]
        events("evaluation", "completed", room_count=result["room_count"],
               connection_checks=result["connection_checks"],
               unreachable_count=len(result["unreachable_rooms"]), routes={key: {
                   field: result[key][field] for field in ("endpoints", "length_m", "status") if field in result[key]
               } for key in ("patient_route", "staff_route")}, unreachable=result["unreachable_rooms"])
        return {"evaluation": result}

    builder = StateGraph(State)
    for name, node in (("task", task), ("approval", approval), ("gcn", gcn),
                       ("generation", generation), ("evaluation", evaluation)):
        builder.add_node(name, node)
    builder.add_edge(START, "task")
    builder.add_edge("task", "approval")
    builder.add_edge("approval", "gcn")
    builder.add_edge("gcn", "generation")
    builder.add_conditional_edges("generation", lambda state: "evaluation" if "layout" in state else END,
                                  ["evaluation", END])
    builder.add_edge("evaluation", END)
    return builder.compile(checkpointer=InMemorySaver())


def execute(state, vocabulary, api, *, confirmed, emit):
    graph = build_graph(vocabulary, api)
    config = {"configurable": {"thread_id": "local-run"}}

    def stream(command):
        for kind, payload in graph.stream(command, config, stream_mode=["custom", "updates"]):
            if kind == "custom":
                emit(payload)
            elif "__interrupt__" in payload:
                emit({"kind": "stage", "stage": "task", "status": "awaiting_confirmation"})

    with tracing_context(enabled=False):
        stream(state)
        if confirmed:
            stream(Command(resume=True))
    return graph.get_state(config).values


def result_from(state):
    frame = state["boundary"]

    def world(point):
        return [round(origin + horizontal * point[0] + vertical * point[1], 8)
                for origin, horizontal, vertical in zip(frame["origin"], frame["axis_x"], frame["axis_y"])]

    def line(points):
        return [world(point) for point in points]

    geometry = state.get("layout")
    result = {
        "schema_version": 1, "status": "completed" if geometry else "no_layout_found", "units": "metres",
        "boundary": frame, "program": state["program"], "prediction": state["prediction"], "advice": state["advice"],
        "attempts": state["attempts"], "layout": None, "evaluation": None,
    }
    if geometry:
        result["layout"] = {"rooms": {room_id: line(ring) for room_id, ring in geometry["rooms"].items()},
                            "corridor": line(geometry["corridor"]), "centerline": line(geometry["centerline"]),
                            "entry": world(geometry["entry"]),
                            "doors": [door | {"line": line(door["line"])} for door in geometry["doors"]]}
        review = state["evaluation"]
        result["evaluation"] = review | {name: review[name] | {"line": line(review[name]["line"])}
                                         for name in ("visibility", "patient_route", "staff_route")
                                         if "line" in review[name]}
        if "shared_lines" in review["flow_overlap"]:
            result["evaluation"]["flow_overlap"] = review["flow_overlap"] | {
                "shared_lines": [line(points) for points in review["flow_overlap"]["shared_lines"]]}
    return result
