"""20号本轮名称同步和内部数字核对图；不改几何或关系。"""
from pathlib import Path
from collections import Counter
import copy
import importlib.util
import json
import re
import sys
import xml.etree.ElementTree as ET

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon, box

from 本轮判读 import CONFIRMED, PENDING

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
PROJECT = ROOT / 'p-平面标注与数据处理/标注试样/20_哈尔滨医科大学附属第一医院门诊保健大楼'
OLD_REVIEW = OUT.parent / '16-20_名称核对_20261103' / PROJECT.name
MD = PROJECT / '标注说明.md'
FONT = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'
CNFONT = '/System/Library/Fonts/STHeiti Medium.ttc'
SPEC = importlib.util.spec_from_file_location('annotation_tools', '/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts/annotation_tools.py')
HELPER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPER)


def read_rows_and_sections(text):
    rows = {}
    sections = []
    for line in text.splitlines():
        if line.startswith('### '):
            sections.append(dict(title=line[4:], ids=[]))
        cells = [s.strip() for s in line.strip('|').split('|')]
        if len(cells) == 7 and re.fullmatch(r'\d+', cells[0]) and re.fullmatch(r'S\d+', cells[1]):
            rows[cells[1]] = cells
            sections[-1]['ids'].append(cells[1])
    return rows, [s for s in sections if s['ids']]


def rotated_polygon(space):
    return Polygon([(y, 2444 - x) for x, y in space['polygon_px']])


def place_number(poly, number, base):
    """只在轮廓内部低墨量空白处放两位数字，优先靠内角。"""
    bounds = poly.bounds
    anchor = poly.representative_point()
    for size in [34, 30, 26, 22, 18, 14, 11]:
        font = ImageFont.truetype(FONT, size)
        b = font.getbbox(number)
        width, height = b[2] - b[0] + 8, b[3] - b[1] + 8
        ww, hh = width / 2, height / 2
        candidates = []
        xs = np.linspace(bounds[0] + ww / 2 + 2, bounds[2] - ww / 2 - 2, 13)
        ys = np.linspace(bounds[1] + hh / 2 + 2, bounds[3] - hh / 2 - 2, 13)
        for y in ys:
            for x in xs:
                rect = box(x - ww / 2, y - hh / 2, x + ww / 2, y + hh / 2)
                if not poly.buffer(-1).covers(rect):
                    continue
                crop = base.crop((int(rect.bounds[0] * 2), int(rect.bounds[1] * 2), int(rect.bounds[2] * 2), int(rect.bounds[3] * 2))).convert('L')
                ink = float(np.mean(np.array(crop) < 95))
                corner = min(x - bounds[0], bounds[2] - x) + min(y - bounds[1], bounds[3] - y)
                candidates.append((ink * 400 + corner * .12, rect, font))
        if candidates:
            return min(candidates, key=lambda c: c[0])[1:]
    raise RuntimeError(f'{number}: 无法在房间内部放置核对号；锚点 {anchor}')


def draw_number(draw, rect, font, number, color):
    b = tuple(v * 2 for v in rect.bounds)
    draw.rounded_rectangle(b, radius=3, fill='white', outline=color, width=2)
    bb = font.getbbox(number)
    draw.text(((b[0] + b[2] - (bb[2] - bb[0])) / 2, (b[1] + b[3] - (bb[3] - bb[1])) / 2 - bb[1]), number, font=font, fill=color)


