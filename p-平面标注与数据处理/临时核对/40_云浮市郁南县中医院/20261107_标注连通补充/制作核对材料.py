from pathlib import Path
import json
import os
import re
from collections import Counter
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon, box, LineString, Point
import pymupdf

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
SAMPLE = ROOT / '标注试样/40_云浮市郁南县中医院'
STATE = OUT.parent / 'review_state.json'
data = json.loads((SAMPLE / 'annotation.json').read_text())
state = json.loads(STATE.read_text())
source = Image.open(SAMPLE / data['image']['file']).convert('RGB')
spaces = {s['id']: s for s in data['spaces']}
polys = {sid: Polygon(s['polygon_px']) for sid, s in spaces.items()}
FONT = '/System/Library/Fonts/STHeiti Medium.ttc'
NUMFONT = '/System/Library/Fonts/Supplemental/Arial.ttf'
COLORS = ['#b45309', '#2563eb', '#2563eb', '#2563eb', '#2563eb', '#7c3aed',
          '#7c3aed', '#0f766e', '#b45309', '#7c3aed', '#7c3aed', '#b45309']
names = [
    ('01', 'S003', '备餐间', '厨房配套用房', '邻接主厨房，原图无房名；两候选均仅据餐饮后勤位置推测。低'),
    ('02', 'S018', '电梯前室', '发热门诊配套用房', '北侧电梯、东侧楼梯及中间白色前区可辨；前室判断较强，具体原名未标。中'),
    ('03', 'S019', '影像检查及配套区', 'CT检查及配套区', '可见大型影像设备及配套小间；支持影像用途，不能据图确认具体设备类型。中'),
    ('04', 'S020', '内庭院', '景观中庭', '方框内有景观状符号，与10号相似；两候选共用此依据，仍需区分庭院与室内设施。中'),
    ('05', 'S021', '医护配套用房', '更衣／卫生配套区', '西侧医护厅旁有多间小房及卫生设施；无法确认整组具体名称。低'),
    ('06', 'S025', '洗衣房配套用房', '库房', '位于西交通核与洗衣房之间，无房名和明确家具；两候选仅据片区推测。低'),
    ('07', 'S033', '高压氧舱配套用房', '候诊／准备区', '可见通往住院大厅、高压氧舱的门；可达性较明确，用途缺乏文字。低'),
    ('08', 'S042', '设备／库区配套用房', '管理用房', '在库区与设备电梯厅旁，可见小房分隔；无足够用途证据。低'),
    ('09', 'S053', '药房配套用房', '药库', '位于药房西北侧，两间小房南侧开门；两候选均仅据药房背景，未见房名。低'),
    ('10', 'S057', '内庭院', '景观中庭', '与04号有相似方框景观符号；需确认用途，庭院一经确定即排除面积。中'),
    ('11', 'S068', '内院', '备用用房', '急救中央大块空白空间，未见名称或明确家具；不能仅凭空白判作庭院。低'),
    ('12', 'S069', '通道', '庭院／采光带', '候药厅南侧狭长白色带，两端构造仍模糊；两候选不能由长条形状区分，另见K03。低'),
]
for item, row in zip(state['name_items'], names):
    assert (item['review_id'], item['space_id']) == row[:2]
    item.update(candidate_name=row[2], alternative_name=row[3], evidence=row[4])
STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n')

def font(size, numeric=False):
    return ImageFont.truetype(NUMFONT if numeric else FONT, size)

def badge(draw, center, text, color, scale=1, origin=(0, 0), size=22):
    f = font(round(size * scale), True)
    cx, cy = ((center[i] - origin[i]) * scale for i in (0, 1))
    bounds = draw.textbbox((0, 0), text, font=f)
    w, h = bounds[2] + 12 * scale, size * scale + 8 * scale
    rect = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
    draw.rounded_rectangle(rect, radius=4 * scale, fill='white', outline=color, width=max(1, round(2 * scale)))
    draw.text((cx - bounds[2] / 2, cy - size * scale / 2 - bounds[1]), text, font=f, fill=color)
    return rect

centers = [(510, 220), (1882, 278), (1680, 410), (1897, 350),
           (1450, 420), (1256, 960), (1255, 1195), (385, 1460),
           (390, 2220), (1633, 2248), (1400, 2450), (545, 2514)]
