from pathlib import Path
import importlib.util
import json
import xml.etree.ElementTree as ET
from shapely.geometry import Polygon, box

root = Path(__file__).resolve().parents[3]
sample = root / 'p-平面标注与数据处理/标注试样/19_哈尔滨医科大学附属第四医院门诊外科楼'
out = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('annotation_tools', '/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts/annotation_tools.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
ns = '{http://www.w3.org/2000/svg}'
ET.register_namespace('', ns[1:-1])
ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')
tree = ET.parse(sample / '标注.svg')
data = json.loads((sample / 'annotation.json').read_text())
changed = []
for space in data['spaces']:
    group = tree.find('.//' + ns + 'g[@id="' + space['id'] + '"]')
    rect = group.find(ns + 'rect')
    x, y, w, h = [float(rect.get(k)) for k in ['x', 'y', 'width', 'height']]
    poly = Polygon(space['polygon_px'])
    if poly.buffer(.1).covers(box(x, y, x + w, y + h)):
        continue
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
        bw = max(module.visual_width(line, font) for line in lines) + 4
        bh = len(lines) * (font + 1) + 3
        x, y = anchor.x - bw / 2, anchor.y - bh / 2
        if not poly.buffer(-.5).covers(box(x, y, x + bw, y + bh)):
            continue
        for child in list(group):
            if child.tag in {ns + 'rect', ns + 'text'}:
                group.remove(child)
        group.append(module.element('rect', {'x': x, 'y': y, 'width': bw, 'height': bh, 'rx': 1, 'fill': 'white', 'fill-opacity': '.94', 'stroke': color, 'stroke-width': '.6'}))
        for i, line in enumerate(lines):
            group.append(module.txt(x + 2, y + font + 1 + i * (font + 1), line, font, color, True))
        changed.append(space['id'])
        break
    else:
        raise RuntimeError('窄标签仍无法容纳: ' + space['id'])
tree.write(sample / '标注.svg', encoding='unicode', xml_declaration=True)
(out / '窄标签修正记录.json').write_text(json.dumps(changed, indent=2))
print(changed)
