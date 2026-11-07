"""Replace leader review images with exact, in-room review numbers."""
from datetime import datetime
from hashlib import sha256
from pathlib import Path
import json
import math
import os
import re
import shutil

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon, box


OUT = Path(__file__).resolve().parent
BASE = OUT.parents[1]
PROJECT = BASE / '标注试样/16_浙江大学医学院邵逸夫医院下沙院区'
PHOTOS = BASE / '临时核对/16_邵逸夫下沙_照片补名_20261103'
OLD = BASE / '临时核对/16-20_名称核对_20261103' / PROJECT.name
FONT = '/System/Library/Fonts/STHeiti Medium.ttc'
DATA = json.loads((PROJECT / 'annotation.json').read_text())
SPACES = {s['id']: s for s in DATA['spaces']}
MAPPING = json.loads((OLD / '本轮核对映射.json').read_text())
SOURCE = cv2.imread(str(PROJECT / DATA['image']['file']))
TRANSFORMS = json.loads((PHOTOS / '原图到照片配准.json').read_text())
PHOTO_ARRAYS = {i: cv2.imread(str(PHOTOS / f'照片转正_{i:02d}.jpg'))
                for i in range(1, 7)}


def checksum(path):
    return sha256(path.read_bytes()).hexdigest()


def relative(path):
    return os.path.relpath(path, PROJECT)


def get_background(crop, scale, use_photo=True):
    x1, y1, x2, y2 = crop
    width, height = round((x2-x1)*scale), round((y2-y1)*scale)
    placement = np.array([[scale, 0, -x1*scale],
                          [0, scale, -y1*scale], [0, 0, 1]])
    center = (x1+x2)/2
    preferred = 6 if center < 1000 else 2 if center > 1850 else 4
    options = []
    corners = np.float32([[x1,y1], [x2,y1], [x2,y2], [x1,y2]]).reshape(1,-1,2)
    if use_photo:
        for entry in TRANSFORMS:
            h = np.array(entry['matrix'])
            number = entry['photo']
            photo = PHOTO_ARRAYS[number]
            points = cv2.perspectiveTransform(corners, h)[0]
            inside = np.all((points[:,0] >= 8) & (points[:,0] < photo.shape[1]-8)
                            & (points[:,1] >= 8) & (points[:,1] < photo.shape[0]-8))
            if inside:
                resolution = abs(cv2.contourArea(points))/((x2-x1)*(y2-y1))
                options.append((number == preferred, resolution, number, h))
    if options:
        _, _, number, h = max(options, key=lambda a: (a[0], a[1]))
        pixels = cv2.warpPerspective(PHOTO_ARRAYS[number], placement@np.linalg.inv(h),
                                     (width, height), flags=cv2.INTER_CUBIC,
                                     borderValue=(255,255,255))
    else:
        number = None
        pixels = cv2.warpPerspective(SOURCE, placement, (width, height),
                                     flags=cv2.INTER_CUBIC, borderValue=(255,255,255))
    return Image.fromarray(cv2.cvtColor(pixels, cv2.COLOR_BGR2RGB)), number


