"""Create inline room-name review panels while preserving existing table rows."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import math
import re
import shutil

from PIL import Image, ImageDraw, ImageFont, ImageStat
from shapely.geometry import Polygon, box

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'p-平面标注与数据处理'
WORK = Path(__file__).resolve().parent
FONT = '/System/Library/Fonts/STHeiti Medium.ttc'
PALETTE = ['#b45309', '#0369a1', '#7e22ce', '#047857', '#be123c', '#4338ca', '#0e7490', '#9f1239']
NAMES = ['09_深圳大学学府医院', '10_石家庄第一医院新建赵卜口院区']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def font(size):
    return ImageFont.truetype(FONT, size)


def row_cells(line):
    cells = [v.strip() for v in line.strip().strip('|').split('|')]
    if len(cells) == 7 and re.fullmatch(r'\d+', cells[0]) and re.fullmatch(r'S\d+', cells[1]):
        return cells
    return None


def sections(text):
    matches = list(re.finditer(r'^### (.+)$', text, re.M))
    result = []
    for idx, match in enumerate(matches):
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        block = text[match.end():end]
        rows = [line for line in block.splitlines() if row_cells(line)]
        if rows:
            result.append((match.start(), end, match.group(1), rows))
    return result


def polygon_in_reading_orientation(space, number, source_height):
    points = space['polygon_px']
    if number == '09':
        points = [[source_height - y, x] for x, y in points]
    return Polygon(points)


def badge_position(poly, gray, label_width, label_height):
    """Choose a bright interior patch, preferring corners away from original text."""
    x1, y1, x2, y2 = poly.bounds
    candidates = []
    for fy in [.08, .92, .2, .8, .35, .65, .5]:
        for fx in [.08, .92, .2, .8, .35, .65, .5]:
            cx = x1 + label_width / 2 + 5 + fx * max(0, x2 - x1 - label_width - 10)
            cy = y1 + label_height / 2 + 5 + fy * max(0, y2 - y1 - label_height - 10)
            rect = box(cx-label_width/2, cy-label_height/2, cx+label_width/2, cy+label_height/2)
            if not poly.covers(rect):
                continue
            patch = gray.crop(rect.bounds)
            dark = sum(patch.histogram()[:150]) / max(1, patch.width * patch.height)
            edge = min(fx, 1-fx) + min(fy, 1-fy)
            candidates.append((dark + edge * .035, cx, cy))
    if candidates:
        _, cx, cy = min(candidates)
        return cx, cy, True
    point = poly.representative_point()
    return point.x, point.y, False


def panel(source, name, title, rows, spaces, out, serial):
    number = name[:2]
    cells = [row_cells(line) for line in rows]
    polys = [polygon_in_reading_orientation(spaces[c[1]], number, 2444) for c in cells]
    bounds = [p.bounds for p in polys]
    x1, y1 = min(v[0] for v in bounds), min(v[1] for v in bounds)
    x2, y2 = max(v[2] for v in bounds), max(v[3] for v in bounds)
    pad_x, pad_y = max(65, (x2-x1)*.08), max(65, (y2-y1)*.13)
    crop = (max(0, math.floor(x1-pad_x)), max(0, math.floor(y1-pad_y)),
            min(source.width, math.ceil(x2+pad_x)), min(source.height, math.ceil(y2+pad_y)))
    raw = source.crop(crop)
    zoom = min(3.2, 1700 / raw.width)
    width = max(1200, round(raw.width * zoom) + 64)
    head = 140
    legend_rows = math.ceil(len(cells) / 4)
    height = head + round(raw.height * zoom) + legend_rows * 52 + 84
    im = Image.new('RGB', (width, height), '#f8fafc')
    draw = ImageDraw.Draw(im)
    tag = cells[0][0] if len(cells) == 1 else cells[0][0] + '—' + cells[-1][0]
    heading = re.sub(r'（.*?）', '', title)
    heading = re.sub(r'^\d+(?:—\d+)?｜', '', heading)
    draw.text((32, 18), f'{number}号｜{heading}｜核对 {tag}', font=font(37), fill='#0f172a')
    draw.text((32, 76), '彩框标出待确认空间；框内数字＝表格核对号；候选与填写栏在图下。', font=font(27), fill='#475569')
    offset = ((width-round(raw.width*zoom))//2, head)
    raw_scaled = raw.resize((round(raw.width*zoom), round(raw.height*zoom)), Image.Resampling.LANCZOS)
    im.paste(raw_scaled, offset)
    gray = source.convert('L')
    records = []
    for idx, (cell, poly) in enumerate(zip(cells, polys)):
        color = PALETTE[idx % len(PALETTE)]
        points = [(offset[0]+(x-crop[0])*zoom, offset[1]+(y-crop[1])*zoom) for x,y in poly.exterior.coords]
        draw.line(points, fill=color, width=4, joint='curve')
        label_font = font(33)
        bw = draw.textlength(cell[0], font=label_font) + 16
        bh = 44
        cx, cy, fits = badge_position(poly, gray, bw/zoom, bh/zoom)
        if not fits:
            # Narrow room: reduce the badge to fit before using its interior point.
            for size in [29, 25, 21, 18]:
                label_font = font(size)
                bw = draw.textlength(cell[0], font=label_font) + 10
                bh = size + 10
                cx, cy, fits = badge_position(poly, gray, bw/zoom, bh/zoom)
                if fits:
                    break
        px = offset[0] + (cx-crop[0])*zoom
        py = offset[1] + (cy-crop[1])*zoom
        draw.rounded_rectangle((px-bw/2, py-bh/2, px+bw/2, py+bh/2), radius=5, fill='white', outline=color, width=2)
        draw.text((px, py), cell[0], anchor='mm', font=label_font, fill=color, stroke_width=0)
        lx = 32 + (idx % 4) * ((width-64)//4)
        ly = head + raw_scaled.height + 16 + (idx//4)*52
        draw.text((lx, ly), f'{cell[0]}｜{cell[1]}', font=font(30), fill=color)
        records.append({'number': cell[0], 'sid': cell[1], 'badge_inside': fits, 'badge_xy': [cx, cy]})
    filename = f'{serial:02d}_核对{cells[0][0]}-{cells[-1][0]}_局部.png'
    im.save(out/filename, optimize=True)
    clean_name = filename.replace('_局部.png', '_无标记原图.png')
    raw.save(out/clean_name, optimize=True)
    rel = '../../临时核对/' + WORK.name + '/' + name + '/' + filename
    clean_rel = rel.replace('_局部.png', '_无标记原图.png')
    lines = [f'#### 核对 {tag}', '', f'![{number}号 {heading}，待确认空间 {tag}]({rel})', '',
             f'[打开局部图原尺寸]({rel}) · [查看同范围无标记原图]({clean_rel})', '',
             '**需确认：**请确认下表各空间名称；可修改预估名称并填“已确认”，或在确认栏直接写实际名称。', '',
             '| 核对号 | S编号 | 预估名称（可改） | 备选名称 | 依据与把握 | 我的确认／备注 | 核对号（重复） |',
             '| --- | --- | --- | --- | --- | --- | --- |', *rows, '']
    return '\n'.join(lines), {'file': filename, 'crop': crop, 'size': im.size, 'items': records}


def process(name):
    project = BASE / '标注试样' / name
    out = WORK / name
    backup = out / '修改前备份'
    backup.mkdir(parents=True, exist_ok=True)
    md_path = project / '标注说明.md'
    backup_md = backup / md_path.name
    if backup_md.exists():
        raise RuntimeError('Backup exists; inspect before rerunning.')
    shutil.copy2(md_path, backup_md)
    text = md_path.read_text()
    data = json.loads((project/'annotation.json').read_text())
    hashes = {p.name: digest(p) for p in project.iterdir() if p.is_file()}
    (out/'修改前文件校验.json').write_text(json.dumps(hashes, ensure_ascii=False, indent=2)+'\n')
    source = Image.open(project/data['image']['file']).convert('RGB')
    if name.startswith('09'):
        source = source.transpose(Image.Transpose.ROTATE_270)
    spaces = {s['id']: s for s in data['spaces']}
    blocks = sections(text)
    old_rows = [row_cells(line) for line in text.splitlines() if row_cells(line)]
    assert {r[1] for r in old_rows} == {s['id'] for s in data['spaces'] if s['type']=='unknown'}
    replacements = []
    panels = []
    serial = 0
    for start, end, heading, rows in blocks:
        result = [f'### {heading}', '']
        for i in range(0, len(rows), 8):
            serial += 1
            new_block, metadata = panel(source, name, heading, rows[i:i+8], spaces, out, serial)
            result.append(new_block)
            panels.append(metadata)
        replacements.append((start, end, '\n'.join(result)+'\n'))
    for start, end, replacement in reversed(replacements):
        text = text[:start] + replacement + text[end:]
    note = ('**本轮核对：先确认房间名称，全部名称确认后再核对连通性。**局部图中的彩框和数字仅定位待确认空间；'
            '每组最多8项，图下紧接对应填写表。候选、依据、原核对号及S编号均沿用已有材料。\n\n')
    if name.startswith('09'):
        note += '**读图方向：**局部图按文字阅读方向顺时针旋转90°；原图文件与JSON坐标保持原样。\n\n'
    first_section = text.index('## ')
    text = text[:first_section] + note + text[first_section:]
    new_rows = [row_cells(line) for line in text.splitlines() if row_cells(line)]
    assert old_rows == new_rows, 'Existing rows or answers changed.'
    md_path.write_text(text)
    assert all(digest(project/f)==h for f,h in hashes.items() if f!='标注说明.md')
    metadata = {'project': name, 'panel_count': len(panels), 'row_count': len(old_rows), 'panels': panels,
                'table_rows_preserved': old_rows == new_rows, 'other_files_unchanged': True}
    (out/'局部图映射与检查.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2)+'\n')
    thumbs = []
    for p in panels:
        image = Image.open(out/p['file']).convert('RGB')
        image.thumbnail((550, 600))
        thumbs.append(image.copy())
    columns = 4
    sheet = Image.new('RGB', (columns*570, math.ceil(len(thumbs)/columns)*650), '#e2e8f0')
    for idx, thumb in enumerate(thumbs):
        sheet.paste(thumb, ((idx%columns)*570+10, (idx//columns)*650+10))
    sheet.save(out/'全部局部图_目检总览.jpg', quality=92)
    return metadata


if __name__ == '__main__':
    for name in NAMES:
        result = process(name)
        print(json.dumps({k:v for k,v in result.items() if k!='panels'}, ensure_ascii=False))
