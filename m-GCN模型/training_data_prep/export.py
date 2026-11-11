"""Separate inference inputs, supervised targets and per-task validity masks."""
import re
from copy import deepcopy
from shapely.geometry import Polygon

from geometry import make_frame, normalize_points, rings

COMBINED = re.compile(r'男.*女|女.*男|[+＋/／]|(?:、|及|和).*(?:室|间|库|卫)')
PENDING = re.compile(r'待核|未确认|未分类|未知|候选|待定|unknown|tbd|\?', re.I)


def apply_training_scope(data, record):
    result = deepcopy(data)
    excluded = set(record.get('excluded_training_space_ids', []))
    overrides = record.get('space_overrides', {})
    original_ids = {s['id'] for s in data['spaces']}
    if not excluded <= original_ids or not set(overrides) <= original_ids:
        raise ValueError('Scope feedback refers to non-existent space IDs')
    result['spaces'] = [s for s in result['spaces'] if s['id'] not in excluded]
    for s in result['spaces']:
        change = overrides.get(s['id'], {})
        if not set(change) <= {'name', 'type', 'level'}:
            raise ValueError('Only explicit semantic overrides are allowed')
        s.update(change)
    result['relations'] = [r for r in result['relations'] if r.get('source') not in excluded and r['target'] not in excluded]
    return result


def convert_sample(data, record, type_vocab, level_vocab):
    frame = make_frame(record['domain'])
    ids = [s['id'] for s in data['spaces']]
    index = {sid: i for i, sid in enumerate(ids)}
    uncertain = set(record.get('uncertain_space_ids', []))
    overrides = record.get('single_room_overrides', {})
    features, boxes, areas, outlines = [], [], [], []
    masks = {'geometry': [], 'function': [], 'single_room': [], 'known_single_room': [],
             'indoor_partition': [], 'layout': [], 'boundary_condition': bool(record['boundary_reviewed'])}
    for s in data['spaces']:
        known = s['type'] != 'unknown' and not PENDING.search(s['name'])
        row = [float(s['type'] == v) for v in type_vocab]
        row += [float(s['level'] == v) for v in level_vocab]
        row += [float(bool(known))]
        features.append(row)
        poly = Polygon(s['polygon_px'])
        shape_ok = poly.is_valid and poly.area > 0 and s['id'] not in uncertain
        indoor = s['type'] not in ('landscape', 'courtyard') and s['level'] != 'landscape'
        single = s['level'] == 'room' and overrides.get(s['id'], not COMBINED.search(s['name']))
        masks['geometry'].append(bool(shape_ok))
        masks['function'].append(bool(known))
        masks['single_room'].append(bool(single and shape_ok and indoor))
        masks['known_single_room'].append(bool(single and shape_ok and indoor and known))
        masks['indoor_partition'].append(bool(shape_ok and indoor))
        masks['layout'].append(bool(shape_ok and indoor))
        xmin, ymin, xmax, ymax = poly.bounds
        center = normalize_points([[(xmin+xmax)/2, (ymin+ymax)/2]], frame)[0]
        boxes.append(center + [(xmax-xmin)/frame['long_side_px'], (ymax-ymin)/frame['long_side_px']])
        areas.append(poly.area/frame['long_side_px']**2)
        outlines.append(normalize_points(s['polygon_px'], frame))
    relations, entrances = [], []
    blocked = set(record.get('masked_relation_ids', []))
    for r in data['relations']:
        if r['type'] == 'entrance':
            entrances.append({'id': r['id'], 'target_index': index[r['target']],
                              'position': normalize_points([r['position_px']], frame)[0],
                              'entrance_type': r['entrance_type'], 'name': r['name'],
                              'position_loss_mask': False})
        else:
            relations.append({'id': r['id'], 'source_index': index[r['source']], 'target_index': index[r['target']],
                              'type': r['type'], 'loss_mask': r['id'] not in blocked,
                              'openings': [{'id': p['id'], 'kind': p['kind'],
                                            'position': normalize_points([p['position_px']], frame)[0],
                                            'position_loss_mask': False} for p in r.get('openings', [])]})
    negatives = []
    for r in record.get('confirmed_negative_relations', []):
        if r.get('source') in index and r.get('target') in index:
            negatives.append({'source_index': index[r['source']], 'target_index': index[r['target']],
                              'type': 'access', 'evidence': r.get('review_id')})
    input_boundary = rings(record['domain'], frame)
    if not record.get('known_exclusions_provided', False):
        input_boundary = [{'outer': part['outer'], 'holes': []} for part in input_boundary]
    return {'schema_version': 'single_floor_layout_v1', 'node_ids': ids,
            'inputs': {'node_features': features, 'boundary': input_boundary,
                       'provided_constraint_edges': [], 'metric_scale_known': False},
            'targets': {'boxes': boxes, 'area_normalized': areas, 'polygons': outlines,
                        'domain': rings(record['domain'], frame),
                        'function_indices': [type_vocab.index(s['type']) for s in data['spaces']],
                        'relations': relations, 'negative_relations': negatives, 'entrances': entrances},
            'masks': masks, 'coordinate_frame': frame,
            'metadata': [{'id': s['id'], 'name': s['name'], 'type': s['type'], 'level': s['level'],
                          'scope_original': s['scope']} for s in data['spaces']],
            'task_contract': {'default': 'boundary_plus_space_program_to_relative_layout',
                              'raw_access_is_input': False, 'exact_door_supervision': False,
                              'boundary_only_requires_program_proposal': True}}
