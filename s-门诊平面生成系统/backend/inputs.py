"""Read the backend's metre-based design inputs and confirmed space program."""

from itertools import pairwise
from math import dist, isfinite
from pathlib import Path

from shapely.geometry import Polygon


class DesignError(ValueError):
    pass


def number(value, label):
    if type(value) not in (int, float) or not isfinite(value):
        raise DesignError(f"{label} must be a finite number")
    return float(value)


def xy(value):
    if not isinstance(value, list) or len(value) != 2:
        raise DesignError("Each boundary point must be [x, y] in metres")
    return [number(part, "coordinate") for part in value]


def boundary_from(source):
    vertices = source.get("boundary")
    if not isinstance(vertices, list) or not 4 <= len(vertices) <= 101:
        raise DesignError("Provide one closed polyline with 3–100 edges")
    points = [xy(point) for point in vertices]
    if points[0] != points[-1] or any(left == right for left, right in pairwise(points)):
        raise DesignError("The boundary must be closed, without zero-length edges")
    polygon = Polygon(points)
    if not polygon.is_valid or polygon.area <= 0:
        raise DesignError("The boundary must have positive area and no self-intersection")
    edges = list(pairwise(points))
    picked = source.get("entrance_edge")
    edge_index = max(range(len(edges)), key=lambda index: dist(*edges[index])) if picked is None else picked
    if type(edge_index) is not int or not 0 <= edge_index < len(edges):
        raise DesignError("entrance_edge must be a zero-based boundary edge index")
    start, end = edges[edge_index]
    length = dist(start, end)
    origin = [(left + right) / 2 for left, right in zip(start, end)]
    axis_x = [(right - left) / length for left, right in zip(start, end)]
    sign = 1 if polygon.exterior.is_ccw else -1
    axis_y = [-sign * axis_x[1], sign * axis_x[0]]
    local = []
    for point in points:
        delta = [value - offset for value, offset in zip(point, origin)]
        local.append([round(sum(value * axis for value, axis in zip(delta, direction)), 8)
                      for direction in (axis_x, axis_y)])
    xmin, ymin, xmax, ymax = Polygon(local).bounds
    if max(xmax - xmin, ymax - ymin) > 60 or abs(xmin) > 60:
        raise DesignError("The demo supports a single zone with a span of up to 60 m")
    return {
        "local_ring": local, "origin": origin, "axis_x": axis_x, "axis_y": axis_y,
        "entrance_edge": edge_index, "entrance_suggested": picked is None, "entrance_length_m": length,
        "summary": {"area_m2": round(polygon.area, 2), "span_m": [round(xmax - xmin, 2), round(ymax - ymin, 2)],
                    "shape": "concave" if polygon.convex_hull.area - polygon.area > 1e-7 else "convex"},
    }


def pair_key(left, right):
    return tuple(sorted((left, right)))


def relation_set(program, name, ids):
    pairs = program.get(name, [])
    if not isinstance(pairs, list):
        raise DesignError(f"{name} must be a list of ID pairs")
    result = set()
    for pair in pairs:
        if (not isinstance(pair, list) or len(pair) != 2 or
                any(not isinstance(item, str) or item not in ids for item in pair) or pair[0] == pair[1]):
            raise DesignError(f"{name} includes an invalid room pair")
        result.add(pair_key(*pair))
    return sorted(result)


def validate_program(program, types, *, draft=False):
    if not isinstance(program, dict):
        raise DesignError("The program must be a JSON object")
    rooms = program.get("rooms")
    if not isinstance(rooms, list) or not 2 <= len(rooms) <= 12:
        raise DesignError("A demo program must have 2–12 room instances")
    clean_rooms = []
    ids = set()
    for room in rooms:
        if not isinstance(room, dict):
            raise DesignError("Each room must be a JSON object")
        room_id, name, room_type = (room.get(field) for field in ("id", "name", "type"))
        if (not isinstance(room_id, str) or not room_id.strip() or room_id.startswith("@") or
                len(room_id) > 32 or room_id in ids):
            raise DesignError("Room IDs must be unique non-empty strings of up to 32 characters")
        if (not isinstance(name, str) or not name.strip() or not isinstance(room_type, str) or
                room_type not in types or room_type == "corridor"):
            raise DesignError(f"{room_id}: provide a name and a known room type code")
        ids.add(room_id)
        minimum, maximum = room.get("min_area_m2"), room.get("max_area_m2")
        if not draft or minimum is not None:
            minimum = number(minimum, f"{room_id} minimum area")
        if not draft or maximum is not None:
            maximum = number(maximum, f"{room_id} maximum area")
        if ((minimum is not None and minimum <= 0) or (maximum is not None and maximum <= 0) or
                (minimum is not None and maximum is not None and maximum < minimum)):
            raise DesignError(f"{room_id}: area range is invalid")
        clean = dict(id=room_id, name=name.strip(), type=room_type, min_area_m2=minimum, max_area_m2=maximum)
        for key in ("source", "note"):
            if isinstance(room.get(key), str):
                clean[key] = room[key]
        clean_rooms.append(clean)
    result = {"rooms": clean_rooms}
    for key in ("required_connections", "optional_connections", "forbidden_connections"):
        result[key] = [list(pair) for pair in relation_set(program, key, ids)]
    required = {tuple(pair) for pair in result["required_connections"]}
    forbidden = {tuple(pair) for pair in result["forbidden_connections"]}
    if required & forbidden:
        raise DesignError("The same room pair is both required and forbidden")
    for key in ("corridor_width_m", "door_width_m"):
        value = program.get(key)
        result[key] = None if draft and value is None else number(value, key)
        if result[key] is not None and not 0.5 <= result[key] <= 5:
            raise DesignError(f"{key} is outside the demo range of 0.5–5 m")
    for key, count in (("sight_target", 1), ("patient_route", 2), ("staff_route", 2)):
        raw = program.get(key)
        targets = [raw] if count == 1 else raw
        if raw is not None and (not isinstance(targets, list) or len(targets) != count or
                                any(not isinstance(item, str) or item not in (ids if count == 1 else ids | {"@entry"})
                                    for item in targets) or (count == 2 and targets[0] == targets[1])):
            raise DesignError(f"{key} must name existing endpoints")
        result[key] = raw
    for key in ("assumptions", "missing"):
        result[key] = [item for item in program.get(key, []) if isinstance(item, str)] if isinstance(program.get(key, []), list) else []
    if program.get("draft_source") in ("brief_extraction", "model_inference"):
        result["draft_source"] = program["draft_source"]
    return result


def read_brief(path):
    if path is None:
        return ""
    path = Path(path)
    if path.suffix.lower() == ".docx":
        from docx import Document
        document = Document(path)
        rows = [" | ".join(cell.text for cell in row.cells) for table in document.tables for row in table.rows]
        text = "\n".join([paragraph.text for paragraph in document.paragraphs] + rows)
    elif path.suffix.lower() == ".pdf":
        from pypdf import PdfReader
        text = "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
    elif path.suffix.lower() == ".txt":
        text = path.read_text(encoding="utf-8-sig")
    else:
        raise DesignError("Supported brief formats are DOCX, text-layer PDF, and TXT")
    if not text.strip():
        raise DesignError("No brief text was extracted; provide a text-layer PDF or a TXT transcription")
    if len(text) > 16000:
        raise DesignError("The demo accepts up to 16,000 characters of brief text; provide an excerpt")
    return text.strip()
