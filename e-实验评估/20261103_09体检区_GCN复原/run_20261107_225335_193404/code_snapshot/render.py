"""Readable, proportion-preserving geometry diagrams without matplotlib."""
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from evaluate import boxes


COLORS = {'consultation': '#dbeafe', 'corridor': '#fef3c7', 'hall': '#fde68a',
          'office': '#dcfce7', 'laboratory': '#e9d5ff', 'toilet': '#e5e7eb',
          'waste_handling': '#fecaca', 'staff_support': '#ccfbf1',
          'patient_preparation': '#ffedd5'}


def font(size):
    for path in ['/System/Library/Fonts/PingFang.ttc',
                 '/System/Library/Fonts/STHeiti Light.ttc']:
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


def transform(points, extent_x):
    # Rotate the drawing for reading only; retain original-coordinate predictions.
    return np.column_stack((points[:, 1], extent_x-points[:, 0]))


def comparison(sample, layouts, output, basename='平面对照'):
    """Each layout is (title, boxes or None for original polygons, subtitle)."""
    frame = sample['reference_frame']
    origin, scale = np.asarray(frame['origin_px']), frame['scale_px']
    extent = np.asarray(frame['extent_normalized'])
    records, cloud = [], []
    for title, values, subtitle in layouts:
        items = []
        for i, node in enumerate(sample['nodes']):
            if values is not None and not sample['supervised_mask'][i]:
                continue
            if values is None:
                points = (np.asarray(node['polygon_px']) - origin) / scale
            else:
                x0, y0, x1, y1 = boxes(values)[i]
                points = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]])
            points = transform(points, extent[0])
            items.append((node, points, bool(sample['supervised_mask'][i])))
            cloud.extend(points.tolist())
        records.append((title, subtitle, items))
    cloud = np.asarray(cloud)
    lo, hi = np.minimum(cloud.min(axis=0), 0), cloud.max(axis=0)
    hi = np.maximum(hi, extent[::-1])
    lo -= 0.025
    hi += 0.025
    width, margin = 1700, 65
    factor = (width-2*margin) / (hi[0]-lo[0])
    panel_h = int((hi[1]-lo[1])*factor) + 125
    height = panel_h*len(layouts) + 60
    image = Image.new('RGBA', (width, height), 'white')
    draw = ImageDraw.Draw(image)
    svg = ET.Element('svg', xmlns='http://www.w3.org/2000/svg',
                     width=str(width), height=str(height), viewBox=f'0 0 {width} {height}')
    ET.SubElement(svg, 'rect', width='100%', height='100%', fill='white')

    def text(x, y, message, size=21, fill='#172033'):
        draw.text((x, y), message, font=font(size), fill=fill)
        elem = ET.SubElement(svg, 'text', x=str(x), y=str(y+size),
                             fill=fill, **{'font-size': str(size),
                                          'font-family': 'PingFang SC, sans-serif'})
        elem.text = message

    for panel, (title, subtitle, items) in enumerate(records):
        top = panel*panel_h
        text(margin, top+12, title, 27)
        text(margin, top+49, subtitle, 19, '#526071')
        frame_points = transform(np.array([[0, 0], extent]), extent[0])
        frame_points = (frame_points-lo)*factor + [margin, top+93]
        x0, y0 = frame_points.min(axis=0)
        x1, y1 = frame_points.max(axis=0)
        draw.rectangle([x0, y0, x1, y1], outline='#adb5bd', width=2)
        ET.SubElement(svg, 'rect', x=str(x0), y=str(y0), width=str(x1-x0),
                      height=str(y1-y0), fill='none', stroke='#adb5bd',
                      **{'stroke-dasharray': '6 5'})
        # Context is shown only on the reference, never supplied as target geometry.
        for node, points, supervised in items:
            coords = (points-lo)*factor + [margin, top+93]
            xy = [tuple(p) for p in coords]
            color = COLORS.get(node['type'], '#e5e7eb') if supervised else '#d1d5db'
            rgb = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))
            draw.polygon(xy, fill=(*rgb, 135), outline='#405168', width=2)
            elem = ET.SubElement(svg, 'polygon',
                                 points=' '.join(f'{x:.2f},{y:.2f}' for x, y in xy),
                                 fill=color, stroke='#405168',
                                 **{'fill-opacity': '.55', 'data-space-id': node['id']})
            ET.SubElement(elem, 'title').text = node['id']+' '+node['name']
        label_groups = {}
        for node, points, supervised in items:
            # Keep all overlapping polygons; combine labels so counts stay readable.
            key = tuple(np.round(points.flatten()*scale, 2))
            label_groups.setdefault(key, []).append((node, points, supervised))
        for group in label_groups.values():
            node, points, supervised = group[0]
            center = (points.mean(axis=0)-lo)*factor + [margin, top+93]
            if len(group) > 1:
                label = {'consultation': '诊室', 'corridor': '通道',
                         'office': '办公'}.get(node['type'], '空间') + f'×{len(group)}'
            else:
                label = node['id'] + ('*' if not supervised else '')
            text(float(center[0]-23), float(center[1]-9), label, 16)
        draw.line((margin, top+panel_h-5, width-margin, top+panel_h-5),
                  fill='#e5e7eb', width=2)
    text(margin, height-45,
         'S编号仅供核对；灰框是标签参照窗，不是建筑外轮廓。*组合空间不评分。', 20)
    image.convert('RGB').save(output / (basename+'.png'))
    ET.ElementTree(svg).write(output / (basename+'.svg'), encoding='utf-8',
                              xml_declaration=True)


def loss_chart(runs, output):
    width, height = 1500, 650
    image = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(image)
    draw.text((65, 15), '训练损失：同一片区拟合（非验证集曲线）', font=font(26), fill='#172033')
    x0, y0, x1, y1 = 90, 80, 1230, 570
    logs = [np.log10(max(h['normalized_box_mse'], 1e-10))
            for run in runs for h in run['history']]
    low, high = float(np.floor(min(logs))), float(np.ceil(max(logs)))
    steps = max(run['history'][-1]['step'] for run in runs)
    for value in np.linspace(low, high, 6):
        y = y1-(value-low)/(high-low)*(y1-y0)
        draw.line((x0, y, x1, y), fill='#e5e7eb')
        draw.text((12, y-10), f'1e{value:.1f}', font=font(17), fill='#526071')
    palette = ['#2563eb', '#0891b2', '#4f46e5', '#dc2626', '#ea580c', '#c2410c']
    for i, run in enumerate(runs):
        points = [(x0+h['step']/steps*(x1-x0),
                   y1-(np.log10(max(h['normalized_box_mse'], 1e-10))-low)/
                   (high-low)*(y1-y0)) for h in run['history']]
        draw.line(points, fill=palette[i % len(palette)], width=3)
        draw.text((1250, 90+i*45), run['label'], font=font(17),
                  fill=palette[i % len(palette)])
    draw.text((600, 595), '优化步数', font=font(21), fill='#526071')
    image.save(output / '训练曲线.png')
