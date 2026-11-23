"""Audit the generated geometry and compute schematic visibility and walking routes."""

from itertools import combinations, pairwise
from math import dist

import networkx as nx
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

from inputs import pair_key
from layout import EPS, clearance_square


def as_shapes(layout):
    shapes = {room_id: Polygon(ring) for room_id, ring in layout["rooms"].items()}
    return shapes | {"@corridor": Polygon(layout["corridor"])}


def audit(boundary, program, layout):
    polygon = Polygon(boundary["local_ring"])
    shapes = as_shapes(layout)
    issues = []
    rooms = {room["id"]: room for room in program["rooms"]}
    if set(shapes) - {"@corridor"} != set(rooms):
        issues.append({"code": "room_inventory"})
    if any(not shape.is_valid or shape.is_empty for shape in shapes.values()):
        return {"passed": False, "issues": issues + [{"code": "invalid_geometry"}]}
    for space_id, shape in shapes.items():
        outside = shape.difference(polygon).area
        if outside > EPS:
            issues.append({"code": "outside_boundary", "space": space_id, "area_m2": outside})
        room = rooms.get(space_id)
        if room and not room["min_area_m2"] - EPS <= shape.area <= room["max_area_m2"] + EPS:
            issues.append({"code": "room_area", "space": space_id, "area_m2": shape.area,
                           "range_m2": [room["min_area_m2"], room["max_area_m2"]]})
    for left, right in combinations(shapes, 2):
        overlap = shapes[left].intersection(shapes[right]).area
        if overlap > EPS:
            issues.append({"code": "overlap", "pair": [left, right], "area_m2": overlap})
    width = program["corridor_width_m"]
    corridor = shapes["@corridor"].buffer(EPS)
    spine = layout["centerline"]
    if (not spine or dist(spine[0], (0, width / 2)) > EPS or
            not corridor.covers(LineString([(-width / 2, 0), (width / 2, 0)])) or
            any(not corridor.covers(clearance_square(point, width)) for point in spine) or
            any(abs(left[0] - right[0]) > EPS and abs(left[1] - right[1]) > EPS or dist(left, right) > width + EPS
                for left, right in pairwise(spine))):
        issues.append({"code": "corridor_clearance", "required_width_m": width})
    observed = set()
    for door in layout["doors"]:
        left, right = door["pair"]
        opening = LineString(door["line"])
        if (left not in shapes or right not in shapes or left == right or
                opening.length + EPS < program["door_width_m"] or
                not all(shapes[item].boundary.buffer(EPS).covers(opening) for item in (left, right))):
            issues.append({"code": "invalid_door", "pair": [left, right]})
        else:
            observed.add(pair_key(left, right))
    required = {tuple(pair) for pair in program["required_connections"]}
    required.update(pair_key(room_id, "@corridor") for room_id in rooms)
    forbidden = {tuple(pair) for pair in program["forbidden_connections"]}
    optional = {tuple(pair) for pair in program["optional_connections"]}
    for pairs, code in ((required - observed, "missing_connection"), (forbidden & observed, "forbidden_connection"),
                        (observed - required - optional - forbidden, "unapproved_connection")):
        issues.extend({"code": code, "pair": list(pair)} for pair in sorted(pairs))
    if not issues:
        graph, _ = route_graph(shapes, layout)
        issues.extend({"code": "unreachable_from_entry", "space": room_id}
                      for room_id in sorted(rooms) if not nx.has_path(graph, "@entry", room_id))
    checks = [{"pair": pair, "requirement": key, "door_present": tuple(pair) in observed,
               "passed": (tuple(pair) in observed) == (key == "required_connections")}
              for key in ("required_connections", "forbidden_connections") for pair in program[key]]
    return {"passed": not issues, "issues": issues, "connection_checks": checks,
            "realized_connections": [list(pair) for pair in sorted(observed)],
            "tested_corridor_width_m": width}


