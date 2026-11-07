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
        element.text='31｜暨南大学附属第一医院综合楼工程 · 名称与范围确认已同步'
root.set('data-display-rotation','counterclockwise-90')
tree.write(svg,encoding='unicode')

