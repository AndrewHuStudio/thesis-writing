"""Matched, masked held-out layout measurements and source-group aggregation."""
from collections import defaultdict

import numpy as np
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from boundary_layout.loss import matching_indices
from layout_evaluation.metrics import overlap_metrics
from room_layout_pilot.evaluate import boxes, paired_iou


def score_layout(sample, prediction):
    permutation = matching_indices(sample, prediction).cpu().numpy()
    raw = prediction.detach().cpu().numpy()
    proposed = raw[permutation]
    target = sample['target'].cpu().numpy()
    valid = sample['valid_mask'].cpu().numpy()
    fine = sample['room_mask']
    predicted_bounds, target_bounds = boxes(proposed), boxes(target)
    domain = unary_union([Polygon(part['outer'], part.get('holes', [])) for part in sample['boundary_parts']])
    ious = paired_iou(predicted_bounds, target_bounds)
    rows, fine_shapes, fine_ids = [], [], []
    for index in np.flatnonzero(valid):
        truth = Polygon(sample['polygons'][index])
        shape = box(*predicted_bounds[index])
        if not truth.is_valid or truth.area <= 0:
            raise ValueError('Invalid geometry was included in the evaluation mask')
        rows.append({'id': sample['node_ids'][index], 'fine_room': bool(fine[index]),
                     'center_error_pct_long_side': 100 * float(np.linalg.norm(proposed[index, :2] - target[index, :2])),
                     'box_iou': float(ious[index]),
                     'polygon_iou': float(shape.intersection(truth).area / shape.union(truth).area),
                     'area_relative_error': float(abs(shape.area - truth.area) / truth.area),
                     'outside_area': float(shape.difference(domain).area), 'area': float(shape.area)})
        if fine[index]:
            fine_shapes.append(shape)
            fine_ids.append(sample['node_ids'][index])
    metrics = {}
    for name, selected in [('fine_rooms', [r for r in rows if r['fine_room']]),
                           ('other_valid_spaces', [r for r in rows if not r['fine_room']])]:
        metrics[name + '_count'] = len(selected)
        for key in ['center_error_pct_long_side', 'box_iou', 'polygon_iou', 'area_relative_error']:
            metrics[name + '_' + key] = float(np.mean([r[key] for r in selected])) if selected else None
        metrics[name + '_outside_area_fraction'] = (
            sum(r['outside_area'] for r in selected) / sum(r['area'] for r in selected)) if selected else None
    overlap = overlap_metrics(fine_ids, fine_shapes) if fine_shapes else None
    metrics['fine_rooms_overlap_area_fraction'] = overlap['overlap_area_fraction_of_union'] if overlap else None
    metrics['fine_rooms_overlap_pair_count'] = overlap['pair_count'] if overlap else None
    metrics['fine_rooms_identity_box_iou'] = float(paired_iou(boxes(raw)[fine], target_bounds[fine]).mean()) if fine.any() else None
    relations = sample['reference_access_pairs'].numpy()
    if len(relations):
        relations = relations[valid[relations].all(axis=1)]
    for name, bounds in [('generated', predicted_bounds), ('reference', target_bounds)]:
        gap = None
        if len(relations):
            left, right = bounds[relations[:, 0]], bounds[relations[:, 1]]
            separation = np.maximum(np.maximum(left[:, :2] - right[:, 2:], right[:, :2] - left[:, 2:]), 0)
            gap = float(np.linalg.norm(separation, axis=1).mean())
        metrics[name + '_observed_access_bbox_gap'] = gap
    return {'plan_id': sample['plan_id'], 'metrics': metrics, 'per_space': rows,
            'prediction_index_for_reference': permutation.tolist(),
            'matching_scope': 'identical_50_column_input_patterns_with_valid_geometry',
            'overlap_details': overlap['pairs'] if overlap else [],
            'physical_navigation_available': False}


def aggregate(rows, group_ids):
    groups = defaultdict(list)
    for row in rows:
        groups[group_ids[row['plan_id']]].append(row)
    summary = {'plans': len(rows), 'source_groups': len(groups)}
    for key in rows[0]['metrics']:
        values = [r['metrics'][key] for r in rows if r['metrics'][key] is not None]
        group_values = []
        for members in groups.values():
            scores = [r['metrics'][key] for r in members if r['metrics'][key] is not None]
            if scores:
                group_values.append(float(np.mean(scores)))
        summary[key] = {'plan_macro': float(np.mean(values)) if values else None,
                        'group_macro': float(np.mean(group_values)) if group_values else None,
                        'plans_with_measurement': len(values), 'groups_with_measurement': len(group_values)}
    return summary


def summarize(runs, group_ids):
    grouped = defaultdict(list)
    for run in runs:
        grouped[(run['model'], run['seed'])].extend(run['test_rows'])
    per_seed = []
    for (model, seed), rows in grouped.items():
        ids = [r['plan_id'] for r in rows]
        if len(ids) != len(set(ids)):
            raise ValueError('A test plan appears more than once for a model and seed')
        per_seed.append({'model': model, 'seed': seed,
                         'all_plans_evaluated_once': set(ids) == set(group_ids),
                         'summary': aggregate(rows, group_ids)})
    comparisons = {}
    for model in sorted({r['model'] for r in per_seed}):
        selected = [r for r in per_seed if r['model'] == model]
        metrics = {}
        for key in selected[0]['summary']:
            if key in ('plans', 'source_groups'):
                continue
            values = [r['summary'][key]['group_macro'] for r in selected]
            finite = [v for v in values if v is not None]
            metrics[key] = {'mean': float(np.mean(finite)) if finite else None,
                            'seed_standard_deviation': float(np.std(finite, ddof=1)) if len(finite) > 1 else None}
        comparisons[model] = {'seeds': len(selected), 'metrics': metrics}
    return {'per_seed': per_seed, 'comparisons': comparisons}