def route_graph(shapes, layout):
    graph = nx.Graph()
    positions = {}
    walkable_corridor = shapes["@corridor"].buffer(EPS)

    def connect(left, right):
        graph.add_edge(left, right, weight=dist(positions[left], positions[right]))

    positions["@entry"] = tuple(layout["entry"])
    graph.add_node("@entry")
    previous = "@entry"
    spine_ids = []
    for index, position in enumerate(layout["centerline"]):
        node = f"@spine:{index}"
        positions[node] = tuple(position)
        spine_ids.append(node)
        if walkable_corridor.covers(LineString([positions[previous], positions[node]])):
            connect(previous, node)
        previous = node
    for room_id, shape in shapes.items():
        if room_id != "@corridor":
            positions[room_id] = (shape.centroid.x, shape.centroid.y)
            graph.add_node(room_id)
    for index, door in enumerate(layout["doors"]):
        node = f"@door:{index}"
        midpoint = LineString(door["line"]).interpolate(0.5, normalized=True)
        positions[node] = (midpoint.x, midpoint.y)
        for space_id in door["pair"]:
            if space_id != "@corridor":
                connect(space_id, node)
            else:
                candidates = sorted(spine_ids, key=lambda spine_id: dist(positions[spine_id], positions[node]))
                for spine_id in candidates:
                    link = LineString([positions[node], positions[spine_id]])
                    if walkable_corridor.covers(link):
                        connect(node, spine_id)
                        break
    return graph, positions


def route(graph, positions, endpoints):
    if endpoints is None:
        return {"status": "not_evaluated", "reason": "no_endpoints"}
    try:
        path = nx.shortest_path(graph, *endpoints, weight="weight")
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return {"status": "unreachable", "endpoints": endpoints}
    points = [positions[node] for node in path]
    return {"status": "reachable", "endpoints": endpoints,
            "length_m": sum(dist(left, right) for left, right in pairwise(points)),
            "line": [list(point) for point in points]}


def sight_line(shapes, layout, target):
    if target is None:
        return {"status": "not_evaluated", "reason": "no_sight_target"}
    centroid = shapes[target].centroid
    points = [layout["entry"], [centroid.x, centroid.y]]
    ray = LineString(points)
    walkable = unary_union(list(shapes.values())).buffer(EPS)
    openings = unary_union([LineString(door["line"]) for door in layout["doors"]]).buffer(EPS)
    clear = walkable.covers(ray) and all(
        ray.intersection(shape.boundary).difference(openings).is_empty
        for space_id, shape in shapes.items() if space_id != "@corridor"
    )
    return {"status": "visible" if clear else "blocked", "target": target, "line": points}


def evaluate(program, layout):
    shapes = as_shapes(layout)
    graph, positions = route_graph(shapes, layout)
    rooms = [{"id": room["id"], "name": room["name"], "area_m2": shapes[room["id"]].area,
              "reachable_from_entry": nx.has_path(graph, "@entry", room["id"])} for room in program["rooms"]]
    patient = route(graph, positions, program["patient_route"])
    staff = route(graph, positions, program["staff_route"])
    separation = {"status": "not_evaluated", "reason": "both_routes_must_be_reachable"}
    if patient["status"] == staff["status"] == "reachable":
        first, second = [LineString(item["line"]) if len(item["line"]) > 1 else LineString() for item in (patient, staff)]
        shared = first.intersection(second)
        separation = {"status": "measured", "shared_length_m": shared.length,
                      "shared_lines": [[list(point) for point in line.coords]
                                       for line in getattr(shared, "geoms", [shared])
                                       if line.geom_type == "LineString" and not line.is_empty]}
    return {"scheme_count": 1, "room_count": len(rooms), "rooms": rooms,
            "corridor_area_m2": shapes["@corridor"].area,
            "unreachable_rooms": [room["id"] for room in rooms if not room["reachable_from_entry"]],
            "visibility": sight_line(shapes, layout, program["sight_target"]),
            "patient_route": patient, "staff_route": staff, "flow_overlap": separation,
            "scope": "schematic geometry only; not a clinical or building-code assessment"}