def number_box(poly, number, crop, scale, pixels, font_size):
    # Keep badges inside the polygon and away from the room's central name.
    x1, y1, x2, y2 = poly.bounds
    draw = ImageDraw.Draw(pixels)
    gray = np.asarray(pixels.convert('L'))
    for size in range(font_size, 10, -1):
        f = ImageFont.truetype(FONT, size)
        bb = draw.textbbox((0,0), number, font=f)
        width = bb[2]-bb[0]+12
        height = size+10
        w, h = width/scale, height/scale
        margin = min(4, (x2-x1)*.05, (y2-y1)*.05)
        candidates = [(x1+margin, y1+margin), (x2-margin-w, y1+margin),
                      (x1+margin, y2-margin-h), (x2-margin-w, y2-margin-h)]
        candidates += [(x, y) for y in np.linspace(y1+margin, y2-margin-h, 7)
                       for x in np.linspace(x1+margin, x2-margin-w, 7)]
        valid = []
        for priority, (x,y) in enumerate(candidates):
            rect = box(x,y,x+w,y+h)
            if x+w > x2 or y+h > y2 or not poly.covers(rect):
                continue
            px, py = (x-crop[0])*scale, (y-crop[1])*scale
            region = gray[round(py):round(py+height), round(px):round(px+width)]
            if not region.size:
                continue
            ink = np.mean(region < 95)
            # Prefer a corner even when the paper has a visible texture.
            score = ink + (0 if priority < 4 else .18) + priority*.0005
            valid.append((score, x, y, width, height, f, bb))
        if valid:
            _, x, y, width, height, f, bb = min(valid, key=lambda v: v[0])
            return x, y, width, height, f, bb
    raise RuntimeError('No in-room badge fits: '+number)


