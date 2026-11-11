"""Create overview and endpoint audit images; never alter source images."""
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps
from shapely.geometry import shape

ROOT = Path(__file__).resolve().parent
FONT = '/System/Library/Fonts/STHeiti Light.ttc'


def font(size):
    return ImageFont.truetype(FONT, size)


def polygons(geom):
    if geom.geom_type == 'Polygon':
        return [geom]
    return [p for g in getattr(geom, 'geoms', []) for p in polygons(g)]


def preview(record):
    source = Image.open(record['source']).convert('RGB')
    scale = min(1, 1600 / max(source.size))
    image = source.resize((round(source.width * scale), round(source.height * scale)))
    layer = Image.new('RGBA', image.size)
    draw = ImageDraw.Draw(layer)
    data = json.loads(Path(record['annotation']).read_text())
    nodes = {n['id']: n for n in record['nodes']}
    for s in data['spaces']:
        f = nodes[s['id']]
        if not f['function_label_available']:
            draw.polygon([(x * scale, y * scale) for x, y in s['polygon_px']], fill=(250, 150, 20, 65))
        if f['excluded_from_indoor_area']:
            pts = [(x * scale, y * scale) for x, y in s['polygon_px']]
            draw.polygon(pts, fill=(0, 200, 220, 45), outline=(0, 140, 180, 255), width=2)
    features = json.loads((ROOT / '候选轮廓' / (record['plan'] + '.geojson')).read_text())
    for p in polygons(shape(features['features'][1]['geometry'])):
        draw.line([(x * scale, y * scale) for x, y in p.exterior.coords], fill=(220, 0, 150, 245), width=3)
    image = Image.alpha_composite(image.convert('RGBA'), layer).convert('RGB')
    canvas = Image.new('RGB', (image.width, image.height + 70), 'white')
    canvas.paste(image, (0, 70))
    draw = ImageDraw.Draw(canvas)
    draw.text((12, 6), record['plan'], fill='black', font=font(22))
    draw.text((12, 37), '紫：未核验占用包络候选  橙：缺功能标签  青：明确面积排除项', fill='#333333', font=font(18))
    canvas.save(ROOT / '检查预览' / (record['plan'] + '.png'))
    return canvas


def contact_sheets(records):
    for start in range(0, len(records), 6):
        selected = records[start:start + 6]
        sheet = Image.new('RGB', (2100, 1320), '#e5e7eb')
        for i, record in enumerate(selected):
            card = preview(record)
            thumb = ImageOps.contain(card, (690, 640))
            x, y = (i % 3) * 700 + (700 - thumb.width) // 2, (i // 3) * 660 + 10
            sheet.paste(thumb, (x, y))
        name = f"总览_{records[start]['plan'][:2]}-{selected[-1]['plan'][:2]}.png"
        sheet.save(ROOT / '检查预览' / name)


def endpoint_crops(records):
    rows = []
    cards = []
    for record in records:
        length = record['candidate_envelope']['normalization_proposal']['length_px']
        data = json.loads(Path(record['annotation']).read_text())
        byid = {s['id']: s for s in data['spaces']}
        for flag in record['opening_endpoint_flags']:
            distance = max(flag['distance_to_polygons_px'])
            if distance / length <= .01:
                continue
            source = Image.open(record['source']).convert('RGB')
            x, y = flag['position_px']
            radius = max(length * .06, distance * 3)
            bbox = (max(0, x - radius), max(0, y - radius), min(source.width, x + radius), min(source.height, y + radius))
            crop = source.crop(tuple(round(v) for v in bbox))
            scale = min(580 / crop.width, 430 / crop.height)
            crop = crop.resize((round(crop.width * scale), round(crop.height * scale)))
            draw = ImageDraw.Draw(crop)
            for sid, color in zip([flag['source'], flag['target']], ['#006aff', '#06a120']):
                pts = [((a - bbox[0]) * scale, (b - bbox[1]) * scale) for a, b in byid[sid]['polygon_px']]
                draw.line(pts + [pts[0]], fill=color, width=3)
                sx = sum(a for a, b in pts) / len(pts)
                sy = sum(b for a, b in pts) / len(pts)
                draw.text((max(0, sx), max(0, sy)), sid, fill=color, font=font(22))
            px, py = (x - bbox[0]) * scale, (y - bbox[1]) * scale
            draw.ellipse((px - 6, py - 6, px + 6, py + 6), fill='red', outline='white', width=1)
            card = Image.new('RGB', (600, 510), 'white')
            card.paste(crop, ((600 - crop.width) // 2, 75))
            draw = ImageDraw.Draw(card)
            title = f"{record['plan'][:2]} {flag['opening']} {flag['source']}—{flag['target']}"
            draw.text((10, 7), title, fill='black', font=font(23))
            draw.text((10, 40), f'距两端最大 {distance:.1f}px；长边 {distance / length:.2%}', fill='#333333', font=font(20))
            filename = f"门洞_{record['plan'][:2]}_{flag['opening']}.png"
            card.save(ROOT / '检查预览' / filename)
            rows.append({'plan': record['plan'], **flag, 'relative_distance': distance / length, 'preview': filename,
                         'status': 'distance_priority_not_semantic_error'})
            cards.append(card)
    for start in range(0, len(cards), 6):
        sheet = Image.new('RGB', (1800, 1020), '#e5e7eb')
        for i, card in enumerate(cards[start:start + 6]):
            sheet.paste(card, ((i % 3) * 600, (i // 3) * 510))
        sheet.save(ROOT / '检查预览' / f'门洞距离优先复核_{start // 6 + 1}.png')
    (ROOT / '门洞距离优先复核.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n')


def main():
    records = [json.loads(p.read_text()) for p in sorted((ROOT / '逐图审计').glob('*.json'))]
    contact_sheets(records)
    endpoint_crops(records)
    print('overview plans:', len(records), 'sheets:', math.ceil(len(records) / 6))


if __name__ == '__main__':
    main()
