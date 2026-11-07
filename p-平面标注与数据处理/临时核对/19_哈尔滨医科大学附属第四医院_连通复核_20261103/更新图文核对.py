from pathlib import Path
from collections import Counter
import html
import importlib.util
import json
import re
import sys
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon, box

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SAMPLE = ROOT / 'p-平面标注与数据处理/标注试样/19_哈尔滨医科大学附属第四医院门诊外科楼'
baseline = json.loads((OUT / '本轮基线.json').read_text())
backup = ROOT / baseline['backup']
original_md = html.unescape((backup / '标注说明.md').read_text())
data = json.loads((SAMPLE / 'annotation.json').read_text())
spaces = {s['id']: s for s in data['spaces']}
answers = {r['id']: r for r in json.loads((OUT / '本轮读取填写.json').read_text())}
pending = [s for s in data['spaces'] if s['type'] == 'unknown']
spec = importlib.util.spec_from_file_location('annotation_tools', '/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts/annotation_tools.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.render(data, SAMPLE / 'annotation.json', SAMPLE / '标注.svg')
module.summary(data, OUT / '本轮概览.md')

# 窄标签完整保留S编号、房名、标准类别，并限制在本空间内部。
ns = '{http://www.w3.org/2000/svg}'
ET.register_namespace('', ns[1:-1])
ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')
tree = ET.parse(SAMPLE / '标注.svg')
label_boxes = []
for space in data['spaces']:
    group = tree.find('.//' + ns + 'g[@id="' + space['id'] + '"]')
    rect = group.find(ns + 'rect')
    x, y, w, h = [float(rect.get(k)) for k in ['x', 'y', 'width', 'height']]
    poly = Polygon(space['polygon_px'])
    if not poly.buffer(.1).covers(box(x, y, x + w, y + h)):
        color = rect.get('stroke')
        anchor = poly.representative_point()
        minx, miny, maxx, maxy = poly.bounds
        name = '名称未确认' if space['type'] == 'unknown' else space['name']
        category = '〔' + module.TYPE_NAMES[space['type']] + '〕'
        for font in [7, 6, 5, 4]:
            width = maxx - minx - 6
            lines = [space['id']] + module.wrap(name, font, width - 4)
            if space['type'] != 'unknown':
                lines += module.wrap(category, font, width - 4)
            w = max(module.visual_width(line, font) for line in lines) + 4
            h = len(lines) * (font + 1) + 3
            x, y = anchor.x - w / 2, anchor.y - h / 2
            if not poly.buffer(-.5).covers(box(x, y, x + w, y + h)):
                continue
            for child in list(group):
                if child.tag in {ns + 'rect', ns + 'text'}:
                    group.remove(child)
            group.append(module.element('rect', {'x': x, 'y': y, 'width': w, 'height': h, 'rx': 1, 'fill': 'white', 'fill-opacity': '.94', 'stroke': color, 'stroke-width': '.6'}))
            for i, line in enumerate(lines):
                group.append(module.txt(x + 2, y + font + 1 + i * (font + 1), line, font, color, True))
            break
        else:
            raise RuntimeError('标签超出轮廓: ' + space['id'])
    label_boxes.append(box(x, y, x + w, y + h))

# 红点不动；P编号在点附近避让房名和其它P编号。
opening_labels = []
for group in tree.findall('.//' + ns + 'g[@data-opening-id]'):
    circle, label = group.find(ns + 'circle'), group.find(ns + 'text')
    x, y = float(circle.get('cx')), float(circle.get('cy'))
    font, width, height = 8, 23, 10
    options = []
    for dx, dy in [(6, -6), (6, 13), (-29, -6), (-29, 13), (6, -18), (-29, -18)]:
        lx, ly = x + dx, y + dy
        rect = box(lx, ly - height, lx + width, ly + 2)
        score = sum(rect.intersection(b).area for b in label_boxes) + 3 * sum(rect.intersection(b).area for b in opening_labels)
        options.append((score, lx, ly, rect))
    _, lx, ly, rect = min(options, key=lambda item: item[0])
    label.set('x', str(lx))
    label.set('y', str(ly))
    label.set('font-size', str(font))
    # MuPDF对paint-order支持不完整；独立白底确保P编号仍为可读红字。
    label.attrib.pop('stroke', None)
    label.attrib.pop('stroke-width', None)
    label.attrib.pop('paint-order', None)
    label.set('fill', '#a61212')
    background = module.element('rect', {'x': lx - 1, 'y': ly - height, 'width': width + 2, 'height': height + 3, 'fill': 'white', 'fill-opacity': '.92', 'rx': 1})
    group.insert(list(group).index(label), background)
    opening_labels.append(rect)
tree.write(SAMPLE / '标注.svg', encoding='unicode', xml_declaration=True)
if '--svg-only' in sys.argv:
    print('仅更新SVG；保留当前MD填写。')
    raise SystemExit(0)

image = Image.open(SAMPLE / data['image']['file']).convert('RGB')
font_path = '/System/Library/Fonts/STHeiti Medium.ttc'

def review_image(filename, crop, sids, labels):
    scale = 3
    canvas = image.crop(crop).resize(((crop[2] - crop[0]) * scale, (crop[3] - crop[1]) * scale))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(font_path, 30)
    for sid in sids:
        points = [((x - crop[0]) * scale, (y - crop[1]) * scale) for x, y in spaces[sid]['polygon_px']]
        draw.line(points + [points[0]], fill='#b45412' if sid in {'S049', 'S050'} else '#216da3', width=3)
        minx, miny, maxx, maxy = Polygon(spaces[sid]['polygon_px']).bounds
        text = labels.get(sid, sid)
        x, y = (minx + 5 - crop[0]) * scale, (miny + 5 - crop[1]) * scale
        bounds = draw.textbbox((x, y), text, font=font)
        draw.rectangle((bounds[0] - 2, bounds[1] - 2, bounds[2] + 2, bounds[3] + 2), fill='white')
        draw.text((x, y), text, font=font, fill='#9f3f0b')
    canvas.save(OUT / filename)

review_image('K01_儿童输液与电梯前室.png', (1560, 850, 2190, 1085), ['S034', 'S035', 'S048', 'S049', 'S050', 'S051', 'S071'], {'S049': '23 S049', 'S050': '24 S050'})

review = original_md.split('## 名称核对填写表', 1)[1]
review = re.sub(r'^.*?(?=^### )', '', review, count=1, flags=re.S | re.M)
updated_lines = []
for line in review.splitlines():
    if not re.match(r'^\|\s*\d+\s*\|', line):
        updated_lines.append(line)
        continue
    cells = [c.strip() for c in line.strip().strip('|').split('|')]
    sid = cells[1]
    answer = answers[sid]['answer']
    if sid not in spaces:
        cells[2] = '地下车库入口' if sid == 'S141' else '已排除'
        cells[4] = '用户明确填写排除；本轮移出JSON和SVG，不参与室内面积归一化，保留原核对号与本行填写以便追溯。'
    elif answer not in {'待确认', '', '待定'}:
        cells[2] = spaces[sid]['name']
        cells[3] = '—'
        cells[4] = '用户填写为“' + answer + '”；已按原名同步JSON/SVG，类别：' + module.TYPE_NAMES[spaces[sid]['type']] + '。原候选及用户填写前版本已备份。'
    elif spaces[sid]['type'] != 'unknown':
        cells[2] = spaces[sid]['name']
        cells[4] = '本行未新增用户确认；沿用上一轮本图已直接辨读并同步的名称。类别：' + module.TYPE_NAMES[spaces[sid]['type']] + '。如需修正，请继续在原确认栏填写。'
    updated_lines.append('| ' + ' | '.join(cells) + ' |')

counts = Counter(r['type'] for r in data['relations'])
located = sum(bool(r.get('openings')) for r in data['relations'])
openings = sum(len(r.get('openings', [])) for r in data['relations'])
overview = (OUT / '本轮概览.md').read_text().replace('# 平面标注概览', '# 19号｜哈尔滨医科大学附属第四医院门诊外科楼（一层）', 1)
notes = f'''
**本轮落实：**读取2026-11-03最新填写，落实71行明确名称（其中40处名称或类别较上轮发生变化）。按用户意见排除84/S141地下车库入口、93/S174和94/S175；不重排其余S编号及01—94核对号。当前174个空间／区域，剩余5个名称unknown：68/S114、69/S115、72/S118、80/S137、81/S138。另15行虽仍写待确认，但已在上一轮按本图可读原注具名，不冒充用户确认。

**范围：**本图一层普通门诊、住院手续办理与交通支持、静点中心、血库、儿科、干部门诊及公共通道。室外台阶、雨篷和轴网不计入。其余原概念单元保留；S029补公共走道西北段、S064补药房门外通道、S027补至西侧门厅的连续通道，均不吞并已标房间。S028/S050按用户填写为电梯前室，S070为厕所前室；其余复合功能名按用户原名记录，不进一步穷尽小间细分。

**连通性本轮初核：**{counts['access']}条人员可达、{counts['service']}条服务联系、{counts['entrance']}条入口连接。{openings}个可定位门洞红点，对应{located}条access；另{counts['access'] - located}条access无定位红点。连续公共地面及未标独立小门的概念连接不编造坐标。E01—E11建筑入口与P编号室内门洞分别保存。

**纠正的主要关系：**S079/S082改接血库内廊S091；S080/S081同时保留可读的北侧入口和南侧内廊门，内部可见门另记。取消静点中心跨过南排房间直连S122的旧边；按图记录S078通向南排单元的门。S067超市和S085鲜花超市从南侧通S093。住院办理S001/S004与大厅的柜台关系改为service，不由柜台推定人员穿行。门诊挂号柜台保留服务联系，同时在可读后台侧门处记录真实access。

**布局推断：**S131候梯厅与西侧公共通道S112、公共大厅中未见实体分隔的连续地面，按图面通行组织保存概念access，不虚构门位。未记录关系不表示不通，也不作为负例。

**本轮不细究的内部细节：**小井道内部、柜台后台通路、S089麻药室及S114附间的未辨清内部开门，不逐项追问精确门位；可见小门已保留定位。交通核作为整体节点，其井道或内部楼梯路线不进一步拆分。东北护士站S034、配药S035和儿童输液／前室区域的关键对外路线统一留在K01核对。

**当前状态：**房名剩5项；范围修正已按本图和用户填写落实；主要连通关系已自主初核，尚有K01关键疑点，不能宣布本图全部完成。正式校验及目检结果将在本轮核验后追加。

## 关键连通核对

### K01｜儿童输液室及电梯前室的对外通路

![K01：固定23/S049和24/S050及邻近公共空间](../../临时核对/{OUT.name}/K01_儿童输液与电梯前室.png)

**问题：**儿童输液室S049、电梯前室S050如何接入公共通道？请指出S049直接相连的是候诊区S048、前室S050还是其他空间；S050与护士站S034／配药S035／交通核S051的实际衔接也可一并说明。

**我的判断：**S049/S050周边墙线较密，当前原图像素不能可靠区分其唯一出口，不能仅从共墙补access。S035与S034之间的门、S051南侧通S071的门已独立记录；缺少的只是这组区域的关键对外解释。

**我的确认／备注：**待填写（写直接相连的S编号或名称即可，无需给门宽或精确门位）。

## 名称核对填写表

固定核对号与填写保留如下。仍需补名的仅68/S114、69/S115、72/S118、80/S137、81/S138；请继续在各自原行的“我的确认／备注”填写，不另设重复答案表。已排除的84、93、94行只留作追溯，不代表仍在JSON中。

[查看原图]({data['image']['file']})｜[查看最新标注](标注.svg)

'''
(SAMPLE / '标注说明.md').write_text(overview + notes + '\n'.join(updated_lines) + '\n')
print({'spaces': len(spaces), 'unknown': len(pending), 'relations': len(data['relations']), 'red_points': openings, 'located_access': located})
