"""Apply readable labels from the eight supplied photos, preserving fixed review IDs."""
from pathlib import Path
from collections import Counter
import copy
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import markdown
from PIL import Image

ROOT = Path.cwd()
BASE = ROOT / 'p-平面标注与数据处理'
PROJECT = BASE / '标注试样/12_遂川县人民医院'
OUT = Path(__file__).resolve().parent
PREV = BASE / '临时核对/12_遂川县人民医院_名称核对_20261101'
sys.path.insert(0, str(BASE / '临时核对/09-10_连通复核_20261102'))
from 连通工具 import annotation, fit_labels

CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_formal(path, output):
    result = subprocess.run([sys.executable, str(annotation.__file__), 'validate',
                             str(path), '--check-dir'], capture_output=True, text=True)
    output.write_text(result.stdout + '\n' + result.stderr)
    check = json.loads(result.stdout)
    assert result.returncode == 2 and check['valid'] and not check['errors'], check
    assert not check['names_complete']
    return check


def main():
    stage = OUT / '待核验成果'
    backup = OUT / '修改前备份'
    backup.mkdir(exist_ok=True)
    stage.mkdir(exist_ok=True)
    hashes = {p.name: digest(p) for p in PROJECT.iterdir() if p.is_file()}
    for path in PROJECT.iterdir():
        if path.is_file():
            if (backup / path.name).exists():
                assert digest(path) == digest(backup / path.name), 'Live source changed since snapshot'
            else:
                shutil.copy2(path, backup / path.name)
    evidence = json.loads((OUT / '照片识别记录.json').read_text())
    records = json.loads((PREV / '核对号映射.json').read_text())
    mapped = {r['number']: r['sid'] for r in records}
    original = (PROJECT / '标注说明.md').read_text()
    data = json.loads((PROJECT / 'annotation.json').read_text())
    before = copy.deepcopy(data)
    spaces = {s['id']: s for s in data['spaces']}
    for number, (name, kind, photo) in evidence['confirmed'].items():
        space = spaces[mapped[number]]
        assert space['type'] == 'unknown'
        space.update(name=name, type=kind)
    spaces[mapped['60']]['name'] = '中庭'
    for old, current in zip(before['spaces'], data['spaces']):
        assert {k: v for k, v in old.items() if k not in ['name', 'type']} == {
            k: v for k, v in current.items() if k not in ['name', 'type']}
    assert before['relations'] == data['relations']
    pending = [r for r in records if spaces[r['sid']]['type'] == 'unknown']
    pending_numbers = {r['number'] for r in pending}
    assert pending_numbers == set(evidence['candidates']) | set(evidence['property_pending'])
    assert len(evidence['confirmed']) + len(pending) == 130
    shutil.copy2(PROJECT / data['image']['file'], stage / data['image']['file'])
    (stage / 'annotation.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    annotation.render(data, stage / 'annotation.json', stage / '标注.svg')
    tree = ET.parse(stage / '标注.svg')
    ns = '{http://www.w3.org/2000/svg}'
    courtyard = tree.find(f'.//{ns}g[@id="S090"]')
    rect = courtyard.find(ns + 'rect')
    rect.set('width', '160')
    rect.set('x', str(548.5 - 80))
    labels = courtyard.findall(ns + 'text')
    for label in labels:
        label.set('x', str(548.5 - 76))
    labels[-1].text = '中庭〔性质待确认〕'
    tree.write(stage / '标注.svg', encoding='unicode')
    fit_labels(stage / '标注.svg', data)

    lines = []
    row_numbers = []
    for line in original.splitlines():
        match = re.match(r'^\| (\d+) \| (S\d+) \|', line)
        if match:
            cells = [c.strip() for c in line.split('|')[1:-1]]
            number, sid = cells[:2]
            row_numbers.append(number)
            assert mapped[number] == sid and cells[-1] == number
            assert cells[5].startswith('待确认'), (number, cells[5])
            if number in evidence['confirmed']:
                name, kind, photo = evidence['confirmed'][number]
                cells[2:6] = [name, '—', f'补充照片{photo}。把握：高。',
                              f'{name}；已据照片填入并同步，非用户逐项确认']
            elif number in evidence['candidates']:
                candidate, reason = evidence['candidates'][number]
                cells[2:5] = [candidate, '—', reason + '。把握：低；未写为确定房名。']
                if number == '60':
                    cells[4] = reason + '。名称把握：高；区域性质待确认。'
                    cells[5] = '中庭名称已识别；待补充露天／挑空或室内可步入，及是否计室内面积'
            line = '| ' + ' | '.join(cells) + ' |'
        lines.append(line)
    assert row_numbers == [r['number'] for r in records]
    text = '\n'.join(lines) + '\n'
    count = len(pending)
    text = re.sub(r'^未完成：[^\n]+',
                  f'名称补充进行中：本轮据8张补充照片落实{len(evidence["confirmed"])}项；仍有{count}项名称或区域性质待补充。',
                  text, count=1, flags=re.M)
    counts = Counter(s['type'] for s in data['spaces'])
    text = re.sub(r'\*\*类型与数量：\*\*[^\n]+', '**类型与数量：**' +
                  '、'.join(f'{annotation.TYPE_NAMES[k]} {v} 个' for k, v in counts.items()) + '。', text)
    text = re.sub(r'\*\*名称待确认：\*\*[^\n]+', '**名称或性质待补充：**' +
                  '、'.join(f'{r["number"]}／{r["sid"]}' for r in pending) + '。名称阶段尚未完成。', text)
    text = text.replace('**共130项：112个房间、17个功能块、1个开放区域。** 其中9项还需核对网格、景观或中庭等区域性质及面积口径；这些项包含在130项内，不另计数量。',
                        f'**固定保留原130项及编号；本轮已落实{len(evidence["confirmed"])}项，仍待补充{count}项，其中8项涉及区域性质。** 已识别的行留在原表，方便追溯。')
    text = text.replace('本表依据当前 `annotation.json` 的130个 `unknown` 项与原图逐项对应。已有说明仅列出S编号，本次补充固定核对号、分区定位、候选依据和可填写确认栏。候选不代表已识别或已确认，未将候选写入JSON或正式SVG。',
                        '本表沿用2026-11-01的130项固定映射。2026-11-03依据用户上传的8张照片直接填写清楚可读的名称，并同步JSON和SVG；“照片识别”是助手依据图面落实，不冒称用户逐项确认。尚待确认行的候选不写入核心数据。')
    text = re.sub(r'\*\*区域性质待核：\*\*[^\n]+',
                  '**区域性质待核：**长条网格带、横向网格块及中庭共8项保留unknown及既有草稿面积口径；露天／挑空、绿化或室内可步入的性质另待确认。“中庭”名称已读出。124／S185依据清楚的“导医”文字及服务台记为导医区，沿用室内面积。未为待核区域增加人员可达关系。', text)
    text = text.replace('北侧两翼与中段的临床归属未定，scope 暂用位置范围代码',
                        '本轮补充具体房名，scope 仍沿用位置范围代码')
    groups = Counter(r['group'] for r in pending)
    group_names = {r['group'] for r in records}
    for name in group_names:
        text = re.sub(r'(\| ' + re.escape(name) + r' \| [^|]+ \| )\d+( \|)',
                      lambda m: m[1] + str(groups[name]) + m[2], text)

    def img(filename):
        return '../../临时核对/' + PREV.name + '/' + filename
    focused = [
        '## 本轮只需补充的内容', '',
        f'原130项中已有{len(evidence["confirmed"])}项据照片落实。以下按片区集中剩余问题；设备小间无需逐一补门位。完整填写仍在后方原表。', '',
        '### A｜西北翼部两处小字', '',
        f'![06、13定位]({img("01_西北翼部_核对01-16.png")})', '',
        '**需补充：**06（S008）的科室名称；13（S016）的房名。暂读作“农医科”“消控室”，均未当作确定名称。', '',
        '**填写位置：**下方原表06、13行，可直接填正确名称。', '',
        '### B｜东北翼部房名与空白房间', '',
        f'![22、25、32、35定位]({img("03_东北翼部_核对19-36.png")})', '',
        '**需补充：**22（S036）、32（S052）、35（S055）的文字；25（S043，静脉配液下方大房间）未见房名，请给名称或允许采用的功能名称。', '',
        '**填写位置：**下方原表22、25、32、35行。24（S040）为交通核旁两个辅助小间，暂保留未定，本轮不细究其内部划分。', '',
        '### C｜影像及观察区剩余小字', '',
        f'![38定位]({img("04_纵向中段北部_核对37-57.png")})', '',
        '**需补充：**38（S061）暂读作“打片室”，首字不够清楚。', '',
        f'![70、71定位]({img("05_纵向中段南部_核对58-82.png")})', '',
        '**需补充：**70（S105）、71（S106）两间观察用房的完整名称。', '',
        f'![98定位]({img("08_门诊中排西侧_核对98-106.png")})', '',
        '**需补充：**98（S145）的名称，暂读作“采精”；100（S147）的“抽血”已另行落实。', '',
        '### D｜收费及药房辅助空间', '',
        f'![120、122、123定位]({img("10_门诊南侧西部_核对118-123.png")})', '',
        '**需补充：**122（S191）、123（S192）的房名。120（S182）仅见设备符号，暂保留未定，不要求补内部细节。', '',
        f'![129、130定位]({img("12_门诊南侧东部_核对125-130.png")})', '',
        '**需补充：**129（S190）暂读作“配药”，需要确认；130（S193）未见房名，可稍后补允许采用的功能名称。', '',
        '### E｜8项区域性质，可按相同性质分组回复', '',
        '**需补充：**18、42、58、60、81、88、118、125：分别为露天／挑空、绿化，还是室内可步入区域？60已读出“中庭”；其余网格区域不能单凭图案确定用途。请同时说明是否计入室内面积。各项原表旁保留同号局部图。', '',
        '**填写位置：**下方对应8行。可一次说明哪些编号同属一类；124已依据明确的导医台文字落实为导医区。', '',
        '**阶段状态：**本轮只补名称；既有197个空间编号、轮廓、相对面积及192条关系保持原样。连通性尚未进入本轮复核；原图、原始填写和修改前数据已备份。', '',
    ]
    text = text.replace('## 房间名称与区域性质待确认表（2026-11-01）',
                        '\n'.join(focused) + '\n## 房间名称与区域性质固定核对表（2026-11-01建表，2026-11-03续填）')
    (stage / '标注说明.md').write_text(text)
    for link in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', text):
        assert (PROJECT / link).exists(), link
    run_formal(stage / 'annotation.json', OUT / '正式校验_待核验.json')
    svg = ET.parse(stage / '标注.svg').getroot()
    ns = '{http://www.w3.org/2000/svg}'
    for s in data['spaces']:
        g = svg.find(f'.//{ns}g[@id="{s["id"]}"]')
        visible = ''.join(t.text or '' for t in g.iter(ns + 'text'))
        assert s['id'] in visible, s['id']
        assert s['name'] in visible or (s['type'] == 'unknown' and '名称未确认' in visible), s['id']
    png = OUT / 'SVG实际渲染.png'
    args = [CHROME, '--headless', '--disable-gpu', '--no-first-run',
            '--hide-scrollbars', '--user-data-dir=/tmp/plan12-photo-qa',
            f'--window-size={svg.get("width")},{int(float(svg.get("height")))+1}',
            '--screenshot=' + str(png), (stage / '标注.svg').as_uri()]
    subprocess.run(args, check=True, capture_output=True)
    full = Image.open(png)
    preview = full.copy()
    preview.thumbnail((1100, 1500))
    preview.save(OUT / 'SVG全图预览.jpg', quality=95)
    head = max(65, min(125, data['image']['width'] * .05))
    for name, bounds in [('西北', (350, 550, 1025, 1020)),
                         ('东北', (1420, 565, 2315, 1020)),
                         ('观察', (300, 1580, 870, 2145)),
                         ('门诊', (300, 2140, 1590, 2730))]:
        x1, y1, x2, y2 = bounds
        full.crop((x1, int(y1+head), x2, int(y2+head))).save(OUT / (name + '_标签目检.png'))
    rendered = markdown.markdown(text, extensions=['tables'])
    rendered = re.sub(r'(src|href)="([^"#][^"]*)"',
                      lambda m: m[1] + '="' + html.escape((PROJECT / html.unescape(m[2])).resolve().as_uri()) + '"', rendered)
    page = '<meta charset="utf-8"><style>body{font-family:Arial,sans-serif;max-width:1500px;margin:24px}img{max-width:100%;max-height:650px;object-fit:contain}table{border-collapse:collapse}td,th{border:1px solid #aaa;padding:6px}h2,h3{margin-top:32px}</style>' + rendered
    (OUT / 'MD预览.html').write_text(page)
    subprocess.run([CHROME, '--headless', '--disable-gpu', '--hide-scrollbars',
                    '--user-data-dir=/tmp/plan12-photo-md-qa', '--window-size=1700,2400',
                    '--screenshot=' + str(OUT / 'MD预览首屏.png'), (OUT / 'MD预览.html').as_uri()],
                   check=True, capture_output=True)
    report = {'resolved': len(evidence['confirmed']), 'pending': len(pending),
              'pending_names_or_blocks': len(set(evidence['candidates']) - set(evidence['property_pending'])),
              'pending_property': len(evidence['property_pending']), 'pending_records': pending,
              'before_hashes': hashes, 'image_unchanged': True, 'relations_unchanged': True,
              'ids_geometry_area_unchanged': True, 'review_rows_preserved': len(row_numbers)}
    (OUT / '交付检查_待发布.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ['pending_records', 'before_hashes']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
