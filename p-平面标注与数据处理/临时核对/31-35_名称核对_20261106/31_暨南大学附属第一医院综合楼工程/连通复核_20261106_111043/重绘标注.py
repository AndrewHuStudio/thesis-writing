"""Render upright SVG and concise remaining questions with stable review numbers."""
import copy
import importlib.util
import json
import math
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon, box

WORK = Path(__file__).resolve().parent
REVIEW = WORK.parent
BATCH = REVIEW.parent
PROJECT = BATCH.parents[1] / '标注试样' / REVIEW.name
SAMPLE = PROJECT / 'annotation.json'
SKILL = Path('/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts')
sys.path.insert(0,str(SKILL))
spec = importlib.util.spec_from_file_location('annotation_tools',SKILL/'annotation_tools.py')
at = importlib.util.module_from_spec(spec)
spec.loader.exec_module(at)
data = json.loads(SAMPLE.read_text())
at.normalize(data)
SAMPLE.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
display = copy.deepcopy(data)
w,h = data['image']['width'],data['image']['height']
display['image'].update(width=h,height=w)
for s in display['spaces']:
    s['polygon_px'] = [[y,w-x] for x,y in s['polygon_px']]
for r in display['relations']:
    if 'position_px' in r:
        x,y = r['position_px']
        r['position_px'] = [y,w-x]
    for opening in r.get('openings',[]):
        x,y = opening['position_px']
        opening['position_px'] = [y,w-x]
svg = PROJECT/'标注.svg'
at.render(display,SAMPLE,svg)
tree = ET.parse(svg)
root = tree.getroot()
ns = {'s':at.NS}
image = root.find('.//s:image',ns)
image.set('width',str(w))
image.set('height',str(h))
transform = f'matrix(0 -1 1 0 0 {w})'
image.set('transform',transform)
byid = {s['id']:s for s in data['spaces']}
for group in root.findall('.//s:g',ns):
    sid = group.get('id')
    if sid in byid:
        polygon = group.find('s:polygon',ns)
        polygon.set('points',' '.join(f'{x},{y}' for x,y in byid[sid]['polygon_px']))
        polygon.set('transform',transform)
        shape = Polygon([[y,w-x] for x,y in byid[sid]['polygon_px']])
        label = group.find('s:rect',ns)
        lx,ly,lw,lh = [float(label.get(k)) for k in ['x','y','width','height']]
        if not shape.covers(box(lx,ly,lx+lw,ly+lh)):
            space = byid[sid]
            text = sid+' '+space['name']+'〔'+at.TYPE_NAMES[space['type']]+'〕'
            anchor = shape.representative_point()
            for size in [7,6,5]:
                lw,lh = at.visual_width(text,size)+8,size+8
                x,y = anchor.x-lw/2,anchor.y-lh/2
                if shape.covers(box(x,y,x+lw,y+lh)):
                    break
            else:
                raise ValueError(('Cannot fit label',sid))
            label.set('x',str(x));label.set('y',str(y))
            label.set('width',str(lw));label.set('height',str(lh))
            for node in group.findall('s:text',ns):
                group.remove(node)
            group.append(at.txt(x+4,y+size+3,text,size,label.get('stroke'),True))
    oid = group.get('data-opening-id')
    if oid:
        relation = next(r for r in data['relations'] if r['id']==group.get('data-relation-id'))
        opening = next(o for o in relation['openings'] if o['id']==oid)
        circle = group.find('s:circle',ns)
        circle.set('cx',str(opening['position_px'][0]))
        circle.set('cy',str(opening['position_px'][1]))
        circle.set('transform',transform)
for element in root.findall('.//s:text',ns):
    element.set('font-family','STHeiti, Arial Unicode MS, sans-serif')
    if element.text=='门诊平面结构化标注':
        element.text='31｜暨南大学附属第一医院综合楼工程 · 连通与门洞复核'
root.set('data-display-rotation','counterclockwise-90')
tree.write(svg,encoding='unicode')

# Move narrow-room and entrance labels away from already verified red points.
from shapely.geometry import Point
tree = ET.parse(svg)
root = tree.getroot()
for gid, dx, dy in [('E008', 110, 0), ('S086', -45, 0)]:
    group = root.find(f'.//s:g[@id="{gid}"]', ns)
    for child in group:
        if child.tag in ['{'+at.NS+'}rect', '{'+at.NS+'}text']:
            child.set('x', str(float(child.get('x'))+dx))
            child.set('y', str(float(child.get('y'))+dy))
    leader = group.find('s:line', ns)
    if leader is not None:
        leader.set('x2', str(float(leader.get('x2'))+dx))
        leader.set('y2', str(float(leader.get('y2'))+dy))
obstacles = []
for group in root.findall('.//s:g', ns):
    if group.get('id', '').startswith(('S', 'E')):
        rect = group.find('s:rect', ns)
        if rect is not None:
            x, y, rw, rh = [float(rect.get(k)) for k in ['x','y','width','height']]
            obstacles.append(box(x-2, y-2, x+rw+2, y+rh+2))
positions = {o['id']: (o['position_px'][1], w-o['position_px'][0])
             for r in data['relations'] for o in r.get('openings', [])}
used = []
for group in root.findall('.//s:g', ns):
    oid = group.get('data-opening-id')
    if not oid:
        continue
    px, py = positions[oid]
    label = group.find('s:text', ns)
    size = float(label.get('font-size'))
    tw = at.visual_width(oid, size)+2
    offsets = [(7,-7), (7,16), (-tw-7,-7), (-tw-7,16),
               (10,-18), (-tw-10,-18), (10,27), (-tw-10,27)]
    offsets += [(dx,dy) for dy in [-30,38,-42,50,-54,62]
                for dx in [7,-tw-7,30,-tw-30]]
    for dx, dy in offsets:
        x, y = px+dx, py+dy
        bounds = box(x-1, y-size-1, x+tw+1, y+3)
        if any(bounds.intersects(ob) for ob in obstacles+used):
            continue
        if any(bounds.distance(Point(qx,qy)) < 6 for other,(qx,qy) in positions.items() if other != oid):
            continue
        label.set('x', str(x)); label.set('y', str(y))
        if abs(dy) > 27 or abs(dx) > tw+10:
            end_x = x if dx > 0 else x+tw
            group.insert(1, at.element('line', {'x1':px,'y1':py,
                'x2':end_x,'y2':y-size/2,'stroke':'#b91c1c',
                'stroke-width':'.7','opacity':'.75'}))
        used.append(bounds)
        break
    else:
        raise ValueError(('Cannot place opening label', oid))
tree.write(svg, encoding='unicode')

