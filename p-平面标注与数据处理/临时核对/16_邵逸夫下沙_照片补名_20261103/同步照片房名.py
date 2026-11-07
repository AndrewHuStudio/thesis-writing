"""Synchronize readable photo labels; keep all review numbers and uncertain rows."""
from collections import Counter
from hashlib import sha256
from pathlib import Path
import copy
import json
import os
import re
import shutil
import sys
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont
import pymupdf


OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
BASE = ROOT / 'p-平面标注与数据处理'
PROJECT = BASE / '标注试样/16_浙江大学医学院邵逸夫医院下沙院区'
PREV = BASE / '临时核对/16-20_名称核对_20261103' / PROJECT.name
sys.path.insert(0, str(BASE / '临时核对/09-10_连通复核_20261102'))
from 连通工具 import annotation, fit_labels

FONT = '/System/Library/Fonts/STHeiti Medium.ttc'
NS = '{http://www.w3.org/2000/svg}'


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def link(path):
    return os.path.relpath(path, PROJECT)


def photo_panel(rows, photo_lookup, filename):
    columns = min(3, len(rows))
    height = ((len(rows)+columns-1)//columns) * 330 + 65
    canvas = Image.new('RGB', (columns*520, height), '#eef2f7')
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(FONT, 23)
    draw.text((16, 16), '本组仍待补充的名称｜保持原核对号', font=font, fill='#17324d')
    for i, row in enumerate(rows):
        q = photo_lookup[row['number']]
        x, y = i % columns * 520, i // columns * 330 + 65
        label = f"{row['number']}｜{row['id']}｜照片{q['photo']}"
        draw.text((x+12, y+8), label, font=font, fill='#17324d')
        image = Image.open(OUT / q['image'])
        image = image.resize((image.width*2, image.height*2))
        image.thumbnail((490, 265), Image.Resampling.LANCZOS)
        canvas.paste(image, (x+12, y+48))
    canvas.save(filename, quality=96, subsampling=0)


def main():
    original = (PROJECT / '标注说明.md').read_text()
    snapshot = {p.name: digest(p) for p in PROJECT.iterdir() if p.is_file()}
    backup = OUT / '修改前备份'
    assert original == (backup / '标注说明.md').read_text(), '用户文档已变动，请重新读取并保留填写。'
    data = json.loads((PROJECT / 'annotation.json').read_text())
    before = copy.deepcopy(data)
    evidence = json.loads((OUT / '照片判读记录.json').read_text())
    records = json.loads((PREV / '本轮核对映射.json').read_text())
    mapping = {r['number']: r for r in records}
    photos = json.loads((OUT / '备选照片空间对应.json').read_text())
    photo_lookup = {r['number']: r for r in photos}
    spaces = {s['id']: s for s in data['spaces']}
    for number, fact in evidence['confirmed'].items():
        space = spaces[mapping[number]['id']]
        assert space['type'] == 'unknown'
        space.update(name=fact['name'], type=fact['type'])
    assert before['relations'] == data['relations']
    for old, new in zip(before['spaces'], data['spaces']):
        assert {k:v for k,v in old.items() if k not in ['name','type']} == {
            k:v for k,v in new.items() if k not in ['name','type']}
    pending = [r for r in records if spaces[r['id']]['type'] == 'unknown']
    assert {r['number'] for r in pending} == set(evidence['pending'])
    stage = OUT / '待核验成果'
    stage.mkdir(exist_ok=True)
    shutil.copy2(PROJECT / data['image']['file'], stage / data['image']['file'])
    path = stage / 'annotation.json'
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
    annotation.render(data, path, stage / '标注.svg')
    fit_labels(stage / '标注.svg', data)
    # Summary is written outside the live document so its review table survives.
    annotation.summary(data, OUT / '更新概览_仅供核验.md')

    rows_seen, output = [], []
    for line in original.splitlines():
        match = re.match(r'^\| (\d+) \| (S\d+) \|', line)
        if match:
            cells = [c.strip() for c in line.split('|')[1:-1]]
            number, sid = cells[:2]
            assert mapping[number]['id'] == sid and cells[-1] == number
            assert cells[5] == '待确认', (number, cells[5])
            rows_seen.append(number)
            photo = photo_lookup[number]
            image_link = link(OUT / photo['image'])
            proof = f'[照片{photo["photo"]}对应局部]({image_link})'
            if number in evidence['confirmed']:
                fact = evidence['confirmed'][number]
                cells[2:6] = [fact['name'], '—', proof + '；图中文字可辨。把握：高。',
                              '据照片识别并同步；非用户逐项确认']
            else:
                candidate = evidence['candidates'].get(number)
                if candidate:
                    parts = candidate['candidate'].split('／')
                    cells[2:5] = [parts[0], '／'.join(parts[1:]) or '—',
                                  proof + '；' + candidate['basis'] + ' 把握：低，未写入确定房名。']
                else:
                    cells[2:5] = ['暂无可靠候选', '—', proof +
                                  '；仍模糊、无标名或文字不能归属当前分区，依据不足。把握：低。']
            line = '| ' + ' | '.join(cells) + ' |'
        output.append(line)
        found = re.search(r'!\[[^\]]*\]\([^)]*/局部_(\d+)-(\d+)\.jpg\)', line)
        if found:
            a, b = map(int, found.groups())
            subset = [r for r in pending if a <= int(r['number']) <= b]
            if subset:
                filename = OUT / f'剩余照片对照_{a:02d}-{b:02d}.jpg'
                photo_panel(subset, photo_lookup, filename)
                output += ['', f'![本组剩余待确认项的补充照片]({link(filename)})']
    assert rows_seen == [r['number'] for r in records]
    text = '\n'.join(output) + '\n'
    count, done = len(pending), len(evidence['confirmed'])
    text = re.sub(r'^未完成：[^\n]+', f'名称补充进行中：本轮据6张照片落实{done}项；仍有{count}项待补充。', text, count=1, flags=re.M)
    types = Counter(s['type'] for s in data['spaces'])
    text = re.sub(r'\*\*类型与数量：\*\*[^\n]+', '**类型与数量：**' +
                  '、'.join(f'{annotation.TYPE_NAMES[k]} {v} 个' for k,v in types.items()) + '。', text)
    text = re.sub(r'\*\*名称待确认：\*\*[^\n]+', '**名称待确认：**' +
                  '、'.join(f'{r["number"]}／{r["id"]}' for r in pending) + '。本图仍未完成。', text)
    text = text.replace('图面无法可靠辨认的141项名称保留', f'本轮仍无法可靠辨认的{count}项名称保留')
    text = text.replace('现有草稿含 141 项待确认名称；', f'初始草稿共 141 项；本轮已据照片落实 {done} 项，剩余 {count} 项待补充；')
    text = text.replace('候选和依据从本图历史核对记录恢复，仍需对照原图核实；候选未写入 JSON。所有未确认项继续保留 `unknown`，SVG 继续显示“名称未确认”。',
                        '原表固定141行及编号均保留。已读出的名称标为“据照片识别并同步”，同步到JSON及SVG；这不等于用户逐项确认。仍待确认行仅保存候选，JSON继续保留unknown。')
    text = text.replace('![141项名称核对总图]', '![初始141项固定编号定位总图]')
    text = text.replace('**状态：**名称核对材料已备好，标注仍未完成。',
                        f'**状态：**本轮已据照片落实{done}项，原表保留其结果；只需继续填写{count}个“待确认”行，标注仍未完成。')
    groups = Counter(r['group'] for r in pending)
    overview = ['## 本轮照片补名结果', '', f'2026-11-03：依据本次6张照片，补充并同步{done}项清楚可读的名称，剩余{count}项仍需补充。空间总数210、稳定S编号、轮廓、相对面积和35条现有关系保持不变。', '',
                '请继续填写下方原表的“待确认”行；每组表旁新增剩余项的照片对照。疑似文字仅作候选，不补写未读出的房名，也不依据房名猜测门洞或人员可达。', '',
                '| 片区 | 剩余待确认数 |', '| --- | ---: |']
    overview += [f'| {g} | {n} |' for g,n in groups.items()]
    overview += ['', '**照片说明：**保存了用户上传的6张照片；照片局部按原图位置配准，仅用于辨认文字。照片有弯曲和透视，局部边缘可能略有偏差，不能用来改写原图坐标或推定门位。', '',
                 '**关系阶段：**目前35条关系仍是旧草稿记录；本轮仅补名称与功能类别，门洞红点及主要连通关系尚待独立复核。', '']
    text = text.replace('## 名称核对填写表', '\n'.join(overview) + '\n## 名称核对填写表', 1)
    (stage / '标注说明.md').write_text(text)
    for image in re.findall(r'!\[[^\]]*\]\(([^)]+)\)', text):
        assert (PROJECT / image).resolve().is_file(), image
    result, code = annotation.check(data, path, check_dir=True)
    assert code == 2 and result['valid'] and result['errors'] == [] and not result['names_complete'], result
    (OUT / '正式校验.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    svg = ET.parse(stage / '标注.svg')
    for s in data['spaces']:
        group = svg.find(f'.//{NS}g[@id="{s["id"]}"]')
        visible = ''.join(t.text or '' for t in group.iter(NS+'text'))
        assert s['id'] in visible and s['name'] in visible, s['id']
        if s['type'] != 'unknown':
            assert annotation.TYPE_NAMES[s['type']] in visible, s['id']
    for name,h in snapshot.items():
        assert digest(PROJECT / name) == h, 'Live file changed: '+name
    for name in ['annotation.json','标注.svg','标注说明.md']:
        shutil.copy2(stage / name, PROJECT / name)
    assert digest(PROJECT / data['image']['file']) == snapshot[data['image']['file']]
    assert len(list(PROJECT.iterdir())) == 4
    doc = pymupdf.open(PROJECT / '标注.svg')
    page = doc[0]
    page.get_pixmap(matrix=pymupdf.Matrix(.55,.55),alpha=False).save(OUT / '标注全图目检.png')
    for name, rect in [('感染', (195,680,625,1005)), ('儿科', (1035,1080,1357,1675)),
                       ('急诊', (1350,1180,1878,1667)), ('住院支持', (1915,755,2575,1010))]:
        page.get_pixmap(matrix=pymupdf.Matrix(2,2),clip=pymupdf.Rect(rect),alpha=False).save(OUT/f'标注局部_{name}.png')
    print(json.dumps(dict(photo_names_added=done, names_pending=count, spaces=len(data['spaces']),
                         relations=len(data['relations']), geometry_and_relations_unchanged=True,
                         visible_svg_labels=len(data['spaces']), structure_valid=result['valid'],
                         names_complete=False), ensure_ascii=False))


if __name__ == '__main__':
    main()
