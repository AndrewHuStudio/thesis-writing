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
        element.text='31｜暨南大学附属第一医院综合楼工程 · 照片名称回填草稿'
root.set('data-display-rotation','counterclockwise-90')
tree.write(svg,encoding='unicode')

FONT = '/System/Library/Fonts/STHeiti Medium.ttc'
font = lambda size: ImageFont.truetype(FONT,size)
src = Image.open(WORK/'用户补充照片_03.jpg').convert('RGB')
questions = [
    ('核对16_东北空白范围.png',(1000,245,1824,755),[
        ('16',[(1183,285),(1647,282),(1647,482),(1775,480),(1776,700),(1182,708)],(1300,420))]),
    ('核对17_19_20_中央片区.png',(300,675,970,965),[
        ('17',[(329,718),(456,715),(456,872),(328,871)],(346,734)),
        ('19',[(566,714),(701,712),(701,870),(565,871)],(581,733)),
        ('20',[(703,712),(881,713),(881,868),(702,869)],(718,733))]),
]
for filename,crop,items in questions:
    factor = 2
    raw = src.crop(crop).resize(((crop[2]-crop[0])*factor,(crop[3]-crop[1])*factor),Image.Resampling.LANCZOS)
    out = Image.new('RGB',(raw.width,raw.height+70),'white')
    out.paste(raw,(0,70))
    draw = ImageDraw.Draw(out)
    draw.text((16,16),'31号｜用户补充照片｜沿用固定核对号',font=font(29),fill='#17314a')
    for i,(number,points,badge) in enumerate(items):
        color = ['#2563eb','#be123c','#0f766e'][i]
        pts = [((x-crop[0])*factor,(y-crop[1])*factor+70) for x,y in points]
        draw.line(pts+[pts[0]],fill=color,width=5)
        x,y = (badge[0]-crop[0])*factor,(badge[1]-crop[1])*factor+70
        draw.rounded_rectangle((x,y,x+61,y+49),8,fill='white',outline=color,width=3)
        draw.text((x+8,y+6),number,font=font(32),fill=color)
    out.save(WORK/filename)
    src.crop(crop).resize(raw.size,Image.Resampling.LANCZOS).save(WORK/filename.replace('.png','_无标记.png'))

rel = lambda f: os.path.relpath(f,PROJECT)
lines = ['# 31_暨南大学附属第一医院综合楼工程｜标注草稿','',
    '<!-- annotation:summary:start -->','概览待更新','<!-- annotation:summary:end -->','',
    '已依据本轮5张照片回填22项空缺，并纠正7处旧稿名称。名称依据为图中文字判读；剩余4项沿用原核对号。连通关系及门洞尚未进入本轮复核。','',
    '## 待确认名称与范围','',
    '可在“我的确认／备注”栏填写用途或范围，也可聊天回复“31号 16=……”。确定为庭院／挑空的空间不计面积，无须另答有无顶盖。','',
    '### 核对16｜S040 东北空白区域','',
    f'![核对16东北范围]({rel(WORK/questions[0][0])})','',
    '**问题：**蓝框空白区域属于室外平台、预留室内空间，还是本层不应纳入的投影／空白范围？','',
    '**我的判断：**照片仍无房名；仅有轴网和独立交通核，现有证据不足以确定范围属性。','',
    '| 核对号 | S编号 | 预估名称（可改） | 备选名称 | 依据与把握 | 我的确认／备注 | 核对号（重复） |',
    '| --- | --- | --- | --- | --- | --- | --- |',
    '| 16 | S040 | 暂无可靠名称 | 室外平台／预留空间／不纳入本层 | 无用途文字，无法据空白与轴网判断。把握：低。 | 待确认 | 16 |','',
    '### 核对17、19、20｜S042、S044、S045 中央片区','',
    f'![核对17、19、20中央片区]({rel(WORK/questions[1][0])})','',
    '**问题：**17、19两块放射状图案区域分别是什么空间？20条带区域是什么用途？','',
    '**我的判断：**这三处未见独立房名；上方另一处同类图案已读为“候药厅”，因此不能仅按图案把17、19判为庭院。中间已读清的“公共电梯厅”对应S043，不是这三项。','',
    '| 核对号 | S编号 | 预估名称（可改） | 备选名称 | 依据与把握 | 我的确认／备注 | 核对号（重复） |',
    '| --- | --- | --- | --- | --- | --- | --- |',
    '| 17 | S042 | 暂无可靠名称 | 候厅／庭院／景观区 | 放射状图案无独立文字；图案不能区分用途。把握：低。 | 待确认 | 17 |',
    '| 19 | S044 | 暂无可靠名称 | 候厅／庭院／景观区 | 与17类似，不能自动采用上方候药厅名称。把握：低。 | 待确认 | 19 |',
    '| 20 | S045 | 暂无可靠名称 | 交通设施／其他区域 | 密集平行线条，未读到名称；不据线条直接判为扶梯。把握：低。 | 待确认 | 20 |','']
(PROJECT/'标注说明.md').write_text('\n'.join(lines))

manifest_path = BATCH/'材料清单.json'
manifest = json.loads(manifest_path.read_text())
for item in manifest:
    if item['project']==REVIEW.name:
        item.update(pending=4,local_groups=2,last_update='2026-11-06照片回填',resolved_from_photos=22)
manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
entry = BATCH/'核对入口.md'
text = entry.read_text()
text = re.sub(r'(\| 31 \| [^\n]*? \| 91 \| )26( \|)',r'\g<1>4\2',text)
text = text.replace('核对总图、59组局部图、无标记原图、固定映射、review_state、旧说明和四文件备份均在本目录对应项目下。原图、JSON、SVG未改动。',
    '核对图、固定映射、review_state和备份均在本目录对应项目下。31号已根据照片回填22项并纠正7处旧稿名称，剩余4项；其余图保持原草稿状态。')
entry.write_text(text)
print('Updated upright SVG, remaining-question Markdown, and batch entry')
