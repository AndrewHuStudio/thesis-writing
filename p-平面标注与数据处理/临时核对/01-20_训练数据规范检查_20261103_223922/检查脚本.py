"""Read-only audit of hospital annotations and layout training targets."""
from pathlib import Path
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import base64
import json
import math
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from urllib.parse import unquote

from PIL import Image, ImageChops
from shapely.geometry import Polygon, Point, box

ROOT = Path.cwd()
SKILL = Path('/Users/hushili/.codex/skills/outpatient-plan-annotation')
SAMPLES = ROOT / 'p-平面标注与数据处理/标注试样'
STAMP = sys.argv[1] if len(sys.argv) > 1 else datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y%m%d_%H%M%S')
OUT = ROOT / 'p-平面标注与数据处理/临时核对' / ('01-20_训练数据规范检查_' + STAMP)
TYPES = json.loads((SKILL / 'references/space-types.json').read_text())
NS = '{http://www.w3.org/2000/svg}'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def indoor(s):
    return s['type'] not in {'landscape', 'courtyard'} and s['level'] != 'landscape'


def graph_diagnostics(spaces, relations):
    nodes = {s['id']: s for s in spaces if indoor(s)}
    adjacency = {sid: set() for sid in nodes}
    for r in relations:
        a, b = r.get('source'), r['target']
        if r['type'] == 'access' and a in nodes and b in nodes:
            adjacency[a].add(b)
            adjacency[b].add(a)
    unseen, components = set(nodes), []
    while unseen:
        stack, component = [min(unseen)], []
        while stack:
            sid = stack.pop()
            if sid not in unseen:
                continue
            unseen.remove(sid)
            component.append(sid)
            stack.extend(adjacency[sid] & unseen)
        components.append(sorted(component))
    signatures = {sid: (s['type'], s['level']) for sid, s in nodes.items()}
    colors = {sig: i for i, sig in enumerate(sorted(set(signatures.values())))}
    labels = {sid: colors[sig] for sid, sig in signatures.items()}
    previous_count = len(set(labels.values()))
    for _ in nodes:
        signatures = {sid: (labels[sid], tuple(sorted(labels[n] for n in neighbors)))
                      for sid, neighbors in adjacency.items()}
        colors = {sig: i for i, sig in enumerate(sorted(set(signatures.values())))}
        labels = {sid: colors[sig] for sid, sig in signatures.items()}
        count = len(set(labels.values()))
        if count == previous_count:
            break
        previous_count = count
    groups = defaultdict(list)
    for sid, label in labels.items():
        groups[label].append(sid)
    symmetric = [sorted(ids) for ids in groups.values()
                 if sum(nodes[sid]['level'] == 'room' for sid in ids) > 1]
    isolated = [{'id': sid, 'name': s['name'], 'type': s['type']}
                for sid, s in nodes.items() if s['level'] == 'room' and not adjacency[sid]]
    return dict(component_sizes=sorted(map(len, components), reverse=True),
                isolated_rooms=isolated, indistinguishable_room_groups=symmetric)


