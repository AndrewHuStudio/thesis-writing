"""Read-only audit of all official annotations; derived proposals are not truth."""
import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

from PIL import Image
from shapely import make_valid
from shapely.geometry import Polygon, Point, mapping
from shapely.ops import unary_union
from shapely.strtree import STRtree

SKILL = Path('/Users/hushili/.codex/skills/outpatient-plan-annotation')
sys.path.insert(0, str(SKILL / 'scripts'))
from annotation_tools import check, indoor
from review_workflow import completion

PENDING = re.compile(r'待核|未确认|未分类|未知|候选|待定|unknown|tbd|\?', re.I)
COMBINED = re.compile(r'男.*女|女.*男|[+＋/／]|(?:、|及|和).*(?:室|间|库|卫)')
OUTDOOR = re.compile(r'室外|屋面|屋顶|雨棚|挑空|庭院|中庭|平台|露台|停车|绿地|绿化')
BACKUPS = ('备份', 'backup', 'archive', '候选Skill', 'Skill修改', 'Skill优化', '同步前', '修改前', '接续前')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def polys(geom):
    if geom.geom_type == 'Polygon':
        return [geom]
    if hasattr(geom, 'geoms'):
        return [p for g in geom.geoms for p in polys(g)]
    return []


def review_candidates(root):
    out = []
    for p in root.rglob('review_state.json'):
        if any(word.lower() in str(p).lower() for word in BACKUPS):
            continue
        try:
            out.append((p, json.loads(p.read_text())))
        except (ValueError, OSError):
            pass
    return out


def select_review(candidates, path, data, image_sha):
    choices = []
    live = {s['id'] for s in data['spaces']}
    for p, state in candidates:
        sig = state.get('image_signature', {})
        if sig.get('file') != data['image']['file'] and path.parent.name not in str(p):
            continue
        if sig and (sig.get('file') != data['image']['file'] or sig.get('sha256', image_sha) != image_sha):
            continue
        refs = {s for r in state.get('regions', []) for s in r.get('member_space_ids', [])}
        stale = sorted(refs - live)
        try:
            result = completion(data, path, p)
        except Exception as error:
            result = {'review_errors': [str(error)]}
        errors = result.get('review_errors', [])
        rank = (not stale and not errors, bool(state.get('regions')), sum(v is True for v in state.get('checks', {}).values()), p.stat().st_mtime)
        choices.append((rank, p, state, result, stale))
    choices.sort(key=lambda x: x[0], reverse=True)
    evidence = [{'path': str(c[1]), 'stale_region_members': c[4], 'completion': c[3]} for c in choices]
    if not choices:
        return {}, {'selected': None, 'candidates': [], 'status': 'no_current_state_located'}
    _, p, state, result, stale = choices[0]
    return state, {'selected': str(p), 'candidates': evidence, 'status': 'matched_candidate_not_new_visual_review', 'completion': result}


