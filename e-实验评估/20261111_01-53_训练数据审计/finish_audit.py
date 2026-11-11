"""Compile auditable findings and proposed training uses; no source edits."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def main():
    summary = json.loads((ROOT / '审计汇总.json').read_text())
    records = [json.loads(p.read_text()) for p in sorted((ROOT / '逐图审计').glob('*.json'))]
    types, scopes, levels = Counter(), Counter(), Counter()
    svg_issues, area_issues, position_aliases = [], [], []
    max_roundtrip_error = 0
    endpoint_thresholds = {str(t): 0 for t in [1, 2, 5, 10, 20, 50]}
    relative_thresholds = {str(t): 0 for t in [.001, .002, .005, .01, .02]}
    combinations = []
    nodes_out, relations_out, pool = [], [], []
    source_before = json.loads((ROOT / '原文件哈希_检查前.json').read_text())
    visual_notes = {
        '03': '存在分翼和独立单元；保留多部件边界，不用凸包跨填空地。',
        '13': '原图为拍摄页，见纸张遮挡和轻微透视；边界及尺度提取前检查校正。',
        '16': '页底含另一图残片；仅提取与当前标注对应的楼层范围。',
        '17': '同页可见另一层图；仅提取已标注的主要平面。',
        '27': '同页侧边有另一图残片；未知功能只保留缺失标签状态。',
        '31': '主平面外另有独立标注单元，需确认是否纳入同一可布置域。',
        '40': '存在多个组团/图块，需逐块核对目标层与连接范围，保留多部件表达。',
        '45': '主翼与独立狭长翼之间有室外范围，不自动连成实心大轮廓。',
        '48': '页面上方存在其它总图线条，提取范围限定为当前标注平面。',
        '51': '页底存在另一层残片，按外部记录限定已标注完整平面。',
        '52': '主翼与独立狭长翼分离，需保留组团与室外边界区别。',
        '53': '建筑轮廓、庭院和潜在屋面/室内外范围须结合原图与原核对限制检查。'
    }
    for r in records:
        data = json.loads(Path(r['annotation']).read_text())
        types.update(s['type'] for s in data['spaces'])
        scopes.update(s['scope'] for s in data['spaces'])
        levels.update(s['level'] for s in data['spaces'])
        svg = ET.parse(Path(r['annotation']).parent / '标注.svg').getroot()
        svg_nodes = {e.get('id'): e for e in svg.iter() if e.get('data-space-name') is not None}
        if set(svg_nodes) != {s['id'] for s in data['spaces']}:
            svg_issues.append([r['plan'], 'space_id_set_mismatch'])
        for s in data['spaces']:
            e = svg_nodes.get(s['id'])
            if e is None or e.get('data-space-name') != s['name'] or e.get('data-space-type') != s['type']:
                svg_issues.append([r['plan'], s['id'], 'name_or_type_mismatch'])
        areas = {}
        for s in data['spaces']:
            p = s['polygon_px']
            area = abs(sum(p[i][0] * p[(i+1) % len(p)][1] - p[(i+1) % len(p)][0] * p[i][1] for i in range(len(p)))) / 2
            if s['type'] not in ('landscape', 'courtyard') and s['level'] != 'landscape':
                areas[s['id']] = area
        total = sum(areas.values())
        for s in data['spaces']:
            if s['id'] in areas and abs(s['area_ratio'] - areas[s['id']] / total) > 1e-7:
                area_issues.append([r['plan'], s['id']])
        xmin, ymin, xmax, ymax = r['candidate_envelope']['bbox_px']
        length = max(xmax - xmin, ymax - ymin)
        for s in data['spaces']:
            for x, y in s['polygon_px']:
                xn, yn = (x - xmin) / length, (ymax - y) / length
                max_roundtrip_error = max(max_roundtrip_error, abs(x - (xn * length + xmin)), abs(y - (ymax - yn * length)))
        positions = defaultdict(list)
        for relation in data['relations']:
            for op in relation.get('openings', []):
                positions[tuple(op['position_px'])].append({'opening': op['id'], 'relation': relation['id'], 'source': relation['source'], 'target': relation['target']})
        for point, items in positions.items():
            if len(items) > 1:
                position_aliases.append({'plan': r['plan'], 'position_px': point, 'items': items,
                                         'status': 'review_shared_location_not_automatic_duplicate_error'})
        for flag in r['opening_endpoint_flags']:
            distance = max(flag['distance_to_polygons_px'])
            for t in endpoint_thresholds:
                endpoint_thresholds[t] += distance > float(t)
            for t in relative_thresholds:
                relative_thresholds[t] += distance / length > float(t)
        for n in r['nodes']:
            nodes_out.append({'plan': r['plan'], **n})
            if n['level'] == 'room' and n['combined_name_review']:
                combinations.append({'plan': r['plan'], **n})
        priority_relations = {f['relation'] for f in r['opening_endpoint_flags'] if max(f['distance_to_polygons_px']) / length > .01}
        for rel in r['relation_candidates']:
            relations_out.append({'plan': r['plan'], **rel, 'priority_geometry_review': rel['id'] in priority_relations,
                                  'proposed_relation_loss_mask': rel['id'] not in priority_relations,
                                  'proposed_door_position_loss_mask': False,
                                  'policy_note': 'first_layout_experiment_defers_exact_door_regression'})
        pool.append({'plan': r['plan'], 'assignment': 'train_candidate', 'boundary_ready': False,
                     'annotation': r['annotation'], 'node_flags': '节点任务候选.json',
                     'image_sha256': r['source_image_sha256'], 'source_group': r['plan'],
                     'group_status': 'source_plan_id_only_hospital_grouping_deferred',
                     'metric_scale_known': False, 'tensor_exported': False})
    hashes_now = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in source_before}
    assert hashes_now == source_before
    assert len(records) == 53 and len(nodes_out) == 8436 and len(relations_out) == 10182
    assert max_roundtrip_error < 1e-8
    extra = {'svg_space_name_type_issues': svg_issues, 'area_ratio_derivation_issues': area_issues,
             'normalization_roundtrip_max_error_px': max_roundtrip_error,
             'normalization_frame_status': 'provisional_geometry_frame_not_verified_building_boundary',
             'endpoint_distance_gt_px': endpoint_thresholds, 'endpoint_distance_gt_relative_longside': relative_thresholds,
             'shared_opening_positions': position_aliases,
             'types': dict(types), 'levels': dict(levels), 'scope_codes': len(scopes),
             'source_212_files_unchanged': True, 'all_53_overview_images_inspected': True,
             'overview_scope': 'global_image_and_candidate_overlay_only_not_every_room_or_door_semantic_verification',
             'per_plan_overview_notes': visual_notes,
             'all_53_boundary_candidates_remain_unverified': True,
             'all_53_pool_policy': 'train_candidate_no_validation_or_test_split'}
    save(ROOT / '补充检查与总览记录.json', extra)
    save(ROOT / '节点任务候选.json', nodes_out)
    save(ROOT / '关系任务候选.json', relations_out)
    save(ROOT / '训练候选池_53图.json', pool)
    save(ROOT / '组合名称复核_28项.json', combinations)
    save(ROOT / '类别统计.json', {'types': dict(types), 'levels': dict(levels), 'scopes': dict(scopes)})
    lines = ['# 01—53号逐图训练用法清单', '',
             '日期：2026-11-11。全部归入训练候选池，未划分验证/测试集，未导出训练张量。', '',
             '每图均已做结构检查和总览检查；下表的候选房间数使用保守的组合名称筛选，不等于最终语义验收。',
             '所有建筑边界仍需根据原图提取/核验；候选包络分片多不等于建筑真的不连通。', '',
             '| 图号与项目 | 空间 | unknown | 已知room | 保守单房间候选 | 区域 | 定位距离>1%长边 | 外部记录 | 图面处理提示 |',
             '| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |']
    for r in records:
        number = r['plan'][:2]
        length = r['candidate_envelope']['normalization_proposal']['length_px']
        priority = sum(max(f['distance_to_polygons_px']) / length > .01 for f in r['opening_endpoint_flags'])
        note = visual_notes.get(number, '据原图提取外轮廓；保留庭院/室外排除。')
        state = '已匹配' if r['review_evidence']['selected'] else '未定位独立state，保留MD/SVG依据'
        lines.append(f"| [{r['plan']}](逐图审计/{r['plan']}.json) | {r['spaces']} | {r['unknown_types']} | {r['known_room_field_count']} | {r['known_single_room_candidates']} | {r['regions']} | {priority} | {state} | {note} |")
    lines += ['', '组合名称候选：', '', '| 图号 | 空间 | 原名称 |', '| --- | --- | --- |']
    lines += [f"| {r['plan'][:2]} | {r['id']} | {r['name'].replace('|', '／')} |" for r in combinations]
    lines += ['', '组合关键词只触发复核。例如“挂号／收费”“会议／示教室”可能本来就是同一物理房间，不自动拆分或删除。', '',
              '门洞距离最高优先级14项见 [局部图与坐标](门洞距离优先复核.json)。距离提示只用于定位/端点复核，不等于关系已判错。', '',
              '图面预览：紫色为占用包络候选，橙色为缺功能标签节点，青色为明确面积排除项。']
    for i in range(0, 53, 6):
        first, last = records[i]['plan'][:2], records[min(i+5, 52)]['plan'][:2]
        lines += ['', f'![{first}—{last}号总览](检查预览/总览_{first}-{last}.png)']
    (ROOT / '逐图训练用法清单.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps({k: v for k, v in extra.items() if k not in ['shared_opening_positions', 'types', 'levels', 'per_plan_overview_notes']}, ensure_ascii=False, indent=2))
    print('shared_opening_position_groups:', len(position_aliases), 'combined_room_review:', len(combinations))


if __name__ == '__main__':
    main()
