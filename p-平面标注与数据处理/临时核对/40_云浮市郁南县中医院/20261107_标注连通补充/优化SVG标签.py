from pathlib import Path
import xml.etree.ElementTree as ET

OUT = Path(__file__).resolve().parent
SAMPLE = OUT.parents[2] / '标注试样/40_云浮市郁南县中医院'
PATH = SAMPLE / '标注.svg'
NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS)
ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')
tree = ET.parse(PATH)
root = tree.getroot()
for group in root.iter('{' + NS + '}g'):
    if group.get('data-opening-id'):
        text = group.find('{' + NS + '}text')
        text.set('font-size', '11')
        text.set('stroke-width', '.7')
        text.set('fill', '#b91c1c')
    spec = {
        'S007': (475, 250, 168, 30, 12, ['S007 餐饮区通道', '〔通道〕']),
        'S022': (1570, 438, 178, 53, 17, ['S022 普通发热门诊', '〔诊室〕']),
        'S058': (1390, 2623, 116, 67, 18, ['S058 急救', '〔抢救〕']),
    }.get(group.get('id'))
    if not spec:
        continue
    x, y, w, h, size, lines = spec
    for child in list(group):
        if child.tag in ('{' + NS + '}rect', '{' + NS + '}text'):
            group.remove(child)
    ET.SubElement(group, '{' + NS + '}rect', {'x': str(x), 'y': str(y),
        'width': str(w), 'height': str(h), 'rx': '2', 'fill': 'white',
        'fill-opacity': '.94', 'stroke': '#0f766e', 'stroke-width': '.8'})
    for i, line in enumerate(lines):
        e = ET.SubElement(group, '{' + NS + '}text', {'x': str(x + 4),
            'y': str(y + size + 2 + i * (size + 3)), 'font-size': str(size),
            'font-family': 'Arial, PingFang SC, sans-serif',
            'fill': '#0f766e', 'font-weight': 'bold'})
        e.text = line
tree.write(PATH, encoding='unicode')
print('已调整P编号描边和三个狭长区域标签。')
