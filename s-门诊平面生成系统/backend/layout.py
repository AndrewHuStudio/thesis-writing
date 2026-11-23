"""Small deterministic room placement and corridor search for the single-zone demo."""

from collections import deque
from itertools import combinations, pairwise
from math import ceil, dist, floor

from shapely import set_precision
from shapely.geometry import Polygon, box
from shapely.ops import linemerge, unary_union
from shapely.prepared import prep

from inputs import DesignError, pair_key


STEP = 0.5
EPS = 1e-7


def line_parts(geometry):
    if geometry.geom_type == "LineString" and not geometry.is_empty:
        return [geometry]
    return [line for part in getattr(geometry, "geoms", ()) for line in line_parts(part)]


def shared_door(left, right, door_width):
    segments = line_parts(left.boundary.intersection(right.boundary))
    if len(segments) > 1:
        segments = line_parts(linemerge(segments))
    for line in sorted(segments, key=lambda segment: (-segment.length, segment.bounds)):
        if line.length + EPS >= door_width:
            start = max(0, (line.length - door_width) / 2)
            points = [line.interpolate(start), line.interpolate(min(line.length, start + door_width))]
            if abs(dist(*[(point.x, point.y) for point in points]) - door_width) <= EPS:
                return [[point.x, point.y] for point in points]
    return None


def clearance_square(point, width):
    x_coord, y_coord = point
    radius = width / 2
    return set_precision(box(x_coord - radius, y_coord - radius, x_coord + radius, y_coord + radius), 1e-8)


def corridor_search(boundary, polygon, width, attempt):
    if boundary["entrance_length_m"] + EPS < width:
        raise DesignError("The selected entrance edge is shorter than the requested corridor width")
    seed = (0, 0)
    covers = prep(polygon).covers

    def center(cell):
        return cell[0] * STEP, cell[1] * STEP + width / 2

    if not covers(clearance_square(center(seed), width)):
        raise DesignError("The requested corridor cannot fit immediately inside the selected entrance")
    predecessors = {seed: None}
    visited = {seed}
    queue = deque([seed])
    while queue:
        x_coord, y_coord = queue.popleft()
        for neighbor in ((x_coord, y_coord + 1), (x_coord - 1, y_coord),
                         (x_coord + 1, y_coord), (x_coord, y_coord - 1)):
            if neighbor not in visited:
                visited.add(neighbor)
                if covers(clearance_square(center(neighbor), width)):
                    predecessors[neighbor] = (x_coord, y_coord)
                    queue.append(neighbor)
    if attempt:
        end = max(predecessors, key=lambda cell: (cell[0] ** 2 + cell[1] ** 2, -cell[0], cell[1]))
    else:
        end = max(predecessors, key=lambda cell: (cell[1], -abs(cell[0]), -cell[0]))
    spine = []
    while end is not None:
        spine.append(center(end))
        end = predecessors[end]
    spine.reverse()
    corridor = unary_union([clearance_square(point, width) for point in spine]).simplify(0)
    return corridor, spine


def room_sizes(room):
    for width in range(4, 21):
        minimum = max(4, ceil((room["min_area_m2"] - EPS) / (width * STEP ** 2)))
        maximum = min(20, floor((room["max_area_m2"] + EPS) / (width * STEP ** 2)))
        for depth in range(minimum, maximum + 1):
            if max(width, depth) <= 2.5 * min(width, depth):
                yield width * STEP, depth * STEP


def starts(start, end, length, door_width):
    first, last = start - length + door_width, end - door_width
    if last >= first - EPS:
        yield first
        for index in range(ceil(first / STEP), floor(last / STEP) + 1):
            candidate = index * STEP
            if first + EPS < candidate < last - EPS:
                yield candidate
        if last > first + EPS:
            yield last


def room_options(room, boundary, corridor, door_width):
    edges = list(pairwise(corridor.exterior.coords))
    covered = prep(boundary).covers
    result = []
    tested = set()
    for width, depth in room_sizes(room):
        for start, end in edges:
            horizontal = start[1] == end[1]
            along, across = (0, 1) if horizontal else (1, 0)
            span = sorted((start[along], end[along]))
            room_length = width if horizontal else depth
            room_cross = depth if horizontal else width
            anchor = start[across]
            if span[1] - span[0] < door_width - EPS or room_length < door_width - EPS:
                continue
            for offset in starts(*span, room_length, door_width):
                for shift in (-room_cross, 0):
                    x_coord, y_coord = (offset, anchor + shift) if horizontal else (anchor + shift, offset)
                    bounds = tuple(round(value, 8) for value in (x_coord, y_coord, x_coord + width, y_coord + depth))
                    if bounds in tested:
                        continue
                    tested.add(bounds)
                    shape = set_precision(box(*bounds), 1e-8)
                    if covered(shape) and shape.intersection(corridor).area <= EPS:
                        door = shared_door(shape, corridor, door_width)
                        if door:
                            center = (shape.centroid.x, shape.centroid.y)
                            result.append((shape, center, door))
    return result