# Label order remains the original fixed 01--12. Route around the reversed
# vertical order of 03 and 04 rather than renumbering either space.
routes = [
    [(510, 220), (90, 220), (-25, 220)],
    [(1882, 278), (2070, 278), (2150, 230), (2220, 230)],
    [(1680, 410), (1785, 315), (2070, 315), (2150, 340), (2220, 340)],
    [(1897, 350), (2040, 400), (2150, 450), (2220, 450)],
    [(1450, 420), (1510, 580), (2080, 580), (2150, 560), (2220, 560)],
    [(1256, 960), (2140, 960), (2220, 960)],
    [(1255, 1195), (2140, 1195), (2220, 1195)],
    [(385, 1460), (90, 1460), (-25, 1460)],
    [(390, 2220), (90, 2220), (-25, 2220)],
    [(1633, 2248), (2140, 2248), (2220, 2248)],
    [(1400, 2450), (2140, 2450), (2220, 2450)],
    [(545, 2514), (90, 2514), (-25, 2514)],
]
crossings = []
for i, route in enumerate(routes):
    for j in range(i):
        if LineString(route).intersects(LineString(routes[j])):
            crossings.append([names[j][0], names[i][0]])
assert not crossings, crossings
side, top = 650, 150
overview = Image.new('RGB', (source.width + side * 2, source.height + top + 60), 'white')
overview.paste(source, (side, top))
draw = ImageDraw.Draw(overview)
draw.text((35, 25), '40号｜首层房名核对总图（沿用原01—12号）', font=font(42), fill='#18314c')
draw.text((35, 88), '12项待确认；彩框为功能范围，房内数字与边栏一一对应。门位另见标注.svg。', font=font(25), fill='#475569')
badge_audit = []
for i, (rid, sid, candidate, alternative, evidence) in enumerate(names):
    color = COLORS[i]
    pts = [(x + side, y + top) for x, y in spaces[sid]['polygon_px']]
    draw.line(pts + [pts[0]], fill=color, width=4)
    route = [(x + side, y + top) for x, y in routes[i]]
    draw.line(route, fill=color, width=3)
    rect = badge(draw, (centers[i][0] + side, centers[i][1] + top), rid, color)
    bbox = box(rect[0] - side, rect[1] - top, rect[2] - side, rect[3] - top)
    assert polys[sid].covers(bbox), (rid, sid)
    badge_audit.append({'review_id': rid, 'space_id': sid, 'inside': True})
    right = routes[i][-1][0] > 0
    x = side + 2220 if right else 30
    y = route[-1][1] - 44
    draw.rounded_rectangle((x, y, x + 580, y + 89), radius=10, fill='#f8fafc', outline=color, width=3)
    draw.text((x + 15, y + 10), f'{rid}｜{sid}  名称未确认', font=font(27), fill=color)
    draw.text((x + 15, y + 48), f'预估：{candidate}', font=font(25), fill='#334155')
overview.save(OUT / '40_完整原图_固定编号核对总图.png')

connection_specs = [
    ('K01', (1280, 180, 1715, 470), [('S017', (1335, 290)), ('S015', (1550, 280)), ('S021', (1430, 420))]),
    ('K02', (1620, 1010, 1960, 1335), [('S029', (1680, 1190)), ('S031', (1870, 1250)), ('S030', (1870, 1113))]),
    ('K03', (225, 2420, 840, 2670), [('S060', (300, 2460)), ('S069', (540, 2514)),
                                  ('S067', (795, 2570)), ('S071', (540, 2620))]),
]
for number, bounds, labels in connection_specs:
    scale = 2.4 if number != 'K03' else 2
    crop = source.crop(bounds)
    scaled = crop.resize((round(crop.width * scale), round(crop.height * scale)))
    canvas = Image.new('RGB', (scaled.width, scaled.height + 85), 'white')
    canvas.paste(scaled, (0, 85))
    cd = ImageDraw.Draw(canvas)
    cd.text((20, 17), f'{number}｜房内数字为稳定S编号', font=font(30), fill='#18314c')
    for sid, center in labels:
        clipped = polys[sid].intersection(box(*bounds))
        poly = [(round((x - bounds[0]) * scale), round((y - bounds[1]) * scale + 85))
                for x, y in clipped.exterior.coords]
        cd.line(poly + [poly[0]], fill='#2563eb', width=3)
        # Use source coordinates for the containment check and display offset.
        rect = badge(cd, (center[0], center[1] + 85 / scale), sid[1:], '#2563eb', scale, bounds[:2], 15)
        source_rect = box(rect[0] / scale + bounds[0], (rect[1] - 85) / scale + bounds[1],
                          rect[2] / scale + bounds[0], (rect[3] - 85) / scale + bounds[1])
        assert polys[sid].covers(source_rect), (number, sid, source_rect.bounds)
        badge_audit.append({'review_id': number, 'space_id': sid, 'inside': True})
    canvas.save(OUT / f'{number}_连通核对.png')
    crop.resize(scaled.size).save(OUT / f'{number}_无标记原图.png')