def audit(folder):
    path = folder / 'annotation.json'
    data = json.loads(path.read_text())
    cmd = [sys.executable, str(SKILL / 'scripts/annotation_tools.py'),
           'validate', str(path), '--check-dir']
    process = subprocess.run(cmd, text=True, capture_output=True)
    try:
        formal = json.loads(process.stdout)
    except json.JSONDecodeError:
        formal = {'valid': False, 'errors': [process.stdout, process.stderr]}
    spaces, relations = data['spaces'], data['relations']
    polygons = {s['id']: Polygon(s['polygon_px']) for s in spaces}
    nodes = {s['id']: s for s in spaces}
    total_area = sum(polygons[s['id']].area for s in spaces if indoor(s))
    ratio_errors = []
    for s in spaces:
        if indoor(s):
            expected = polygons[s['id']].area / total_area
            if abs(s.get('area_ratio', 0) - expected) > 1e-7:
                ratio_errors.append({'id': s['id'], 'stored': s.get('area_ratio'),
                                     'expected': expected})
    with Image.open(folder / data['image']['file']) as img:
        actual_size = list(img.size)
    expected_size = [data['image']['width'], data['image']['height']]
    root = ET.parse(folder / '标注.svg').getroot()
    display_transform = root.get('data-display-transform')
    rotated = display_transform == 'x_display=y_original;y_display=2444-x_original'
    def display_point(point):
        return [point[1], data['image']['width'] - point[0]] if rotated else point
    svg_spaces = {e.get('id'): e for e in root.iter() if e.get('id') in nodes}
    svg_errors = []
    svg_geometry_errors = []
    for sid, s in nodes.items():
        group = svg_spaces.get(sid)
        if group is None:
            svg_errors.append({'id': sid, 'error': 'missing space group'})
            continue
        text = ''.join(''.join(e.itertext()) for e in group.iter(NS + 'text'))
        plain = re.sub(r'\s+', '', text)
        for value in [sid, s['name'], '〔' + TYPES[s['type']] + '〕']:
            if re.sub(r'\s+', '', value) not in plain:
                svg_errors.append({'id': sid, 'error': 'visible text mismatch', 'expected': value})
        for key, expected in [('data-space-name', s['name']), ('data-space-type', s['type'])]:
            if group.get(key) != expected:
                svg_errors.append({'id': sid, 'error': key, 'expected': expected})
        drawn = list(group.iter(NS + 'polygon'))
        try:
            coordinates = [list(map(float, p.split(','))) for p in drawn[0].get('points').split()]
            expected_polygon = Polygon([display_point(p) for p in s['polygon_px']])
            difference = Polygon(coordinates).symmetric_difference(expected_polygon).area
            if len(drawn) != 1 or difference > 1e-4:
                svg_geometry_errors.append({'id': sid, 'difference_area_px2': difference})
        except (IndexError, ValueError, AttributeError):
            svg_geometry_errors.append({'id': sid, 'error': 'missing or invalid polygon'})
    for r in relations:
        if r['type'] != 'entrance':
            continue
        group = next((e for e in root.iter() if e.get('id') == r['id']), None)
        circles = list(group.iter(NS + 'circle')) if group is not None else []
        if len(circles) != 1 or any(abs(float(circles[0].get(k)) - v) > .01
                for k, v in zip(('cx', 'cy'), display_point(r['position_px']))):
            svg_geometry_errors.append({'id': r['id'], 'error': 'entrance marker mismatch'})
    backgrounds = list(root.iter(NS + 'image'))
    background_matches = False
    if len(backgrounds) == 1:
        href = backgrounds[0].get('{http://www.w3.org/1999/xlink}href', '')
        if href.startswith('data:') and ';base64,' in href:
            raw = base64.b64decode(href.split(',', 1)[1])
            background_matches = hashlib.sha256(raw).hexdigest() == digest(folder / data['image']['file'])
            if not background_matches:
                import io
                with Image.open(folder / data['image']['file']) as original:
                    expected = original.convert('RGB')
                    if rotated:
                        expected = expected.transpose(Image.Transpose.ROTATE_90)
                    with Image.open(io.BytesIO(raw)) as embedded:
                        actual = embedded.convert('RGB')
                        background_matches = expected.size == actual.size and ImageChops.difference(expected, actual).getbbox() is None
    md = (folder / '标注说明.md').read_text()
    missing_images = []
    for target in re.findall(r'!\[[^\]]*\]\(([^\n]*?)\)', md):
        target = target.strip().strip('<>')
        if not re.match(r'https?://|data:', target):
            local = unquote(target.split('#')[0])
            if not (folder / local).exists():
                missing_images.append(target)
    room_shapes, room_boxes = [], []
    for s in spaces:
        if s['level'] == 'room':
            poly = polygons[s['id']]
            bounding = box(*poly.bounds)
            room_shapes.append({'id': s['id'], 'name': s['name'],
                                'bbox_fill': poly.area / bounding.area,
                                'type': s['type']})
            room_boxes.append((s['id'], bounding))
    box_overlaps = []
    for i, (a, pa) in enumerate(room_boxes):
        for b, pb in room_boxes[i + 1:]:
            inter = pa.intersection(pb).area
            ratio = inter / min(pa.area, pb.area)
            if inter > 1 and ratio > 0.05:
                box_overlaps.append({'a': a, 'b': b, 'overlap_over_smaller_box': ratio})
    opening_distances = []
    for r in relations:
        for o in r.get('openings', []):
            point = Point(o['position_px'])
            a, b = polygons[r['source']], polygons[r['target']]
            da, db = point.distance(a.boundary), point.distance(b.boundary)
            opening_distances.append({'id': o['id'], 'relation': r['id'],
                                      'source': r['source'], 'target': r['target'],
                                      'boundary_distance_px': [da, db],
                                      'max_distance_px': max(da, db)})
    vague = [s for s in spaces if re.search(r'unknown|unconfirmed|undetermined|unclassified', s['scope'])]
    feature_order = ['type:' + t for t in sorted({s['type'] for s in spaces})]
    feature_order += ['level:' + t for t in sorted({s['level'] for s in spaces})]
    return dict(project=folder.name, annotation=str(path.relative_to(ROOT)),
                formal_command=cmd, formal_exit_code=process.returncode, formal=formal,
                spaces=len(spaces), rooms=len(room_shapes), relations=len(relations),
                openings=len(opening_distances),
                levels=dict(Counter(s['level'] for s in spaces)),
                types=dict(Counter(s['type'] for s in spaces)),
                scopes=dict(Counter(s['scope'] for s in spaces)),
                relation_types=dict(Counter(r['type'] for r in relations)),
                access_without_openings=sum(r['type'] == 'access' and not r.get('openings') for r in relations),
                actual_image_size=actual_size, declared_image_size=expected_size,
                image_size_matches=actual_size == expected_size,
                area_ratio_sum=sum(s.get('area_ratio', 0) for s in spaces),
                area_ratio_errors=ratio_errors, svg_label_errors=svg_errors,
                svg_geometry_errors=svg_geometry_errors, svg_background_matches=background_matches,
                svg_display_transform=display_transform,
                missing_embedded_images=missing_images,
                rooms_bbox_fill_below_08=[s for s in room_shapes if s['bbox_fill'] < .8],
                room_bbox_overlaps_above_05=sorted(box_overlaps, key=lambda x: -x['overlap_over_smaller_box']),
                openings_over_20px_from_either_boundary=sorted(
                    [o for o in opening_distances if o['max_distance_px'] > 20],
                    key=lambda x: -x['max_distance_px']),
                vague_scope_count=len(vague),
                vague_scope_examples=[{'id': s['id'], 'name': s['name'], 'scope': s['scope']} for s in vague[:12]],
                composite_name_review_candidates=[{'id': s['id'], 'name': s['name']} for s in spaces
                    if s['level'] == 'room' and re.search(r'、|[／/＋+]|男.*女|女.*男|组合', s['name'])],
                pilot_feature_order_if_whole_plan=feature_order,
                graph=graph_diagnostics(spaces, relations),
                scope_boundary_relations=sum(nodes[r['source']]['scope'] != nodes[r['target']]['scope']
                    for r in relations if r.get('source') in nodes and r['target'] in nodes))


