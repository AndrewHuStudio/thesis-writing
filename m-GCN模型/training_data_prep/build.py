"""Build independent boundary records and export normalized layout supervision."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from shapely.geometry import Polygon, mapping
from shapely.ops import unary_union

from geometry import envelope, rings, domain_from_rings, polygons
from export import convert_sample, apply_training_scope

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / 'e-实验评估/20261111_01-53_训练数据审计'
OUT = ROOT / 'p-平面标注与数据处理/训练数据/单层医院_v1'
TYPES = Path('/Users/hushili/.codex/skills/outpatient-plan-annotation/references/space-types.json')
LEVELS = ['room', 'open_space', 'semi_open_space', 'core_block', 'functional_block', 'landscape']
UNCERTAIN = {'40': ['S020', 'S057', 'S068', 'S069'], '45': ['S027', 'S028'],
             '46': ['S071'], '49': ['S081', 'S082'], '50': ['S010', 'S105'],
             '53': ['S038', 'S082', 'S085', 'S122']}


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def ensure_dirs():
    for name in ['边界记录', '边界预览', 'samples', 'tensors', 'review_evidence']:
        (OUT / name).mkdir(parents=True, exist_ok=True)


def boundaries():
    ensure_dirs()
    control_path = OUT / 'boundary_controls.json'
    controls = json.loads(control_path.read_text()) if control_path.exists() else {}
    results = []
    for p in sorted((AUDIT / '逐图审计').glob('*.json')):
        audit = json.loads(p.read_text())
        data = json.loads(Path(audit['annotation']).read_text())
        number = audit['plan'][:2]
        control = controls.setdefault(number, {'radius_fraction': .0075, 'review_status': 'pending',
                                                'review_notes': [], 'uncertain_space_ids': UNCERTAIN.get(number, []),
                                                'single_room_overrides': {}})
        data = apply_training_scope(data, control)
        parts, excluded = [], []
        for s in data['spaces']:
            if s['type'] in ('landscape', 'courtyard') or s['level'] == 'landscape':
                excluded.append(Polygon(s['polygon_px']))
            else:
                parts.append(Polygon(s['polygon_px']))
        raw = unary_union(parts)
        length = max(raw.bounds[2]-raw.bounds[0], raw.bounds[3]-raw.bounds[1])
        excluded = unary_union(excluded)
        domain = envelope(parts, excluded, length * control['radius_fraction'])
        if control.get('manual_outer_shells_px'):
            domain = domain_from_rings([{'outer': ring} for ring in control['manual_outer_shells_px']]).difference(excluded)
        if control.get('additional_holes_px'):
            domain = domain.difference(unary_union([Polygon(r) for r in control['additional_holes_px']]))
        if control.get('remove_domains_px'):
            domain = domain.difference(unary_union([Polygon(r) for r in control['remove_domains_px']]))
        closed = raw.buffer(length * control['radius_fraction'], join_style=2).buffer(-length * control['radius_fraction'], join_style=2).union(raw)
        unallocated = []
        for part in polygons(closed):
            for ring in part.interiors:
                gap = Polygon(ring).difference(excluded)
                for piece in polygons(gap):
                    if piece.area / length**2 > .0007:
                        unallocated.append({'polygon_px': [list(q) for q in piece.exterior.coords[:-1]],
                                            'status': 'unannotated_inner_range_not_assumed_indoor_or_courtyard',
                                            'domain_loss_mask': False})
        domain_rings = rings(domain)
        shape_sha = digest(domain_rings)
        reviewed = (control['review_status'] == 'reviewed_conceptual' and control.get('reviewed_shape_sha256') == shape_sha)
        record = {'plan': audit['plan'], 'source_annotation': audit['annotation'],
                  'source_image': audit['source'], 'source_image_sha256': audit['source_image_sha256'],
                  'source_limitations': audit['source_limitations'],
                  'outer_shells_and_holes_px': domain_rings, 'geometry_sha256': shape_sha,
                  'geometry': mapping(domain),
                  'review_status': 'reviewed_conceptual' if reviewed else 'pending',
                  'review_notes': control['review_notes'], 'boundary_reviewed': reviewed,
                  'review_evidence': control.get('review_evidence', {}),
                  'boundary_scope': 'current_annotated_single_floor_conceptual_design_domain',
                  'exact_external_wall_survey': False, 'metric_scale_m_per_px': None,
                  'uncertain_space_ids': control.get('uncertain_space_ids', []),
                  'single_room_overrides': control.get('single_room_overrides', {}),
                  'excluded_training_space_ids': control.get('excluded_training_space_ids', []),
                  'space_overrides': control.get('space_overrides', {}),
                  'user_feedback': control.get('user_feedback', {}),
                  'single_room_review_evidence': control.get('single_room_review_evidence', {}),
                  'supervision_scope': control.get('supervision_scope', 'full_conceptual_domain'),
                  'boundary_condition_eligible': reviewed and control.get('supervision_scope') != 'partial_uncertain_outer_domain',
                  'components': len(polygons(domain)), 'holes': sum(len(p.interiors) for p in polygons(domain)),
                  'gap_radius_px': length * control['radius_fraction'],
                  'added_area_over_indoor_union': domain.difference(raw).area/raw.area,
                  'uncovered_indoor_area_fraction': raw.difference(domain).area/raw.area,
                  'unallocated_inner_regions': unallocated,
                  'domain_is_full_occupancy_truth': False,
                  'evidence_preview': '边界预览/' + audit['plan'] + '.png',
                  'explicit_exclusions_px': [s for s in data['spaces'] if s['type'] in ('landscape', 'courtyard') or s['level'] == 'landscape']}
        save(OUT / '边界记录' / (audit['plan'] + '.json'), record)
        results.append({k: record[k] for k in ['plan', 'components', 'holes', 'gap_radius_px', 'added_area_over_indoor_union', 'review_status']})
    save(control_path, controls)
    save(OUT / 'boundary_draft_summary.json', results)
    print(json.dumps(results, ensure_ascii=False, indent=2))


def flatten_rings(parts):
    points, offsets, component, hole = [], [0], [], []
    for i, p in enumerate(parts):
        for j, ring in enumerate([p['outer']] + p.get('holes', [])):
            points.extend(ring)
            offsets.append(len(points))
            component.append(i)
            hole.append(j > 0)
    return dict(vertices=np.asarray(points, dtype=np.float64).reshape(-1, 2),
                offsets=np.asarray(offsets, dtype=np.int64),
                component=np.asarray(component, dtype=np.int64),
                hole=np.asarray(hole, dtype=bool))


def to_arrays(sample):
    y = sample['targets']
    masks = sample['masks']
    rels = y['relations']
    relation_types = ['access', 'service', 'shared_wall']
    points, offsets = [], [0]
    for p in y['polygons']:
        points.extend(p)
        offsets.append(len(points))
    arrays = {'x': np.asarray(sample['inputs']['node_features'], dtype=np.float32),
              'node_ids': np.asarray(sample['node_ids']), 'y_bbox': np.asarray(y['boxes'], dtype=np.float64),
              'y_area': np.asarray(y['area_normalized'], dtype=np.float64),
              'y_type': np.asarray(y['function_indices'], dtype=np.int64),
              'y_polygon_vertices': np.asarray(points, dtype=np.float64),
              'y_polygon_offsets': np.asarray(offsets, dtype=np.int64),
              'relation_label_index': np.asarray([[r['source_index'], r['target_index']] for r in rels], dtype=np.int64).reshape(-1, 2).T,
              'relation_label_type': np.asarray([relation_types.index(r['type']) for r in rels], dtype=np.int64),
              'relation_loss_mask': np.asarray([r['loss_mask'] for r in rels], dtype=bool),
              'negative_access_index': np.asarray([[r['source_index'], r['target_index']] for r in y['negative_relations']], dtype=np.int64).reshape(-1, 2).T,
              'entrance_target_index': np.asarray([r['target_index'] for r in y['entrances']], dtype=np.int64),
              'y_entrance_position': np.asarray([r['position'] for r in y['entrances']], dtype=np.float64).reshape(-1, 2),
              'entrance_position_loss_mask': np.asarray([r['position_loss_mask'] for r in y['entrances']], dtype=bool),
              'coordinate_origin_px': np.asarray(sample['coordinate_frame']['origin_px']),
              'coordinate_long_side_px': np.asarray(sample['coordinate_frame']['long_side_px']),
              'boundary_condition_mask': np.asarray(masks['boundary_condition']),
              'full_domain_partition_mask': np.asarray(masks.get('full_domain_partition', False))}
    for k, v in masks.items():
        if isinstance(v, list):
            arrays[k + '_mask'] = np.asarray(v, dtype=bool)
    for prefix, parts in [('boundary', sample['inputs']['boundary']), ('target_domain', y['domain'])]:
        arrays.update({prefix + '_' + k: v for k, v in flatten_rings(parts).items()})
    return arrays


def export_all():
    ensure_dirs()
    type_names = json.loads(TYPES.read_text())
    type_vocab = ['unknown'] + sorted(t for t in type_names if t != 'unknown')
    save(OUT / 'vocabulary.json', {'types': type_vocab, 'type_names': type_names, 'levels': LEVELS,
                                  'node_feature_order': ['type:' + t for t in type_vocab] + ['level:' + t for t in LEVELS] + ['function_known'],
                                  'scope_encoding': 'original_metadata_only',
                                  'relation_types': ['access', 'service', 'shared_wall']})
    entries = []
    for p in sorted((OUT / '边界记录').glob('*.json')):
        br = json.loads(p.read_text())
        audit = json.loads((AUDIT / '逐图审计' / p.name).read_text())
        original = json.loads(Path(br['source_annotation']).read_text())
        data = apply_training_scope(original, br)
        record = dict(br, domain=domain_from_rings(br['outer_shells_and_holes_px']),
                      boundary_reviewed=br['boundary_condition_eligible'],
                      confirmed_negative_relations=audit['explicit_negative_evidence'],
                      masked_relation_ids=[])
        length = max(record['domain'].bounds[2]-record['domain'].bounds[0], record['domain'].bounds[3]-record['domain'].bounds[1])
        record['masked_relation_ids'] = sorted({f['relation'] for f in audit['opening_endpoint_flags'] if max(f['distance_to_polygons_px']) / length > .01})
        sample = convert_sample(data, record, type_vocab, LEVELS)
        sample['plan_id'] = br['plan']
        sample['provenance'] = {'source_annotation': str(Path(br['source_annotation']).relative_to(ROOT)),
                                'source_annotation_sha256': hashlib.sha256(Path(br['source_annotation']).read_bytes()).hexdigest(),
                                'source_image_sha256': br['source_image_sha256'], 'boundary_geometry_sha256': br['geometry_sha256'],
                                'boundary_record': '边界记录/' + p.name, 'source_scope_limitations': br['source_limitations'],
                                'boundary_review_status': br['review_status'], 'split': 'train',
                                'ground_truth_precision': 'conceptual_approximation_not_surveyed',
                                'excluded_training_space_ids': br['excluded_training_space_ids'],
                                'space_overrides': br['space_overrides'],
                                'user_feedback': br['user_feedback'],
                                'original_overridden_space_values': [s for s in original['spaces'] if s['id'] in br['space_overrides']],
                                'test_split': 'deferred_by_user'}
        # Region membership is an auxiliary target, not a default model input.
        selected = audit['review_evidence'].get('selected')
        regions = []
        sample['provenance']['audit_record_sha256'] = hashlib.sha256((AUDIT / '逐图审计' / p.name).read_bytes()).hexdigest()
        sample['provenance']['review_evidence_snapshot'] = None
        if selected:
            content = Path(selected).read_bytes()
            snapshot = OUT / 'review_evidence' / p.name
            snapshot.write_bytes(content)
            sample['provenance']['review_evidence_snapshot'] = {
                'file': 'review_evidence/' + p.name,
                'source': str(Path(selected).relative_to(ROOT)),
                'sha256': hashlib.sha256(content).hexdigest()}
            regions = json.loads(content).get('regions', [])
        from geometry import normalize_points
        sample['targets']['regions'] = []
        live_ids = {s['id'] for s in data['spaces']}
        for r in regions:
            members = [sid for sid in r.get('member_space_ids', []) if sid in live_ids]
            if not members:
                continue
            pieces = r.get('polygons_px', [r['polygon_px']] if 'polygon_px' in r else [])
            clipped = [poly for piece in pieces for poly in polygons(Polygon(piece).intersection(record['domain']))]
            sample['targets']['regions'].append({'id': r['id'], 'name': r['name'],
                'member_space_ids': members,
                'polygons': [normalize_points(list(poly.exterior.coords)[:-1], sample['coordinate_frame']) for poly in clipped],
                'layer': 'auxiliary_region_not_duplicate_room', 'coordinates': 'normalized_y_up'})
        sample['targets']['unallocated_inner_regions'] = [
            {'polygon': normalize_points(r['polygon_px'], sample['coordinate_frame']),
             'status': r['status'], 'domain_loss_mask': False} for r in br['unallocated_inner_regions']]
        sample['masks']['full_domain_partition'] = False
        save(OUT / 'samples' / p.name, sample)
        arrays = to_arrays(sample)
        np.savez_compressed(OUT / 'tensors' / (p.stem + '.npz'), **arrays)
        entries.append({'plan_id': br['plan'], 'split': 'train', 'nodes': len(sample['node_ids']),
                        'sample': 'samples/' + p.name, 'tensor': 'tensors/' + p.stem + '.npz',
                        'boundary_record': '边界记录/' + p.name,
                        'boundary_reviewed': br['boundary_reviewed'],
                        'boundary_condition_eligible': br['boundary_condition_eligible'],
                        'geometry_available': sum(sample['masks']['geometry']),
                        'layout_supervised': sum(sample['masks']['layout']),
                        'function_known': sum(sample['masks']['function']),
                        'known_single_rooms': sum(sample['masks']['known_single_room']),
                        'uncertain_space_ids': br['uncertain_space_ids']})
    assert len(entries) == 53
    save(OUT / 'manifest.json', {'schema_version': 'single_floor_layout_v1', 'plans': entries,
                               'all_split': 'train', 'validation_test_split': None,
                               'boundary_only_model_implemented': False, 'training_run': None,
                               'default_input_graph': 'not_assumed_true_access_graph'})
    print(json.dumps({'exported': len(entries), 'boundary_reviewed': sum(e['boundary_reviewed'] for e in entries),
                      'boundary_condition_eligible': sum(e['boundary_condition_eligible'] for e in entries)}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', choices=['boundaries', 'export'], required=True)
    args = parser.parse_args()
    boundaries() if args.stage == 'boundaries' else export_all()
