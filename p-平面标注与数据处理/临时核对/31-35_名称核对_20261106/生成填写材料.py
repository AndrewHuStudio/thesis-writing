"""Create persistent numbered crops and editable Markdown; preserve core data."""
import hashlib
import json
import math
import os
import re
import shutil
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon, box

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1] / '标注试样'
FONT = '/System/Library/Fonts/STHeiti Medium.ttc'
COLORS = ['#2563eb','#0f766e','#be123c','#7c3aed','#c2410c','#0369a1']


def bounds(rows):
    points = [p for r in rows for p in r['display_polygon']]
    return min(x for x,y in points), min(y for x,y in points), max(x for x,y in points), max(y for x,y in points)


def chunks(rows):
    groups = []
    for r in rows:
        if groups:
            trial = groups[-1]+[r]
            x0,y0,x1,y1 = bounds(trial)
            if len(trial) <= 5 and trial[0]['group'] == r['group'] and x1-x0 < 650 and y1-y0 < 600:
                groups[-1].append(r)
                continue
        groups.append([r])
    return groups


def badge(image, polygon, number):
    x0,y0,x1,y1 = polygon.bounds
    gray = np.array(image.crop((int(x0),int(y0),math.ceil(x1),math.ceil(y1))).convert('L'))
    options = []
    for size in range(24, 7, -2):
        font = ImageFont.truetype(FONT,size)
        w,h = math.ceil(font.getlength(number))+10,size+10
        if w > x1-x0-4 or h > y1-y0-4:
            continue
        for cy in np.linspace(y0+h/2+2,y1-h/2-2,9):
            for cx in np.linspace(x0+w/2+2,x1-w/2-2,9):
                rect = (round(cx-w/2),round(cy-h/2),round(cx+w/2),round(cy+h/2))
                if not polygon.covers(box(*rect)):
                    continue
                patch = gray[max(0,rect[1]-int(y0)):rect[3]-int(y0),
                             max(0,rect[0]-int(x0)):rect[2]-int(x0)]
                ink = float(np.mean(patch < 140)) if patch.size else 1
                score = ink*100 + ((cx-x0)/(x1-x0)+(cy-y0)/(y1-y0))*.02
                options.append((score,rect,size,ink))
        if options and min(options)[3] < .04:
            return min(options)[1:]
    assert options, (number, polygon.bounds)
    return min(options)[1:]