def create_review_images(data, rows, sections):
    import os
    source = Image.open(OUT / '原图转正.png').convert('RGB').resize((6520, 4888))
    registration = json.loads((OUT / '照片配准.json').read_text())
    photos = {}
    for i in range(1, 5):
        pic = cv2.imread(str(OUT / f'用户照片{i:02d}_转正.jpg'))
        matrix = np.diag([2., 2., 1.]) @ np.linalg.inv(np.array(registration[str(i)]['matrix']))
        warped = cv2.warpPerspective(pic, matrix, (6520, 4888), borderValue=(255, 255, 255))
        photos[i] = Image.fromarray(cv2.cvtColor(warped, cv2.COLOR_BGR2RGB))
    spaces = {s['id']: s for s in data['spaces']}
    polygons = {sid: rotated_polygon(s) for sid, s in spaces.items()}
    positions = {}
    for sid, row in rows.items():
        rect, font = place_number(polygons[sid], row[0], source)
        positions[sid] = (rect, font)
    overview = source.copy()
    draw = ImageDraw.Draw(overview)
    for sid, row in rows.items():
        color = '#14746b' if sid in CONFIRMED else '#b44021'
        draw.line([(x * 2, y * 2) for x, y in polygons[sid].exterior.coords], fill=color, width=2)
        draw_number(draw, *positions[sid], row[0], color)
    overview.save(OUT / '20号_房间内部数字总图.jpg', quality=95)
    audit = []
    for index, section in enumerate(sections, 1):
        ids = section['ids']
        number = int(rows[ids[0]][0])
        photo = 1 if number <= 35 else 3 if number <= 59 else 4 if number <= 70 else 2 if number <= 74 else 4
        bounds = [polygons[sid].bounds for sid in ids]
        crop = (max(0, min(b[0] for b in bounds) - 35), max(0, min(b[1] for b in bounds) - 35), min(3260, max(b[2] for b in bounds) + 35), min(2444, max(b[3] for b in bounds) + 35))
        canvas = photos[photo].copy()
        draw = ImageDraw.Draw(canvas)
        for sid in ids:
            color = '#14746b' if sid in CONFIRMED else '#b44021'
            draw.line([(x * 2, y * 2) for x, y in polygons[sid].exterior.coords], fill=color, width=2)
            draw_number(draw, *positions[sid], rows[sid][0], color)
            audit.append(dict(number=rows[sid][0], id=sid, photo=photo, inside=polygons[sid].covers(positions[sid][0]), marker_box_rotated=list(positions[sid][0].bounds)))
        name = f'{index:02d}_核对{rows[ids[0]][0]}-{rows[ids[-1]][0]}'
        pixel_crop = tuple(int(v * 2) for v in crop)
        result = canvas.crop(pixel_crop)
        # 标题与图例已在现有MD中，局部照片不重复窄幅标题。
        result.save(OUT / (name + '_房间内数字.jpg'), quality=96)
        photos[photo].crop(pixel_crop).save(OUT / (name + '_无标记照片.jpg'), quality=96)
        section['image'] = os.path.relpath(OUT / (name + '_房间内数字.jpg'), PROJECT)
        section['plain'] = os.path.relpath(OUT / (name + '_无标记照片.jpg'), PROJECT)
    (OUT / '数字位置核验.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n')
    assert len(audit) == len(rows) and all(r['inside'] for r in audit)
    return sections


def render_rotated_svg(data):
    rotated = copy.deepcopy(data)
    rotated['image'] = dict(file='原图转正.png', width=3260, height=2444)
    for space in rotated['spaces']:
        space['polygon_px'] = [[y, 2444 - x] for x, y in space['polygon_px']]
    for relation in rotated['relations']:
        if 'position_px' in relation:
            x, y = relation['position_px']; relation['position_px'] = [y, 2444 - x]
    assert not any(r.get('openings') for r in rotated['relations'])
    HELPER.render(rotated, OUT / '显示数据.json', PROJECT / '标注.svg')
    tree = ET.parse(PROJECT / '标注.svg')
    root = tree.getroot()
    root.set('data-source-coordinate-system', 'original-image-2444x3260')
    root.set('data-display-transform', 'x_display=y_original;y_display=2444-x_original')
    tree.write(PROJECT / '标注.svg', encoding='unicode')


