"""Render stable review numbers inside the existing code-defined room outlines."""
import ast
import hashlib
import json
import math
import shutil
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon, box

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1] / '标注试样'
FONT = '/System/Library/Fonts/STHeiti Medium.ttc'
COLORS = ['#2563eb', '#0f766e', '#be123c', '#7c3aed', '#c2410c', '#0369a1']

# Reuse the exact crop grouping, without running the Markdown writer.
tree = ast.parse((BASE / '生成填写材料.py').read_text())
definitions = ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef)
                              and n.name in ['bounds', 'chunks']], type_ignores=[])
exec(compile(definitions, 'crop_definitions', 'exec'))


def choose_badge(image, polygon, number):
    x0,y0,x1,y1 = polygon.bounds
    gray = np.array(image.convert('L'))
    for size in range(42, 13, -2):
        font = ImageFont.truetype(FONT, size)
        width = math.ceil(font.getlength(number)) + 16
        height = size + 14
        if width > x1-x0-6 or height > y1-y0-6:
            continue
        options = []
        for cy in np.linspace(y0+height/2+4, y1-height/2-4, 13):
            for cx in np.linspace(x0+width/2+4, x1-width/2-4, 13):
                rect = (round(cx-width/2), round(cy-height/2),
                        round(cx+width/2), round(cy+height/2))
                if not polygon.covers(box(*rect)):
                    continue
                patch = gray[rect[1]:rect[3], rect[0]:rect[2]]
                ink = float(np.mean(patch < 130))
                # Prefer blank room floor, then a position near the upper left.
                score = ink * 100 + ((cy-y0)/(y1-y0) + (cx-x0)/(x1-x0))*0.03
                options.append((score, rect, font, ink))
        if options:
            best = min(options, key=lambda p:p[0])
            if best[3] < 0.03 or size == 14:
                return best[1], best[2], best[3]
    raise ValueError(('No interior position', number, polygon.bounds))


placements = []
for hospital in range(21, 26):
    project = next(ROOT.glob(f'{hospital}_*'))
    directory = BASE / project.name
    before = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in project.iterdir() if p.is_file()}
    mapping = json.loads((directory / '固定核对映射.json').read_text())
    data = json.loads((project / 'annotation.json').read_text())
    source_width,source_height = data['image']['width'], data['image']['height']
    backup = directory / '房内数字前备份'
    backup.mkdir(exist_ok=True)
    previews = []
    for index,group in enumerate(chunks(mapping), 1):
        start,end = group[0]['number'],group[-1]['number']
        filename = directory / f'局部_{index:02d}_核对{start}-{end}.png'
        saved = backup / filename.name
        if not saved.exists():
            shutil.copy2(filename, saved)
        picture = Image.open(saved).convert('RGB')
        x0,y0,x1,y1 = bounds(group)
        crop = (max(0, math.floor(x0)-75), max(0, math.floor(y0)-75),
                min(source_width, math.ceil(x1)+75), min(source_height, math.ceil(y1)+75))
        cw,ch = crop[2]-crop[0],crop[3]-crop[1]
        rotated = hospital in [21,24,25]
        rw,rh = (ch,cw) if rotated else (cw,ch)
        sx,sy = picture.width/rw,(picture.height-55)/rh
        def transform(point):
            x,y = point[0]-crop[0],point[1]-crop[1]
            if rotated:
                x,y = y,cw-x
            return x*sx,55+y*sy
        draw = ImageDraw.Draw(picture)
        for j,row in enumerate(group):
            polygon = Polygon([transform(point) for point in row['polygon_px']])
            rect,font,ink = choose_badge(picture, polygon, row['number'])
            draw.rounded_rectangle(rect, radius=8, fill='white', outline=COLORS[j], width=3)
            draw.text(((rect[0]+rect[2])/2,(rect[1]+rect[3])/2), row['number'],
                      font=font, anchor='mm', fill=COLORS[j], stroke_width=0)
            assert polygon.covers(box(*rect)), (hospital,row['number'])
            placements.append(dict(hospital=hospital, number=row['number'], id=row['id'],
                                   file=filename.name, rectangle=rect, dark_fraction=ink))
        picture.save(filename)
        previews.append((start if start == end else start+'—'+end, picture.copy()))
    for offset in range(0,len(previews),8):
        selected = previews[offset:offset+8]
        sheet = Image.new('RGB',(1440,math.ceil(len(selected)/2)*620),'white')
        for i,(label,thumbnail) in enumerate(selected):
            thumbnail.thumbnail((700,560))
            x,y=(i%2)*720,(i//2)*620
            ImageDraw.Draw(sheet).text((x+10,y+5),f'{hospital}号 核对{label}',
                font=ImageFont.truetype(FONT,24),fill='black')
            sheet.paste(thumbnail,(x,y+45))
        sheet.save(directory/f'目检页_{offset//8+1:02d}.jpg',quality=92)
    after = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in project.iterdir() if p.is_file()}
    assert before == after, 'Original deliverables changed'
    print(hospital,'room numbers',len(mapping),'local figures',len(previews),'deliverables unchanged',flush=True)
assert len(placements) == 261
(BASE / '房内数字定位记录.json').write_text(json.dumps(placements,ensure_ascii=False,indent=2))
print('Verified 261 badges inside matching room polygons; all sample files unchanged.')
