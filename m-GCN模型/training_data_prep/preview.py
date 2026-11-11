"""Show explicit outer boundary, exclusions and uncertain areas over source."""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps
from shapely.geometry import shape

from geometry import polygons
from build import OUT, AUDIT

FONT = '/System/Library/Fonts/STHeiti Light.ttc'


def font(size):
    return ImageFont.truetype(FONT, size)


def draw_boundary(record):
    image = Image.open(record['source_image']).convert('RGBA')
    scale = min(1, 1800/max(image.size))
    image = image.resize((round(image.width*scale), round(image.height*scale)))
    overlay = Image.new('RGBA', image.size)
    draw = ImageDraw.Draw(overlay)
    data = json.loads(Path(record['source_annotation']).read_text())
    uncertain = set(record['uncertain_space_ids'])
    for region in record.get('unallocated_inner_regions', []):
        draw.polygon([(x*scale,y*scale) for x,y in region['polygon_px']], fill=(250,180,0,65))
    for s in data['spaces']:
        if s['id'] in record.get('space_overrides', {}):
            pts = [(x*scale,y*scale) for x,y in s['polygon_px']]
            draw.polygon(pts, fill=(10,190,80,75), outline=(0,125,50,255), width=2)
            draw.text(pts[0],s['id']+' 大厅',font=font(14),fill=(0,100,30,255))
        if s['id'] in uncertain:
            draw.polygon([(x*scale,y*scale) for x,y in s['polygon_px']], fill=(250,150,20,100))
    for p in polygons(shape(record['geometry'])):
        draw.line([(x*scale,y*scale) for x,y in p.exterior.coords], fill=(220,0,140,255), width=4)
        for hole in p.interiors:
            pts = [(x*scale,y*scale) for x,y in hole.coords]
            draw.polygon(pts, fill=(0,170,240,65))
            draw.line(pts, fill=(0,125,210,255), width=3)
    image = Image.alpha_composite(image, overlay).convert('RGB')
    canvas = Image.new('RGB', (image.width, image.height+80), 'white')
    canvas.paste(image, (0,80))
    draw = ImageDraw.Draw(canvas)
    draw.text((10,5), record['plan'], fill='black',font=font(23))
    draw.text((10,38), f"紫=概念外壳 蓝=明确排除 橙=范围不确定 | 部件{record['components']} 孔洞{record['holes']}", fill='#333333',font=font(19))
    canvas.save(OUT / '边界预览' / (record['plan'] + '.png'))
    return canvas


def make_crops():
    flags = json.loads((AUDIT/'组合名称复核_28项.json').read_text())
    cards = []
    for flag in flags:
        record = json.loads((OUT/'边界记录'/(flag['plan']+'.json')).read_text())
        data = json.loads(Path(record['source_annotation']).read_text())
        s = next(s for s in data['spaces'] if s['id']==flag['id'])
        pts = s['polygon_px']
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        pad = max(max(xs)-min(xs),max(ys)-min(ys))*.3+25
        box = [max(0,min(xs)-pad),max(0,min(ys)-pad),min(data['image']['width'],max(xs)+pad),min(data['image']['height'],max(ys)+pad)]
        source = Image.open(record['source_image']).convert('RGB')
        crop = source.crop(tuple(round(x) for x in box))
        k = min(530/crop.width,410/crop.height)
        crop = crop.resize((round(crop.width*k),round(crop.height*k)))
        d = ImageDraw.Draw(crop)
        q = [((x-box[0])*k,(y-box[1])*k) for x,y in pts]
        d.line(q+[q[0]],fill='#006aff',width=3)
        card = Image.new('RGB',(550,490),'white')
        card.paste(crop,((550-crop.width)//2,75))
        d = ImageDraw.Draw(card)
        d.text((8,5),flag['plan'][:2]+' '+flag['id'],font=font(23),fill='black')
        d.text((8,36),flag['name'],font=font(21),fill='black')
        card.save(OUT/'边界预览'/f"组合_{flag['plan'][:2]}_{flag['id']}.png")
        cards.append(card)
    for start in range(0,len(cards),6):
        sheet = Image.new('RGB',(1650,980),'#dddddd')
        for i,card in enumerate(cards[start:start+6]):sheet.paste(card,((i%3)*550,(i//3)*490))
        sheet.save(OUT/'边界预览'/f'组合复核_{start//6+1}.png')


def main():
    records = [json.loads(p.read_text()) for p in sorted((OUT/'边界记录').glob('*.json'))]
    for start in range(0,len(records),6):
        sheet = Image.new('RGB',(2100,1320),'#e5e7eb')
        batch=records[start:start+6]
        for i,r in enumerate(batch):
            card=ImageOps.contain(draw_boundary(r),(690,640))
            sheet.paste(card,((i%3)*700+(700-card.width)//2,(i//3)*660+10))
        sheet.save(OUT/'边界预览'/f"边界总览_{batch[0]['plan'][:2]}-{batch[-1]['plan'][:2]}.png")
    make_crops()
    print('boundary previews:',len(records))


if __name__=='__main__':main()