def write_report(results, source_unchanged, hashes_before, hashes_after):
    levels, types, relations, scopes = Counter(), Counter(), Counter(), Counter()
    for r in results:
        levels.update(r['levels']); types.update(r['types'])
        relations.update(r['relation_types']); scopes.update(r['scopes'])
    totals = {key: sum(r[key] for r in results) for key in
              ['spaces', 'rooms', 'relations', 'openings', 'access_without_openings', 'vague_scope_count']}
    failures = [r['project'] for r in results if r['formal_exit_code'] != 0]
    errors = {key: sum(len(r[key]) for r in results) for key in
              ['area_ratio_errors', 'svg_label_errors', 'svg_geometry_errors', 'missing_embedded_images']}
    errors['image_size_mismatch'] = sum(not r['image_size_matches'] for r in results)
    errors['svg_background_mismatch'] = sum(not r['svg_background_matches'] for r in results)
    summary = dict(created_at=STAMP, scope='01-20 only', source_unchanged=source_unchanged,
                   source_files=len(hashes_before), formal_passed=len(results)-len(failures),
                   formal_failed=failures, totals=totals, levels=dict(levels), types=dict(types),
                   relation_types=dict(relations), scope_count=len(scopes), scopes=dict(scopes),
                   supplemental_errors=errors,
                   room_bbox_low_fill=sum(len(r['rooms_bbox_fill_below_08']) for r in results),
                   room_bbox_overlap_pairs=sum(len(r['room_bbox_overlaps_above_05']) for r in results),
                   boundary_distance_review_count=sum(len(r['openings_over_20px_from_either_boundary']) for r in results),
                   indistinguishable_room_groups=sum(len(r['graph']['indistinguishable_room_groups']) for r in results))
    payload = dict(summary=summary, cases=results, hashes_before=hashes_before, hashes_after=hashes_after,
                   limitations=['No re-reading of all original labels or doors by eye.',
                                'Boundary distances, disconnected nodes and name hints are review candidates, not semantic errors.',
                                'No model training or dataset export was performed.'])
    (OUT / '检查明细.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
    lines = ['# 01—20 号标注与布局预测训练数据规范检查', '',
             f'检查时间：{STAMP}（Asia/Shanghai）。仅检查01—20；未修改原始四文件。', '',
             f'正式校验：{summary["formal_passed"]}/20 通过；80个来源文件哈希一致：{source_unchanged}。', '',
             '本轮自动检查不能替代原图文字及门洞的逐项视觉判读，也不构成建筑合规或模型效果验收。', '',
             f'补充一致性检查：`{errors}`；包括逐空间面积比例、SVG名称／类别／轮廓／入口坐标、SVG底图像素、原图尺寸和MD嵌入图片路径。20号声明旋转展示，按其显式变换核对轮廓、入口及底图，不能将展示坐标直接与原图坐标比较。', '',
             '## 标注层检查', '',
             '| 编号 | 空间 | room | 关系 | 开口 | 正式校验 | 面积比例逐项不符 | SVG文字不符 | 图片链接失效 |',
             '| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |']
    for r in results:
        values = [r['project'][:2], r['spaces'], r['rooms'], r['relations'], r['openings'],
                  '通过' if r['formal_exit_code'] == 0 else '失败', len(r['area_ratio_errors']),
                  len(r['svg_label_errors']), len(r['missing_embedded_images'])]
        lines.append('| ' + ' | '.join(map(str, values)) + ' |')
    lines += ['', '## 训练数据层发现', '',
              f'- 总计 {totals["spaces"]} 个空间／区域，其中room层级 {totals["rooms"]}；完整层级分布：`{dict(levels)}`。room字段不是逐个物理房间的完整验收结论。',
              f'- 共用type代码 {len(types)} 种；scope取值 {len(scopes)} 种，其中含未定／未分类标记的节点 {totals["vague_scope_count"]} 个。scope尚不能直接当统一科室真值。',
              f'- 无定位开口的概念access共 {totals["access_without_openings"]} 条，属于现有允许语义；不能全部作为直接门洞邻接。shared_wall缺失也不作为无共墙负例。',
              f'- room多边形外接框填充率低于0.8有 {summary["room_bbox_low_fill"]} 个；room外接框重叠超过较小框5%的空间对有 {summary["room_bbox_overlap_pairs"]} 对。外接框训练会损失真实轮廓，也可能让本来不相交的真值多边形变成重叠框。',
              '- 输入必须与监督标签分开：polygon_px及派生坐标是几何目标；area_ratio如作为目标面积输入，须确认新任务也能提供。门位同理。',
              '- 原图像素不是米；新项目的边界、参考方向、尺度如何提供，需要单独定义。面积占比的分母是当前保留标注范围，排除区域不能自动视为已覆盖。',
              '- 20号JSON保持2444×3260原图坐标，SVG旋转为横向展示。训练标签读取JSON；如从SVG取几何，必须应用其显式变换的逆变换。',
              '- 当前试验data.py按单图／scope动态生成type和level词表；多案例训练需要固定共用词表及编码版本。现有build_sample同时计算输入和答案，新任务推理需要不读取答案几何的独立入口。',
              '- 按医院／同源项目分组划分训练、验证、测试；局部scope裁剪仍属于同一来源，不能随机分散至不同集合。裁剪后要处理跨scope的接口关系。', '',
              '## 仅供复核的几何与图诊断', '',
              '以下阈值仅用于排序复核，不能自动证明错误或生成修正。20像素在不同图上的物理尺度不同；未重新目检全部候选。', '',
              '| 编号 | 未定scope节点 | 无门位access | 无access的room | 非室外access连通分量 | 低填充room | 重叠框对 | 开口距任一边界>20px | 同型同构房间组 |',
              '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for r in results:
        values = [r['project'][:2], r['vague_scope_count'], r['access_without_openings'],
                  len(r['graph']['isolated_rooms']), len(r['graph']['component_sizes']),
                  len(r['rooms_bbox_fill_below_08']), len(r['room_bbox_overlaps_above_05']),
                  len(r['openings_over_20px_from_either_boundary']),
                  len(r['graph']['indistinguishable_room_groups'])]
        lines.append('| ' + ' | '.join(map(str, values)) + ' |')
    lines += ['', '同型同构组仅基于type＋level及室内access图诊断；当前确定性消息传递模型缺少区分信息时可能输出相同位置。它不是标注错误，也不表示所有未来模型均无法区分。', '',
              '## 逐图复核线索', '']
    for r in results:
        lines += [f'### {r["project"]}', '',
                  f'- 原数据：[annotation.json](../../{Path(r["annotation"]).relative_to("p-平面标注与数据处理").as_posix()})',
                  f'- 关系类型数量：`{r["relation_types"]}`；跨scope关系 {r["scope_boundary_relations"]} 条。',
                  f'- scope：`{r["scopes"]}`。']
        if r['area_ratio_errors']:
            lines.append('- 面积比例不符：`' + json.dumps(r['area_ratio_errors'][:10], ensure_ascii=False) + '`。')
        if r['room_bbox_overlaps_above_05']:
            lines.append('- 外接框重叠示例：`' + json.dumps(r['room_bbox_overlaps_above_05'][:5], ensure_ascii=False) + '`。')
        if r['openings_over_20px_from_either_boundary']:
            lines.append('- 开口边界距离候选：`' + json.dumps(r['openings_over_20px_from_either_boundary'][:5], ensure_ascii=False) + '`。')
        if r['composite_name_review_candidates']:
            lines.append('- 可能的组合房间名称（仅候选）：`' + json.dumps(r['composite_name_review_candidates'][:8], ensure_ascii=False) + '`。')
        lines.append('')
    (OUT / '检查报告.md').write_text('\n'.join(lines) + '\n')
    return summary


def main():
    folders = [p for p in sorted(SAMPLES.glob('[0-9][0-9]_*'))
               if p.is_dir() and 1 <= int(p.name[:2]) <= 20]
    assert len(folders) == 20
    files = [p for folder in folders for p in folder.iterdir() if p.is_file()]
    before = {str(p.relative_to(ROOT)): digest(p) for p in files}
    OUT.mkdir(parents=True, exist_ok=len(sys.argv) > 1)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(audit, folders))
    after = {str(p.relative_to(ROOT)): digest(p) for p in files}
    summary = write_report(results, before == after, before, after)
    import shutil
    shutil.copy2(__file__, OUT / '检查脚本.py')
    print(json.dumps({'output': str(OUT), 'summary': summary}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
