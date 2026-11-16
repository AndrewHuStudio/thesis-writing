"""Polygon geometry and tie-aware topology diagnostics for saved predictions."""
from itertools import combinations

import networkx as nx
import numpy as np
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from room_layout_pilot.evaluate import boxes, paired_iou


def overlap_metrics(ids, polygons, area_epsilon=1e-10):
    intersections, details = [], []
    for i, j in combinations(range(len(polygons)), 2):
        intersection = polygons[i].intersection(polygons[j])
        if intersection.area > area_epsilon:
            intersections.append(intersection)
            details.append({'source': ids[i], 'target': ids[j], 'area': float(intersection.area)})
    occupied = unary_union(polygons).area
    overlap = unary_union(intersections).area if intersections else 0.
    return {'pair_count': len(details), 'overlap_area_fraction_of_union': overlap / occupied,
            'pairs': details}


def geometry_metrics(sample, prediction, boundary):
    """Score room rectangles in the pilot's saved, isotropically normalized frame."""
    prediction = np.asarray(prediction, dtype=float)
    target = np.asarray(sample['y'], dtype=float)
    if prediction.shape != target.shape or target.ndim != 2 or target.shape[1] != 4:
        raise ValueError('Prediction and target must have matching N by 4 box arrays')
    if not np.isfinite(prediction).all() or np.any(prediction[:, 2:] <= 0):
        raise ValueError('Predicted boxes need finite coordinates and positive sizes')
    if boundary.is_empty or not boundary.is_valid or boundary.area <= 0:
        raise ValueError('Evaluation boundary must be a valid positive-area geometry')
    frame = sample['reference_frame']
    origin = np.asarray(frame['origin_px'], dtype=float)
    length = float(frame['scale_px'])
    if not np.isfinite(length) or length <= 0:
        raise ValueError('Invalid saved coordinate scale')
    indices = np.flatnonzero(np.asarray(sample['room_mask'], dtype=bool))
    if not len(indices):
        raise ValueError('No eligible room geometry to evaluate')
    predicted_bounds, target_bounds = boxes(prediction), boxes(target)
    predicted, reference, ids, rows = [], [], [], []
    bbox_ious = paired_iou(predicted_bounds, target_bounds)
    for index in indices:
        node = sample['nodes'][index]
        points = (np.asarray(node['polygon_px'], dtype=float) - origin) / length
        truth = Polygon(points)
        if not truth.is_valid or truth.area <= 0:
            raise ValueError(f"Invalid reference room polygon: {node['id']}")
        proposed = box(*predicted_bounds[index])
        predicted.append(proposed)
        reference.append(truth)
        ids.append(node['id'])
        rows.append({'id': node['id'], 'name': node['name'],
                     'bbox_center_distance': float(np.linalg.norm(prediction[index, :2] - target[index, :2])),
                     'polygon_iou': float(proposed.intersection(truth).area / proposed.union(truth).area),
                     'box_iou': float(bbox_ious[index]),
                     'polygon_area_relative_error': float(abs(proposed.area - truth.area) / truth.area),
                     'outside_fraction': float(proposed.difference(boundary).area / proposed.area)})
    predicted_overlap = overlap_metrics(ids, predicted)
    reference_overlap = overlap_metrics(ids, reference)
    outside_area = sum(p.difference(boundary).area for p in predicted)
    total_area = sum(p.area for p in predicted)
    return {'evaluation_rooms': len(ids), 'matching': 'saved_node_identity',
            'coordinate_unit': 'saved_pilot_scope_long_side',
            'mean_center_distance_pct_scope_long_side': 100 * float(np.mean([r['bbox_center_distance'] for r in rows])),
            'mean_box_iou': float(np.mean([r['box_iou'] for r in rows])),
            'mean_polygon_iou': float(np.mean([r['polygon_iou'] for r in rows])),
            'mean_polygon_area_relative_error': float(np.mean([r['polygon_area_relative_error'] for r in rows])),
            'room_overlap_pair_count': predicted_overlap['pair_count'],
            'room_overlap_area_fraction': predicted_overlap['overlap_area_fraction_of_union'],
            'outside_building_area_fraction': float(outside_area / total_area),
            'outside_room_ids': [r['id'] for r in rows if r['outside_fraction'] > 1e-8],
            'reference_room_overlap_pair_count': reference_overlap['pair_count'],
            'reference_overlap_area_fraction': reference_overlap['overlap_area_fraction_of_union'],
            'overlap_details': predicted_overlap['pairs'], 'per_room': rows}


def graph_metrics(scores, pairs, node_count, trials=20, seed=20261116):
    """Sample ties at a fixed n-pair budget, then describe candidate-graph topology."""
    scores, pairs = np.asarray(scores), np.asarray(pairs)
    if scores.ndim != 1 or pairs.shape != (len(scores), 2) or not np.isfinite(scores).all():
        raise ValueError('Invalid graph prediction arrays')
    if node_count < 2 or trials < 1 or len(scores) < 1:
        raise ValueError('Need at least two nodes, one pair, and one tie trial')
    if not np.issubdtype(pairs.dtype, np.integer):
        raise ValueError('Pair endpoints must be integer node indices')
    if (pairs < 0).any() or (pairs >= node_count).any() or (pairs[:, 0] == pairs[:, 1]).any():
        raise ValueError('Invalid candidate endpoints')
    if len(np.unique(np.sort(pairs, axis=1), axis=0)) != len(pairs):
        raise ValueError('Candidate pairs must be unique undirected pairs')
    budget = min(node_count, len(scores))
    threshold = np.partition(scores, len(scores) - budget)[len(scores) - budget]
    above = np.flatnonzero(scores > threshold)
    tied = np.flatnonzero(scores == threshold)
    required = budget - len(above)
    generator = np.random.default_rng(seed)
    rows = []
    for _ in range(trials):
        selected = np.concatenate((above, generator.choice(tied, required, replace=False)))
        graph = nx.Graph()
        graph.add_nodes_from(range(node_count))
        graph.add_edges_from(pairs[selected].tolist())
        components = list(nx.connected_components(graph))
        rows.append({'component_count': len(components),
                     'isolated_node_fraction': nx.number_of_isolates(graph) / node_count,
                     'largest_component_node_fraction': max(map(len, components)) / node_count})
    summary = {key: {'mean': float(np.mean([r[key] for r in rows])),
                     'minimum': float(min(r[key] for r in rows)),
                     'maximum': float(max(r[key] for r in rows))} for key in rows[0]}
    return {'nodes': node_count, 'candidate_pair_budget': budget,
            'ties_at_cutoff': len(tied), 'tie_trials': trials, 'tie_seed': seed,
            'metrics': summary, 'scope': 'conceptual_candidate_graph_topology',
            'physical_route_assessment_available': False}