def relative(path):
    return os.path.relpath(path, SAMPLE)

# Baseline MD has no filled answers; preserve the exact text in the four-file
# backup, then replace stale counts and vanished temporary links with live material.
lines = ['# 40号｜云浮市郁南县中医院（首层）', '',
         '<!-- annotation:summary:start -->', '<!-- annotation:summary:end -->', '',
         f'本轮沿用73个功能区级节点，不逐室细分内部小房间。已补{sum(len(r.get("openings", [])) for r in data["relations"])}处可见门洞／开口；无定位的概念连接不画红点。', '',
         '房名固定号沿用01—12；候选尚未确认，JSON继续保留 `unknown`。可改“预估名称（可改）”并填“已确认”，也可直接填实际名称。确认庭院／挑空后直接排除面积，无须另答顶盖问题。', '',
         f'![完整原图与固定核对号]({relative(OUT / "40_完整原图_固定编号核对总图.png")})', '']
for rid, sid, candidate, alternative, evidence in names:
    lines += [f'### {rid}｜{sid}', '',
              f'![{rid}号房名局部图]({relative(OUT / "逐项局部" / (rid + "_" + sid + ".png"))})', '',
              '| 核对号 | S编号 | 预估名称（可改） | 备选名称 | 依据与把握 | 我的确认／备注 | 核对号（重复） |',
              '| --- | --- | --- | --- | --- | --- | --- |',
              f'| {rid} | {sid} | {candidate} | {alternative} | {evidence} | 待确认 | {rid} |', '']
questions = {
    'K01': ('S017医护厅是否经东侧缓冲小间直接进入S015特殊发热门诊？',
            '缓冲区两侧门的连续路线不清，暂不建立跨区access；请确认相通或独立。'),
    'K02': ('除服务窗口外，S031住院药房是否经北侧人员口直接接S029住院大厅？',
            '西侧柜台只记service；北侧人员门不清，暂不补access。如从别处进入，请写所连空间。'),
    'K03': ('12号S069是否为可通行长条空间，东接S067大厅、西接S060医护区？',
            '两端似有接口，但用途仍未定；先不补边。可分别写东／西相通情况；如为庭院请写实际开口。'),
}
for number, (question, judgment) in questions.items():
    lines += [f'### {number}｜关键连通', '',
              f'![{number}连通局部图]({relative(OUT / (number + "_连通核对.png"))})', '',
              f'[查看无标记原图]({relative(OUT / (number + "_无标记原图.png"))})', '',
              f'**问题：**{question}', '', f'**我的判断：**{judgment}', '',
              '**我的确认／备注：**待填写（写“相通”“不相通”或实际连接；仍不清楚可填“待确认”）', '']
(SAMPLE / '标注说明.md').write_text('\n'.join(lines))

# Whole SVG and two dense local previews; these remain outside the formal sample.
svg = pymupdf.open(SAMPLE / '标注.svg')
page = svg[0]
page.get_pixmap(matrix=pymupdf.Matrix(.65, .65), alpha=False).save(OUT / 'SVG_全图.png')
head = 109.6
for name, bounds in [('SVG_门诊急救密集区', (200, 2180, 1810, 2750)),
                      ('SVG_餐饮发热门诊', (180, 150, 2060, 570))]:
    x0, y0, x1, y1 = bounds
    page.get_pixmap(matrix=pymupdf.Matrix(1.1, 1.1),
                    clip=pymupdf.Rect(x0, y0 + head, x1, y1 + head), alpha=False).save(OUT / f'{name}.png')

thumb_w, thumb_h = 600, 400
sheet = Image.new('RGB', (thumb_w * 3, thumb_h * 4), '#cbd5e1')
for i, (rid, sid, *_) in enumerate(names):
    im = Image.open(OUT / '逐项局部' / f'{rid}_{sid}.png')
    im.thumbnail((thumb_w, thumb_h))
    sheet.paste(im, ((i % 3) * thumb_w, (i // 3) * thumb_h))
sheet.save(OUT / '12项局部图_目检汇总.png')
audit = {'leader_crossings': crossings, 'badge_containment': badge_audit,
         'pending_name_count': len(names), 'fixed_mapping_preserved': True,
         'relations_by_type': dict(Counter(r['type'] for r in data['relations']))}
(OUT / '核对材料检查.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(audit, ensure_ascii=False, indent=2))
