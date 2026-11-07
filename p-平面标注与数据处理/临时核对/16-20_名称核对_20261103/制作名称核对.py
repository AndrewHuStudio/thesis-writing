"""Restore existing review mappings and add persistent, editable name review sections."""
from collections import defaultdict
from hashlib import sha256
from pathlib import Path
import json
import math
import os
import re
import shutil

from PIL import Image
from shapely.geometry import Polygon

from 核对绘图 import COLORS, make_master, make_panel


OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
SAMPLES = ROOT / 'p-平面标注与数据处理/标注试样'
PLANS = json.loads((OUT / '固定名称核对映射.json').read_text())


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def relative(path, project):
    return os.path.relpath(path, project)


def cell(text):
    return str(text).replace('|', '／').replace('\n', ' ')


def standardize(q):
    candidate = q['candidate'].strip()
    if not candidate or any(w in candidate for w in ['未知', '无可靠', '暂无可靠']):
        candidate = '暂无可靠候选'
    q['candidate'] = candidate
    c = q['confidence']
    q['confidence'] = '高' if c == '高' else '中' if c in ['中', '中高'] else '低'
    basis = q['basis'].strip() or '原图名称无法可靠辨读，依据不足。'
    if candidate == '暂无可靠候选':
        basis += ' 暂无可靠房间用途依据，请填写实际名称。'
        q['confidence'] = '低'
    elif q['confidence'] == '低':
        basis += ' 仅为待核候选，当前文字或房间级证据不足。'
    if '／' in candidate:
        basis += ' 上述候选共用此线索，现有证据不能区分。'
    q['evidence_display'] = basis + f" 把握：{q['confidence']}。"


def chunks(items, spaces):
    result, current = [], []
    for q in items:
        p = Polygon(spaces[q['id']]['polygon_display'])
        if current:
            prev = Polygon(spaces[current[-1]['id']]['polygon_display'])
            far = p.centroid.distance(prev.centroid) > 700
            if len(current) >= 6 or far:
                result.append(current)
                current = []
        current.append(q)
    if current:
        result.append(current)
    return result