def place_rooms(program, prediction, advice, boundary, corridor, attempt):
    rooms = program["rooms"]
    door_width = program["door_width_m"]
    required, optional, forbidden = [{tuple(pair) for pair in program[key]} for key in
                                     ("required_connections", "optional_connections", "forbidden_connections")]
    optional -= forbidden
    scores = {tuple(row["pair"]): row["score"] for row in prediction["access_scores"]}
    preferences = {tuple(pair) for pair in advice.get("preferred_pairs", [])}
    near = set(advice.get("near_entrance", []))
    order = sorted(rooms, key=lambda room: (-sum(room["id"] in pair for pair in required),
                                             -room["min_area_m2"], room["id"]))
    beam = [(0.0, {})]
    cache = {}
    scale = max(boundary.bounds[2] - boundary.bounds[0], boundary.bounds[3] - boundary.bounds[1])
    for room in order:
        room_id = room["id"]
        area_key = (room["min_area_m2"], room["max_area_m2"])
        if area_key not in cache:
            cache[area_key] = room_options(room, boundary, corridor, door_width)
        target = prediction["layout_boxes_local_m"][room_id]
        candidates = []
        for option in cache[area_key]:
            shape, center, _ = option
            size = (shape.bounds[2] - shape.bounds[0], shape.bounds[3] - shape.bounds[1])
            cost = (dist(center, target[:2]) + 0.4 * dist(size, target[2:])) / scale
            if room_id in near:
                cost += dist(center, (0, 0)) / scale
            if attempt:
                cost += 1.5 * (shape.area / room["min_area_m2"] - 1)
            candidates.append((cost, option))
        candidates.sort(key=lambda item: (item[0], item[1][0].bounds))
        next_beam = []
        for cost, placed in beam:
            for rank_cost, option in candidates[:120 if not attempt else 360]:
                shape = option[0]
                if any(shape.intersection(other[0]).area > EPS for other in placed.values()):
                    continue
                bonus = 0
                for other_id, other in placed.items():
                    pair = pair_key(room_id, other_id)
                    if pair in required or pair in optional:
                        if shared_door(shape, other[0], door_width):
                            if pair in optional:
                                bonus += 0.25 * scores.get(pair, 0) + (0.15 if pair in preferences else 0)
                        elif pair in required:
                            break
                else:
                    next_beam.append((cost + rank_cost - bonus, placed | {room_id: option}))
        if not next_beam:
            raise DesignError(f"No layout found for room {room_id} with the current corridor and search budget")
        next_beam.sort(key=lambda item: item[0])
        beam = next_beam[:(4 if not attempt else 12)]
    return beam[0][1]


def generate_layout(boundary, program, prediction, advice, attempt):
    polygon = Polygon(boundary["local_ring"])
    corridor, spine = corridor_search(boundary, polygon, program["corridor_width_m"], attempt)
    placements = place_rooms(program, prediction, advice, polygon, corridor, attempt)
    doors = [{"pair": [room_id, "@corridor"], "line": option[2]} for room_id, option in placements.items()]
    forbidden = {tuple(pair) for pair in program["forbidden_connections"]}
    allowed = {tuple(pair) for key in ("required_connections", "optional_connections") for pair in program[key]}
    for left, right in combinations(sorted(placements), 2):
        pair = (left, right)
        if pair in allowed and pair not in forbidden:
            opening = shared_door(placements[left][0], placements[right][0], program["door_width_m"])
            if opening:
                doors.append({"pair": list(pair), "line": opening})
    return {
        "rooms": {room_id: [list(point) for point in option[0].exterior.coords]
                  for room_id, option in placements.items()},
        "corridor": [list(point) for point in corridor.exterior.coords],
        "centerline": [list(point) for point in spine], "entry": [0, 0], "doors": doors,
    }