def render(rows, title, filename, overview=False):
    polygons = {r['id']: Polygon(SPACES[r['id']]['polygon_px']) for r in rows}
    if overview:
        crop = (0, 0, DATA['image']['width'], DATA['image']['height'])
        scale, header, fontsize = 2.0, 100, 28
    else:
        bounds = [p.bounds for p in polygons.values()]
        crop = (max(0, math.floor(min(b[0] for b in bounds))-28),
                max(0, math.floor(min(b[1] for b in bounds))-30),
                min(SOURCE.shape[1], math.ceil(max(b[2] for b in bounds))+30),
                min(SOURCE.shape[0], math.ceil(max(b[3] for b in bounds))+30))
        scale = min(4.0, 2400/(crop[2]-crop[0]))
        header, fontsize = 90, 38
    image, photo = get_background(crop, scale, use_photo=not overview)
    canvas = Image.new('RGB', (image.width, image.height+header), 'white')
    canvas.paste(image, (0,header))
    draw = ImageDraw.Draw(canvas)
    size = min(30, max(17, image.width//45))
    draw.text((18,12), title, font=ImageFont.truetype(FONT,size), fill='#17324d')
    caption = '房内数字＝固定核对号，对应下方表格；请直接按数字填写。'
    draw.text((18, size+24), caption, font=ImageFont.truetype(FONT,max(13,size-7)), fill='#475569')
    audit = []
    for row in rows:
        poly = polygons[row['id']]
        # A thin outline supports exact localization without covering the name.
        points = [((x-crop[0])*scale, header+(y-crop[1])*scale)
                  for x,y in poly.exterior.coords]
        draw.line(points, fill='#2563eb', width=2)
        x, y, w, h, f, bb = number_box(poly, row['number'], crop, scale, image, fontsize)
        px, py = (x-crop[0])*scale, header+(y-crop[1])*scale
        draw.rounded_rectangle((px,py,px+w,py+h),radius=5,fill='white',
                               outline='#1748ad',width=3)
        draw.text((px+6-bb[0],py+(h-(bb[3]-bb[1]))/2-bb[1]),row['number'],
                  font=f,fill='#153f98')
        assert poly.covers(box(x,y,x+w/scale,y+h/scale))
        audit.append(dict(number=row['number'],id=row['id'],
                          badge_box_px=[x,y,x+w/scale,y+h/scale], photo=photo))
    canvas.save(filename, quality=96, subsampling=0)
    if overview:
        canvas.thumbnail((1850,1600))
        canvas.save(OUT/'房内编号总图_预览.jpg',quality=94)
    return audit


def chunks(rows):
    # Split far-apart groups so numbers and source names remain readable.
    result, current = [], []
    for row in rows:
        proposed = current+[row]
        bounds = [Polygon(SPACES[r['id']]['polygon_px']).bounds for r in proposed]
        spread = max(b[2] for b in bounds)-min(b[0] for b in bounds)
        if current and spread > 1150:
            result.append(current)
            current = []
        current.append(row)
    if current:
        result.append(current)
    return result


def main():
    md = PROJECT/'标注说明.md'
    original = md.read_text()
    baseline = {p.name:checksum(p) for p in PROJECT.iterdir() if p.is_file()}
    stamp = datetime.now().strftime('%H%M%S')
    backup = OUT/f'修改前备份_{stamp}'
    backup.mkdir()
    shutil.copy2(md,backup/md.name)
    row_lines = [l for l in original.splitlines() if re.match(r'^\|\s*\d+\s*\|',l)]
    assert len(row_lines) == 141
    matches = list(re.finditer(r'!\[([^\]]*)\]\([^)]*/局部_(\d+)-(\d+)\.jpg\)',original))
    assert len(matches) == 27
    replacements, audit = {}, []
    for match in matches:
        a,b = int(match[2]),int(match[3])
        rows = [r for r in MAPPING if a <= int(r['number']) <= b]
        images = []
        for i, subset in enumerate(chunks(rows),1):
            suffix = f'_{i}' if len(chunks(rows)) > 1 else ''
            filename = OUT/f'房内编号_{a:02d}-{b:02d}{suffix}.jpg'
            title = f"{subset[0]['number']}—{subset[-1]['number']}｜{subset[0]['group']}"
            audit += render(subset,title,filename)
            images.append(f'![{title}，数字直接标在房间内]({relative(filename)})')
        replacements[match[0]] = '\n\n'.join(images)
    overview = OUT/'房内编号总图.jpg'
    total_audit = render(MAPPING,'16号｜房内编号定位总图（01—141）',overview,overview=True)
    updated = original
    for old,new in replacements.items():
        updated = updated.replace(old,new)
    updated = re.sub(r'!\[本组剩余待确认项的补充照片\]\([^)]*\)\s*\n','',updated)
    updated = re.sub(r'!\[初始141项固定编号定位总图\]\([^)]*\)',
                     f'![141项固定编号直接标在房间内]({relative(overview)})',updated)
    updated = re.sub(r'\[打开高清核对总图\]\([^)]*\)',
                     f'[打开高清房内编号总图]({relative(overview)})',updated)
    updated = updated.replace('每组表旁新增剩余项的照片对照。',
                              '每组表旁已改为房内编号图：数字直接位于对应房间内。')
    updated = updated.replace('旧总图和旧局部图的边栏保留初始候选，仅供固定编号定位；当前名称与状态以本表和新增照片为准。',
                              '核对图已改为房内数字标记：图中01、02等数字就是本表左列核对号；名称与确认状态以本表为准。')
    updated = updated.replace('照片局部按原图位置配准，仅用于辨认文字。',
                              '核对局部优先使用补充照片，并按原图位置配准，在对应房间内标出固定核对号。')
    assert [l for l in updated.splitlines() if re.match(r'^\|\s*\d+\s*\|',l)] == row_lines
    for path in re.findall(r'!\[[^\]]*\]\(([^)]+)\)',updated):
        assert (PROJECT/path).resolve().is_file(),path
    assert len(audit) == 141 and len({r['number'] for r in audit}) == 141
    assert [r['number'] for r in audit] == [r['number'] for r in MAPPING]
    assert len(total_audit) == 141
    for name,h in baseline.items():
        assert checksum(PROJECT/name) == h, '文件处理期间已改变：'+name
    md.write_text(updated)
    for name,h in baseline.items():
        if name != md.name:
            assert checksum(PROJECT/name) == h
    (OUT/'房内编号校验.json').write_text(json.dumps(dict(
        local_badges=audit,overview_badges=total_audit,table_rows_preserved=141,
        leader_lines=0,source_json_svg_unchanged=True),ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(local_images=len(replacements),badges=len(audit),
                         table_rows_preserved=len(row_lines),leader_lines=0,
                         source_json_svg_unchanged=True),ensure_ascii=False))


if __name__ == '__main__':
    main()