def draw_badge(draw, rect, number, size, color):
    draw.rounded_rectangle(rect, radius=max(2,size//5), fill='white',outline=color,width=max(1,size//12))
    draw.text(((rect[0]+rect[2])/2,(rect[1]+rect[3])/2),number,
              font=ImageFont.truetype(FONT,size),fill=color,anchor='mm')


def field(value):
    return str(value).replace('|','／').replace('\n',' ')


manifest = []
for number in range(31,36):
    project = next(ROOT.glob(f'{number}_*'))
    target = BASE / project.name
    data = json.loads((project / 'annotation.json').read_text())
    rows = json.loads((target / '固定核对映射.json').read_text())
    backup = target / '续作前备份'
    backup.mkdir(exist_ok=True)
    hashes = {}
    for f in project.iterdir():
        if f.is_file():
            if not (backup / f.name).exists():
                shutil.copy2(f,backup / f.name)
            hashes[f.name] = hashlib.sha256((backup / f.name).read_bytes()).hexdigest()
    (target / '续作前SHA256.json').write_text(json.dumps(hashes,ensure_ascii=False,indent=2))
    md = project / '标注说明.md'
    assert '## 房名与范围核对（2026-11-06）' not in md.read_text(), 'Preserve existing answers'
    raw = Image.open(project / data['image']['file']).convert('RGB')
    rotated = number in [31,35]
    if rotated:
        raw = raw.rotate(90,expand=True)
    for r in rows:
        r['display_polygon'] = [(y,data['image']['width']-x) for x,y in r['polygon_px']] if rotated else r['polygon_px']
    placements = []
    for r in rows:
        rect,size,ink = badge(raw,Polygon(r['display_polygon']),r['number'])
        r.update(badge_rect=rect,badge_size=size)
        placements.append(dict(number=r['number'],id=r['id'],rect=rect,size=size,ink_fraction=ink,
                               coordinate_system='upright' if rotated else 'original'))
    (target / '房内编号位置.json').write_text(json.dumps(placements,ensure_ascii=False,indent=2))
    overview = Image.open(target / '完整核对总图.png').convert('RGB')
    od = ImageDraw.Draw(overview)
    scale,ox,oy = {31:(6000/3260,1350,230),32:(1.9,1050,(9000-round(3344*1.9))//2),
                   33:(1,1020,150),34:(1,780,135),35:(1,740,150)}[number]
    for i,r in enumerate(rows):
        rect = [ox+r['badge_rect'][0]*scale,oy+r['badge_rect'][1]*scale,
                ox+r['badge_rect'][2]*scale,oy+r['badge_rect'][3]*scale]
        draw_badge(od,rect,r['number'],round(r['badge_size']*scale),COLORS[i%len(COLORS)])
    overview.save(target / '完整核对总图.png')
    overview.thumbnail((2000,2200))
    overview.save(target / '总图预览.jpg',quality=94)
    rel = lambda p: os.path.relpath(p,project)
    openings = sum(len(r.get('openings',[])) for r in data['relations'])
    lines = [f'# {project.name}｜标注草稿','', '<!-- annotation:summary:start -->',
             f'未完成：{len(rows)} 项名称、用途或范围待确认；主要连通及门洞尚待后续复核。','',
             f'空间 {len(data["spaces"])} 个；关系 {len(data["relations"])} 条；已定位室内开口 {openings} 个。','',
             f'[原图]({data["image"]["file"]}) · [标注 SVG](标注.svg)', '<!-- annotation:summary:end -->','',
             '## 房名与范围核对（2026-11-06）','',
             '沿用原核对号与稳定 S 编号。候选来自历史草稿，未经本轮确认。可修改“预估名称（可改）”，并将“我的确认／备注”改为“已确认”；也可在确认栏直接填实际名称，或在聊天中回复“31号 01=名称”。','',
             '先确认名称、类别和范围，再逐图复核连通。庭院、内庭院、室内庭院及挑空均不计面积；只需区分用途，无须另答有无顶盖。','',
             f'![{number}号完整核对总图]({rel(target / "完整核对总图.png")})','']
    groups = chunks(rows)
    previews = []
    for index, group in enumerate(groups,1):
        start,end = group[0]['number'],group[-1]['number']
        title = start if start==end else start+'—'+end
        x0,y0,x1,y1 = bounds(group)
        crop = (max(0,math.floor(x0)-65),max(0,math.floor(y0)-65),
                min(raw.width,math.ceil(x1)+65),min(raw.height,math.ceil(y1)+65))
        scale = max(2,min(4,1500/max(crop[2]-crop[0],crop[3]-crop[1])))
        size = (round((crop[2]-crop[0])*scale),round((crop[3]-crop[1])*scale))
        rawcrop = raw.crop(crop).resize(size,Image.Resampling.LANCZOS)
        canvas = Image.new('RGB',(size[0],size[1]+65),'white')
        canvas.paste(rawcrop,(0,65))
        draw = ImageDraw.Draw(canvas)
        draw.text((15,12),f'{number}号 核对{title}｜房内数字为固定核对号',font=ImageFont.truetype(FONT,25),fill='#17314a')
        for j,r in enumerate(group):
            color = COLORS[j%len(COLORS)]
            points = [((x-crop[0])*scale,(y-crop[1])*scale+65) for x,y in r['display_polygon']]
            draw.line(points+[points[0]],fill=color,width=4)
            a,b,c,d = r['badge_rect']
            rect = ((a-crop[0])*scale,(b-crop[1])*scale+65,(c-crop[0])*scale,(d-crop[1])*scale+65)
            draw_badge(draw,rect,r['number'],round(r['badge_size']*scale),color)
        png = target / f'局部_{index:02d}_核对{start}-{end}.png'
        unmarked = target / f'局部_{index:02d}_无标记原图.png'
        canvas.save(png)
        rawcrop.save(unmarked)
        previews.append((title,canvas))
        lines += [f'### 核对{title}｜'+ '、'.join(r['id'] for r in group),'',
                  f'![核对{title}局部图]({rel(png)})','',f'[同范围无标记原图]({rel(unmarked)})','',
                  '| 核对号 | S编号 | 预估名称（可改） | 备选名称 | 依据与把握 | 我的确认／备注 | 核对号（重复） |',
                  '| --- | --- | --- | --- | --- | --- | --- |']
        for r in group:
            evidence = r['evidence']
            if len(r['candidates'])>1:
                evidence = '各候选共用依据：'+evidence+'；现有证据不能可靠区分。'
            evidence += ' 把握：'+r['confidence']+'（旧稿预估）。'
            lines.append('| '+' | '.join(map(field,[r['number'],r['id'],r['candidates'][0],
                          '；'.join(r['candidates'][1:]) or '—',evidence,'待确认',r['number']]))+' |')
        lines.append('')
    md.write_text('\n'.join(lines)+'\n')
    state = dict(name_items=[dict(review_id=r['number'],space_id=r['id'],status='pending') for r in rows],
                 connectivity_items=[],checks=dict(connectivity_reviewed=False,visual_reviewed=False))
    (target / 'review_state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
    for batch in range(0,len(previews),6):
        selected = previews[batch:batch+6]
        sheet = Image.new('RGB',(1800,math.ceil(len(selected)/2)*700),'white')
        draw = ImageDraw.Draw(sheet)
        for i,(title,img) in enumerate(selected):
            thumb = img.copy()
            thumb.thumbnail((880,640))
            x,y = (i%2)*900,(i//2)*700
            draw.text((x+12,y+4),f'{number}号 核对{title}',font=ImageFont.truetype(FONT,27),fill='black')
            sheet.paste(thumb,(x,y+45))
        sheet.save(target / f'目检页_{batch//6+1:02d}.jpg',quality=94)
    manifest.append(dict(project=project.name,spaces=len(data['spaces']),pending=len(rows),local_groups=len(groups)))
    print(number,len(rows),'questions',len(groups),'crops',flush=True)
(BASE / '材料清单.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