def process(plan):
    n = plan['number']
    project = SAMPLES / plan['project']
    target = OUT / plan['project']
    target.mkdir(exist_ok=True)
    md = project / '标注说明.md'
    original_md = md.read_text()
    if '## 名称核对填写表' in original_md:
        raise RuntimeError('已有填写表，需要保留其填写后再续作：' + str(md))
    data = json.loads((project / 'annotation.json').read_text())
    spaces = {s['id']: dict(s) for s in data['spaces']}
    items = plan['items']
    assert {q['id'] for q in items} == {s['id'] for s in spaces.values() if s['type'] == 'unknown'}
    baseline = {p.name: digest(p) for p in project.iterdir() if p.is_file()}
    backup = target / '修改前备份'
    backup.mkdir(exist_ok=False)
    shutil.copy2(md, backup / md.name)
    (target / '修改前文件校验.json').write_text(json.dumps(baseline, ensure_ascii=False, indent=2)+'\n')
    source = Image.open(project / data['image']['file']).convert('RGB')
    for s in spaces.values():
        s['polygon_display'] = s['polygon_px']
    if n == 20:
        source = source.transpose(Image.Transpose.ROTATE_90)
        for s in spaces.values():
            s['polygon_display'] = [[y, data['image']['width']-x] for x, y in s['polygon_px']]
    groups = defaultdict(list)
    for q in items:
        standardize(q)
        groups[q['group']].append(q)
    panels, sections, routes = [], [], []
    for gi, (group, rows) in enumerate(groups.items()):
        color = COLORS[gi % len(COLORS)]
        for q in rows:
            q['color'] = color
        for ci, chunk in enumerate(chunks(rows, spaces), 1):
            first, last = chunk[0]['number'], chunk[-1]['number']
            title = f'{first}—{last}｜{group}'
            filename = f'局部_{first}-{last}.jpg'
            image = target / filename
            audit = make_panel(source, chunk, spaces, title, color, image)
            assert set(audit['paths']) == {q['id'] for q in chunk}
            routes.append(dict(numbers=[q['number'] for q in chunk], **audit))
            panels.append(image)
            sections += [f'### {title}', '', f'![{title}]({relative(image, project)})', '',
                         '| 核对号 | S编号 | 预估名称（可改） | 备选名称 | 依据与把握 | 我的确认／备注 | 核对号（重复） |',
                         '| --- | --- | --- | --- | --- | --- | --- |']
            for q in chunk:
                parts = q['candidate'].split('／')
                sections.append('| ' + ' | '.join(map(cell, [q['number'], q['id'], parts[0],
                                '／'.join(parts[1:]) or '—', q['evidence_display'],
                                '待确认', q['number']])) + ' |')
            sections += ['']
            print(n, first, last, 'panel ready', flush=True)
    master = target / '名称核对总图.jpg'
    make_master(source, items, spaces, panels, f"{n}｜{plan['project'][3:]}", master)
    overview = ['## 名称核对填写表', '', f'本轮整理：2026-11-03。现有草稿含 {len(items)} 项待确认名称；固定核对号和 S 编号沿用原记录。', '',
                '可修改“预估名称（可改）”，并将“我的确认／备注”填为“已确认”；接受原预估时只填“已确认”即可。也可在确认栏直接填写实际名称。空白和“待确认”不视为确认。', '',
                '候选和依据从本图历史核对记录恢复，仍需对照原图核实；候选未写入 JSON。所有未确认项继续保留 `unknown`，SVG 继续显示“名称未确认”。', '',
                f'[查看原图]({data["image"]["file"]})｜[查看现有标注](标注.svg)｜[打开高清核对总图]({relative(master, project)})', '',
                f'![{len(items)}项名称核对总图]({relative(master, project)})', '',
                '按下面各片区的固定核对号阅读，可分批填写。聊天回复请带医院编号，例如 `16号：01=诊室，02=治疗室`，避免不同图的核对号混淆。', '',
                '**状态：**名称核对材料已备好，标注仍未完成。门洞红点及主要连通关系需在名称确认后继续复核；当前已有关系不等于已经全面复核。', '']
    updated = re.sub(r'`/tmp/outpatient'+str(n)+r'-review`',
                     f'[本轮持久核对目录]({relative(target, project)})', original_md)
    # Preserve the existing overview and append the only active editable table.
    updated = updated.rstrip() + '\n\n' + '\n'.join(overview + sections) + '\n'
    assert digest(md) == baseline[md.name], '文档在处理期间被修改，停止写回。'
    md.write_text(updated)
    assert all(digest(project / name) == value for name, value in baseline.items() if name != md.name)
    assert len(list(project.iterdir())) == 4
    for filename in re.findall(r'!\[[^\]]*\]\(([^)]+)\)', updated):
        assert (project / filename).is_file(), filename
    row_pattern = r'^\| (\d+) \| (S\d+) \|.*\| 待确认 \| (\d+) \|$'
    table = re.findall(row_pattern, updated, re.M)
    assert [(a, b) for a, b, c in table] == [(q['number'], q['id']) for q in items]
    assert all(a == c for a, b, c in table)
    (target / '本轮核对映射.json').write_text(json.dumps(items, ensure_ascii=False, indent=2)+'\n')
    (target / '局部引线核验.json').write_text(json.dumps(routes, ensure_ascii=False, indent=2)+'\n')
    return dict(number=n, spaces=len(spaces), unknown=len(items), panels=len(panels),
                names_complete=False, source_json_svg_unchanged=True,
                mapping_complete=True, image_links_valid=True, leader_crossings=0)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', type=int)
    args = parser.parse_args()
    result = []
    for plan in PLANS:
        if args.plan is None or plan['number'] == args.plan:
            result.append(process(plan))
    name = f'材料核验_{args.plan}.json' if args.plan else '材料核验.json'
    (OUT / name).write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(result, ensure_ascii=False))