def main():
    before = json.loads((PROJECT / 'annotation.json').read_text())
    original_md = MD.read_text()
    rows, sections = read_rows_and_sections(original_md)
    mapping = json.loads((OLD_REVIEW / '本轮核对映射.json').read_text())
    assert [(x['number'], x['id']) for x in mapping] == [(r[0], sid) for sid, r in rows.items()]
    assert set(rows) == set(CONFIRMED) | set(PENDING)
    for record in mapping:
        row = rows[record['id']]
        assert row[2] == record['candidate'].split('／')[0], '预估名称已有人修改，需重新读取并保留'
        assert row[5] == '待确认', '存在新增用户填写，需重新读取并保留'
    data = copy.deepcopy(before)
    for space in data['spaces']:
        if space['id'] in CONFIRMED:
            update = CONFIRMED[space['id']]
            for key in ('name', 'type', 'scope'):
                if key in update:
                    space[key] = update[key]
    for sid, row in rows.items():
        if sid in CONFIRMED:
            r = CONFIRMED[sid]
            row[2] = r['name']; row[3] = '—'
            row[4] = f'【图面已同步】照片{r["photo"]:02d}：{r["basis"]} 把握：高。'
        else:
            candidate, alternative, basis, confidence = PENDING[sid]
            row[2] = candidate; row[3] = alternative
            row[4] = f'【未确认】{basis} 把握：{confidence}。JSON继续unknown。'
    sections = create_review_images(data, rows, sections)
    HELPER.normalize(data)
    assert data['relations'] == before['relations']
    assert [(s['id'], s['polygon_px']) for s in data['spaces']] == [(s['id'], s['polygon_px']) for s in before['spaces']]
    (PROJECT / 'annotation.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    render_rotated_svg(data)
    count = Counter(s['type'] for s in data['spaces'])
    n = count['unknown']
    import os
    relative = os.path.relpath(OUT, PROJECT)
    lines = [
        '# 20号｜哈尔滨医科大学附属第一医院门诊保健大楼｜标注草稿', '',
        f'**未完成：{n} 个空间名称／用途仍未确认；空间范围核对尚未收尾，连通性尚未开始全面复核。**', '',
        f'本轮依据2026-11-03提供的四张局部照片与本图原图对照，新增同步{len(CONFIRMED)}项图面可辨名称及类别。保留113个稳定S编号、88个固定核对号和原确认栏。', '',
        '**范围：**仅当前原图内可辨室内主体。左上翼可辨生活水箱间、消控及机房和部分诊室，不能将整翼直接认作急诊；右下翼已辨急诊药局和急诊急救门厅，中央北侧为住院部门厅及出入院办公。未从其他医院借用名称或范围。图外楼层不在本次范围，未依据照片推定楼层；外部台阶、坡道、雨篷和尺寸轴网不计室内面积。', '',
        '**规模：**113个草稿空间／区域；' + '、'.join(f'{HELPER.TYPE_NAMES[k]} {v}个' for k, v in count.items()) + '。', '',
        '**范围状态：**本轮保留全部原多边形；S107与S109疑为同一急诊药局的两个草稿分片，暂分别保存同名，不能据分片数理解为两个独立药局。S100药房与候药大厅间狭长带、S040等细小范围仍待核。', '',
        '**连接状态：**原有110条关系（102条人员可达、8条入口）原样保留；已定位室内开口0个。本轮只核房名、功能类别和范围，不将现有关系视为已复核，不新增门洞坐标或红点。', '',
        '**坐标与面积：**JSON保持原图2444×3260像素坐标；SVG完整底图逆时针转正，显示变换为`(x转正,y转正)=(y原,2444-x原)`。原图未改，空间相对面积归一化合计为1；概念轮廓不代表实测面积，也不把轴网线当隔墙。', '',
        '## 名称核对填写表', '',
        f'固定核对号01—88不重排，本表保留本轮已同步行供修正；优先填写标有“【未确认】”的{n}行。绿色数字表示图面已同步，橙色表示未确认。数字直接放在房间内部，无外侧标签或长引线。每组照片与填写表相邻，可打开无标记照片看原字。', '',
        '可改“预估名称（可改）”，并在“我的确认／备注”填写“已确认”或实际名称；也可直接补范围修正、合并、排除意见。确认栏沿用原内容，本轮未将自动识字写作用户已确认。聊天可回复`20号：02=名称，05=名称`。', '',
        '【图面已同步】仅表示原注或构造足够清楚，已同步JSON和SVG；【未确认】的候选、依据和把握只保存在本MD，JSON名称继续为“名称未确认”、type为unknown。原候选与旧依据保存在修改前备份。', '',
        f'[查看原图]({data["image"]["file"]})｜[查看标注](标注.svg)｜[打开内部数字总图]({relative}/20号_房间内部数字总图.jpg)', '',
        f'![20号固定核对号总图]({relative}/20号_房间内部数字总图.jpg)', '',
    ]
    for section in sections:
        lines += ['### ' + section['title'], '', f'![{section["title"]}]({section["image"]})', '', f'[查看同范围无标记照片]({section["plain"]})', '',
                  '| 核对号 | S编号 | 预估名称（可改） | 备选名称 | 依据与把握 | 我的确认／备注 | 核对号（重复） |',
                  '| --- | --- | --- | --- | --- | --- | --- |']
        for sid in section['ids']:
            lines.append('| ' + ' | '.join(rows[sid]) + ' |')
        lines.append('')
        if 'S109' in section['ids']:
            lines += ['**范围核对F01（不另分配房名核对号）：**83／S107与85／S109之间只见轴网线、柱，照片未见隔墙；判断为同一急诊药局的可能性高。建议房间核对收尾时保留S107、将S109并入；原83和85两条记录及填写均保留映射。当前仅同步同名，尚未合并，也未改关系。', '', '**我的确认／备注：**待填写（同意合并，或说明实际分隔）', '']
    lines += ['## 本轮状态与后续顺序', '',
              f'- 房名及类别：{len(CONFIRMED)}项已据图面同步，{n}项仍unknown；所有88个核对号保留。',
              '- 范围：原多边形保留，急诊药局合并建议及狭长分带仍待核；本轮不宣称范围完成。',
              '- 连通性：尚未全面复核，原关系仅为草稿；待你说“房间标注完毕”后读取本MD最新填写，落实明确名称、范围、合并或排除，再自主复核主要通路和清晰开口。',
              '- 校验：本轮另运行正式validate --check-dir；结构结果与名称是否齐全分开记录。全图与密集局部目检不代替原图门洞判断。', '']
    MD.write_text('\n'.join(lines))
    audit = dict(updated_names=len(CONFIRMED), pending_names=n, spaces=len(data['spaces']), stable_mapping=[dict(number=r[0], id=sid) for sid, r in rows.items()], confirmations_preserved=all(r[5] == '待确认' for r in rows.values()), geometry_unchanged=True, relations_unchanged=True)
    (OUT / '本轮同步核验.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n')
    (OUT / '本轮名称依据.json').write_text(json.dumps(dict(confirmed=CONFIRMED, pending=PENDING), ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