def audit_plan(path, candidates, out):
    data = json.loads(path.read_text())
    plan = path.parent.name
    source = path.parent / data['image']['file']
    image_sha = sha(source)
    state, review = select_review(candidates, path, data, image_sha)
    validation, _ = check(data, path, allow_incomplete=True, check_dir=True)
    with Image.open(source) as im:
        image_size = list(im.size)
    spaces, relations = data['spaces'], data['relations']
    geometries = [Polygon(s['polygon_px']) for s in spaces]
    good = [p.is_valid and p.area > 0 for p in geometries]
    repaired = [p if ok else make_valid(p) for p, ok in zip(geometries, good)]
    byid = {s['id']: p for s, p in zip(spaces, repaired)}
    tree = STRtree(repaired)
    overlaps = []
    touched = set()
    for i, p in enumerate(repaired):
        for j in tree.query(p):
            j = int(j)
            if j <= i:
                continue
            area = p.intersection(repaired[j]).area
            if area > 1:
                a, b = spaces[i]['id'], spaces[j]['id']
                overlaps.append({'a': a, 'b': b, 'area_px2': area, 'fraction_smaller': area / min(p.area, repaired[j].area)})
                touched.update([a, b])
    flags = []
    w, h = data['image']['width'], data['image']['height']
    for s, p, ok in zip(spaces, repaired, good):
        bounds_ok = all(0 <= x <= w and 0 <= y <= h for x, y in s['polygon_px'])
        unknown = s['type'] == 'unknown' or bool(PENDING.search(s['name']))
        combined = bool(COMBINED.search(s['name']))
        shape_ok = ok and bounds_ok and s['id'] not in touched
        flags.append({'id': s['id'], 'name': s['name'], 'type': s['type'], 'level': s['level'],
                      'scope': s['scope'], 'geometry_candidate': shape_ok,
                      'function_label_available': not unknown,
                      'single_room_candidate': shape_ok and not combined and s['level'] == 'room',
                      'known_single_room_candidate': shape_ok and not unknown and not combined and s['level'] == 'room',
                      'combined_name_review': combined,
                      'outdoor_or_void_review': bool(OUTDOOR.search(s['name'] + ' ' + s['scope'])),
                      'excluded_from_indoor_area': not indoor(s),
                      'original_polygon_valid': ok, 'bounds_ok': bounds_ok,
                      'overlap_review': s['id'] in touched,
                      'mask_status': 'proposed_from_structure_not_final_semantic_verification'})
    raw = unary_union([p for s, p in zip(spaces, repaired) if indoor(s)])
    excluded = unary_union([p for s, p in zip(spaces, repaired) if not indoor(s)])
    xmin, ymin, xmax, ymax = raw.bounds
    length = max(xmax - xmin, ymax - ymin)
    radius = length * .001
    candidate = raw.buffer(radius, join_style=2).buffer(-radius, join_style=2)
    if not excluded.is_empty:
        candidate = candidate.difference(excluded)
    candidate_parts = polys(candidate)
    raw_parts = polys(raw)
    candidate_meta = {'status': 'unverified_occupied_envelope_candidate_not_building_boundary',
                      'method': 'indoor_union_then_small_gap_closing_then_subtract_explicit_exclusions',
                      'gap_radius_px': radius, 'raw_components': len(raw_parts),
                      'candidate_components': len(candidate_parts),
                      'raw_holes': sum(len(p.interiors) for p in raw_parts),
                      'candidate_holes': sum(len(p.interiors) for p in candidate_parts),
                      'relative_symmetric_difference': candidate.symmetric_difference(raw).area / raw.area,
                      'bbox_px': [xmin, ymin, xmax, ymax],
                      'largest_component_area_fraction': max((p.area for p in candidate_parts), default=0) / candidate.area,
                      'scale_m_per_px': None, 'metric_scale_status': 'not_recorded_in_annotation_json',
                      'normalization_proposal': {'origin_px': [xmin, ymax], 'length_px': length,
                                                 'x_formula': '(x-xmin)/length', 'y_formula': '(ymax-y)/length',
                                                 'status': 'provisional_frame_until_boundary_review'}}
    endpoint_flags = []
    relation_flags = []
    for r in relations:
        distances = []
        for op in r.get('openings', []):
            point = Point(op['position_px'])
            ends = [byid[r['source']], byid[r['target']]]
            ds = [p.distance(point) for p in ends]
            bd = [p.boundary.distance(point) for p in ends]
            distances.append(max(ds))
            if max(ds) > 1:
                endpoint_flags.append({'relation': r['id'], 'opening': op['id'], 'source': r['source'],
                                       'target': r['target'], 'distance_to_polygons_px': ds,
                                       'distance_to_boundaries_px': bd, 'position_px': op['position_px']})
        relation_flags.append({'id': r['id'], 'source': r['source'], 'target': r['target'], 'type': r['type'],
                               'positive_relation_candidate': True,
                               'positioned_access': r['type'] == 'access' and bool(r.get('openings')),
                               'conceptual_access_without_position': r['type'] == 'access' and not r.get('openings'),
                               'door_position_candidate': bool(distances) and max(distances) <= 1,
                               'original_semantic_evidence': 'inherited_annotation_not_new_visual_confirmation'})
    # Regions are auxiliary evidence, never duplicated as extra room nodes.
    regions = state.get('regions', [])
    region_issues = []
    for r in regions:
        missing = sorted(set(r.get('member_space_ids', [])) - set(byid))
        if missing:
            region_issues.append({'region': r.get('id'), 'missing_members': missing})
        rings = r.get('polygons_px', [r['polygon_px']] if 'polygon_px' in r else [])
        for ring in rings:
            if not Polygon(ring).is_valid:
                region_issues.append({'region': r.get('id'), 'invalid_polygon': True})
    explicit_negatives = []
    for item in state.get('connectivity_items', []):
        if item.get('status') == 'confirmed_disconnected':
            explicit_negatives.append(item)
    notes = (path.parent / '标注说明.md').read_text()
    result = {'plan': plan, 'annotation': str(path), 'source': str(source),
              'source_image_sha256': image_sha, 'actual_image_size': image_size,
              'metadata_size_matches': image_size == [w, h],
              'validation': validation, 'review_evidence': review,
              'spaces': len(spaces), 'relations': len(relations),
              'levels': dict(Counter(s['level'] for s in spaces)),
              'types': dict(Counter(s['type'] for s in spaces)),
              'unknown_types': sum(s['type'] == 'unknown' for s in spaces),
              'name_pending': sum(bool(PENDING.search(s['name'])) for s in spaces),
              'known_room_field_count': sum(s['level'] == 'room' and s['type'] != 'unknown' for s in spaces),
              'known_single_room_candidates': sum(f['known_single_room_candidate'] for f in flags),
              'valid_polygon_count': sum(good), 'overlaps': overlaps,
              'opening_count': sum(len(r.get('openings', [])) for r in relations),
              'access_without_openings': sum(r['type'] == 'access' and not r.get('openings') for r in relations),
              'opening_endpoint_flags': endpoint_flags,
              'combined_name_flags': [f['id'] for f in flags if f['combined_name_review']],
              'outdoor_or_void_flags': [f['id'] for f in flags if f['outdoor_or_void_review']],
              'regions': len(regions), 'region_issues': region_issues,
              'explicit_negative_evidence': explicit_negatives,
              'source_limitations': state.get('source_limitations', []),
              'md_summary': '\n'.join(notes.splitlines()[:18]),
              'candidate_envelope': candidate_meta,
              'pool_assignment': 'train_candidate', 'split_performed': False,
              'building_boundary_status': 'not_yet_traced_or_verified',
              'visual_review_status': 'pending_overview_only',
              'nodes': flags, 'relation_candidates': relation_flags}
    save(out / '逐图审计' / (plan + '.json'), result)
    save(out / '候选轮廓' / (plan + '.geojson'), {'type': 'FeatureCollection', 'features': [
        {'type': 'Feature', 'properties': {'role': 'raw_indoor_union', 'verified_boundary': False}, 'geometry': mapping(raw)},
        {'type': 'Feature', 'properties': {'role': 'closed_candidate', 'verified_boundary': False}, 'geometry': mapping(candidate)}]})
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project-root', type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    root = args.project_root.resolve()
    out = Path(__file__).resolve().parent
    sample_root = root / 'p-平面标注与数据处理/标注试样'
    paths = sorted(sample_root.glob('[0-9][0-9]_*/annotation.json'))
    assert len(paths) == 53
    for name in ['逐图审计', '候选轮廓', '检查预览']:
        (out / name).mkdir(exist_ok=True)
    sources = [p for folder in [p.parent for p in paths] for p in folder.iterdir() if p.is_file()]
    before = {str(p): sha(p) for p in sources}
    save(out / '原文件哈希_检查前.json', before)
    candidates = review_candidates(root / 'p-平面标注与数据处理')
    results = []
    for path in paths:
        result = audit_plan(path, candidates, out)
        results.append(result)
        print(result['plan'][:2], 'errors=', len(result['validation']['errors']),
              'unknown=', result['unknown_types'], 'endpoint_flags=', len(result['opening_endpoint_flags']), flush=True)
    after = {str(p): sha(p) for p in sources}
    totals = {key: sum(r[key] for r in results) for key in [
        'spaces', 'relations', 'unknown_types', 'known_room_field_count', 'known_single_room_candidates',
        'valid_polygon_count', 'opening_count', 'access_without_openings', 'regions']}
    summary = {'plans': len(results), 'totals': totals,
               'formal_structure_valid_plans': sum(r['validation']['valid'] for r in results),
               'metadata_size_matches': sum(r['metadata_size_matches'] for r in results),
               'plans_with_review_evidence': sum(r['review_evidence']['selected'] is not None for r in results),
               'plans_with_unknown_types': sum(r['unknown_types'] > 0 for r in results),
               'plans_with_regions': sum(r['regions'] > 0 for r in results),
               'plans_with_endpoint_flags': sum(bool(r['opening_endpoint_flags']) for r in results),
               'endpoint_flag_count': sum(len(r['opening_endpoint_flags']) for r in results),
               'overlap_pairs': sum(len(r['overlaps']) for r in results),
               'region_issue_count': sum(len(r['region_issues']) for r in results),
               'all_source_files_unchanged': before == after, 'source_file_count': len(before),
               'policy': {'all_53': 'train_candidate', 'test_split': 'deferred_by_user',
                          'boundary_candidates_are_truth': False, 'proposed_masks_are_final': False},
               'plans_summary': [{k: v for k, v in r.items() if k not in ['nodes', 'relation_candidates']} for r in results]}
    save(out / '原文件哈希_检查后.json', after)
    save(out / '审计汇总.json', summary)
    assert before == after, 'Source files changed during audit'
    print(json.dumps({k: v for k, v in summary.items() if k != 'plans_summary'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
