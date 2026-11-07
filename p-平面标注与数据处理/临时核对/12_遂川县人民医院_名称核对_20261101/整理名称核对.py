from pathlib import Path
from collections import Counter
from PIL import Image, ImageDraw, ImageFont
import hashlib
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[3]
PROJECT = ROOT / 'p-平面标注与数据处理/标注试样/12_遂川县人民医院'
OUT = Path(__file__).resolve().parent
MD = PROJECT / '标注说明.md'
DATA = json.loads((PROJECT / 'annotation.json').read_text())
SPACES = {s['id']: s for s in DATA['spaces']}
UNKNOWN = {s['id'] for s in DATA['spaces'] if s['type'] == 'unknown'}
IMAGE = Image.open(PROJECT / DATA['image']['file']).convert('RGB')
FONT = '/System/Library/Fonts/Supplemental/Arial Unicode.ttf'
COLORS = ['#a53c27', '#7b4ab5', '#245fa1', '#21745a', '#926020',
          '#ae3c74', '#4556a8', '#8c4b20', '#1f7378', '#a84431',
          '#6a4aa0', '#245f91']


def ids(*numbers):
    return [f'S{n:03d}' for n in numbers]


GROUPS = [
    ('西北翼部', ids(1, 2, 3, 6, 7, 8, 9, 10, 11, 12, 13, 15, 16, 17, 18, 19)),
    ('北侧大厅附属空间', ids(25, 31)),
    ('东北翼部', ids(33, 34, 35, 36, 37, 40, 43, 44, 45, 48, 49, 50, 51, 52, 53, 54, 55, 57)),
    ('纵向中段北部', ids(60, 61, 62, 63, 64, 65, 68, 69, 70, 71, 72, 73, 74, 75, 76, 79, 80, 81, 82, 83, 84)),
    ('纵向中段南部', ids(86, 88, 90, 93, 95, 96, 97, 98, 99, 100, 101, 102, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 116, 119, 120)),
    ('门诊北排西侧', ids(124, 125, 126, 127, 128, 130, 139, 141, 142)),
    ('门诊北排东侧', ids(132, 133, 134, 135, 136, 137)),
    ('门诊中排西侧', ids(145, 146, 147, 148, 149, 150, 151, 152, 168)),
    ('门诊中排东侧', ids(153, 154, 155, 156, 157, 158, 159, 160, 162, 163, 171)),
    ('门诊南侧西部', ids(173, 181, 182, 183, 191, 192)),
    ('门诊大厅中央构图区', ids(185)),
    ('门诊南侧东部', ids(176, 187, 188, 189, 190, 193)),
]

# These are hypotheses for review, never replacements for JSON names.
CANDIDATES = {
    'S002': ('办公室', '暂无可靠备选', '西北翼部北排第2间，文字形态疑似“办公室”，笔画粘连，完整房名仍需确认。把握：低。'),
    'S003': ('值班室', '暂无可靠备选', '西北翼部北排第3间，文字疑似“值班室”，内含另划小间S010；字迹模糊。把握：低。'),
    'S031': ('采光庭院', '室内网格构图区', '北侧大厅西侧独立矩形网格。两候选共用网格构图依据，不能据此判断室内外或挑空。把握：低。'),
    'S065': ('采光带', '室内网格构图区', '纵向中段北部东沿长条连续网格。两候选共用网格形态依据，未能确定屋盖及可步入性质。把握：低。'),
    'S071': ('CT检查室', 'CT相关用房（具体名称待填）', '中段北部横排房间内疑见“CT”字符；两候选共用该文字线索，不能确认完整房名或设备功能。把握：中。'),
    'S073': ('CT检查室', 'CT相关用房（具体名称待填）', '位于S072东侧，字样疑含“CT”；两候选共用该文字线索，不能确认具体检查室名称。把握：中。'),
    'S086': ('采光带', '室内网格构图区', '承接S065向南延伸的长条网格，中间有分段。两候选共用网格形态依据，不能确定露天、挑空或室内可步入。把握：低。'),
    'S090': ('庭院', '室内景观区', '中段南部上端中央有曲线及植物状构图，支持景观用途；两候选共用该依据，无法判定是否露天或挑空。把握：中。'),
    'S119': ('采光庭院', '室内网格构图区', '中段与门诊交接处、公共通道围绕的横向长条网格。两候选共用图案依据，不能据此判定是否计室内面积。把握：低。'),
    'S130': ('暂无可靠候选', '—', '门诊北交通核西侧网格块，图案与邻近交通核构造密集叠合，不能仅按网格认定庭院或电梯厅。把握：低。'),
    'S173': ('采光庭院', '室内网格构图区', '门诊西候诊通道围绕的横向网格。两候选共用网格形态依据，屋盖、是否挑空及能否步入均不明。把握：低。'),
    'S176': ('采光庭院', '室内网格构图区', '门诊东候诊通道围绕的横向网格。两候选共用网格形态依据，屋盖、是否挑空及能否步入均不明。把握：低。'),
    'S181': ('输液区', '候诊区', '门诊西南大空间可见多排座位状符号；两候选共用座位布置依据，文字不清，不能仅凭座位区分输液和候诊。把握：低。'),
    'S185': ('挑空中庭', '室内景观构图区', '门诊大厅中央有方框及圆形构图；两候选共用该图案依据，不能确认挑空、楼层开洞或室内地面装饰。把握：低。'),
    'S187': ('药房', '库房', '门诊南侧东部西半块可见平行长条状布置，可能为货架；两候选共用疑似货架依据，不能据此确认药房。把握：低。'),
    'S189': ('药房', '库房', '门诊南侧东部大空间有多列长条状布置，可能为货架；两候选共用疑似货架依据，字迹不足以区分用途。把握：低。'),
}
AREA_IDS = set(ids(31, 65, 86, 90, 119, 130, 173, 176, 185))


def bounds(s):
    p = s['polygon_px']
    return (min(x for x, y in p), min(y for x, y in p),
            max(x for x, y in p), max(y for x, y in p))


def font(size):
    return ImageFont.truetype(FONT, size)


def draw_centered(draw, xy, text, f, color):
    box = draw.textbbox((0, 0), text, font=f)
    draw.text((xy[0] - (box[2] - box[0]) / 2,
               xy[1] - (box[3] - box[1]) / 2 - box[1]), text, font=f, fill=color)


def overlay(im, records, origin=(0, 0), scale=2):
    draw = ImageDraw.Draw(im)
    for rec in records:
        s = SPACES[rec['sid']]
        color = rec['color']
        p = [((x - origin[0]) * scale, (y - origin[1]) * scale)
             for x, y in s['polygon_px']]
        draw.line(p + [p[0]], fill=color, width=max(2, round(scale * 2)))
        x0, y0, x1, y1 = bounds(s)
        # Keep the small locator away from the usual central room-name position.
        y = y1 - min(15, (y1 - y0) / 4)
        crossings = []
        vertices = s['polygon_px']
        for (ax, ay), (bx, by) in zip(vertices, vertices[1:] + vertices[:1]):
            if (ay <= y < by) or (by <= y < ay):
                crossings.append(ax + (y - ay) * (bx - ax) / (by - ay))
        crossings.sort()
        spans = list(zip(crossings[::2], crossings[1::2]))
        left, right = max(spans, key=lambda span: span[1] - span[0])
        x = (left + right) / 2
        label = rec['number']
        f = font(round(12 * scale))
        box = draw.textbbox((0, 0), label, font=f)
        w = box[2] - box[0] + 8 * scale
        h = 17 * scale
        cx, cy = (x - origin[0]) * scale, (y - origin[1]) * scale
        draw.rounded_rectangle((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2),
                               radius=3 * scale, fill='white', outline=color, width=2)
        draw_centered(draw, (cx, cy), label, f, color)
        rec.setdefault('locator_px', [x, y])


def generate():
    listed = [sid for _, group in GROUPS for sid in group]
    assert len(listed) == len(set(listed)) == 130
    assert set(listed) == UNKNOWN
    if not (OUT / '修改前_标注说明.md').exists():
        shutil.copy2(MD, OUT / '修改前_标注说明.md')
    hashes = {name: hashlib.sha256((PROJECT / name).read_bytes()).hexdigest()
              for name in [DATA['image']['file'], 'annotation.json', '标注.svg']}
    records = []
    group_meta = []
    for gi, (name, group) in enumerate(GROUPS):
        start = len(records) + 1
        for sid in group:
            records.append({'number': f'{len(records) + 1:02d}', 'sid': sid,
                            'group': name, 'color': COLORS[gi]})
        group_meta.append((gi, name, records[start - 1:], start, len(records)))

    # Full original is preserved on a centered canvas; all locators directly
    # identify their own outlines, avoiding long crossing lines in dense rows.
    plan = IMAGE.resize((IMAGE.width * 2, IMAGE.height * 2))
    overlay(plan, records)
    sidebar, top = 650, 150
    canvas = Image.new('RGB', (plan.width + sidebar * 2, plan.height + top + 80), 'white')
    canvas.paste(plan, (sidebar, top))
    draw = ImageDraw.Draw(canvas)
    draw.text((sidebar, 30), '12 遂川县人民医院｜名称核对总图 01—130', font=font(48), fill='#202b3c')
    draw.text((sidebar, 95), '保留完整原图；彩框及框内核对号对应标注说明中的同号行。', font=font(26), fill='#525c6b')
    for side in (0, 1):
        y = top + 90
        x = 28 if side == 0 else sidebar + plan.width + 25
        for gi, name, recs, start, end in group_meta[side * 6:(side + 1) * 6]:
            draw.text((x, y), f'{start:02d}—{end:02d} {name}', font=font(29), fill=COLORS[gi])
            y += 48
            for rec in recs:
                draw.text((x + 15, y), f"{rec['number']}｜{rec['sid']} 名称待确认", font=font(24), fill=COLORS[gi])
                y += 36
            y += 60
    canvas.save(OUT / '00_名称核对总图_高清.png')
    preview = canvas.copy()
    preview.thumbnail((1800, 2200))
    preview.save(OUT / '00_名称核对总图_预览.png')

    prefix = '../../临时核对/' + OUT.name + '/'
    lines = [
        '## 房间名称与区域性质待确认表（2026-11-01）', '',
        '**共130项：112个房间、17个功能块、1个开放区域。** 其中9项还需核对网格、景观或中庭等区域性质及面积口径；这些项包含在130项内，不另计数量。', '',
        '本表依据当前 `annotation.json` 的130个 `unknown` 项与原图逐项对应。已有说明仅列出S编号，本次补充固定核对号、分区定位、候选依据和可填写确认栏。候选不代表已识别或已确认，未将候选写入JSON或正式SVG。', '',
        '**填写方法：**可直接修改“预估名称（可改）”，再把“我的确认／备注”改为“已确认”；也可在确认栏填写实际名称，或在聊天中回复 `01=房间名称，02=房间名称`。右端为重复核对号，不是答案列。编号01—130与S编号的对应保持固定，后续分批确认不重排。', '',
        '**读取顺序：**北部西翼→北侧大厅附属空间→北部东翼→纵向中段由北向南→门诊北排西侧／东侧→门诊中排西侧／东侧→南侧西部／中央／东部；各片区内先上后下，同排从左到右。原S编号不改动。总图在各彩框内直接标核对号，避免密集房间的长引线错指；旁栏列对应S编号，局部图保留同一核对号。', '',
        f'[查看原图]({DATA["image"]["file"]}) · [查看现有具名SVG](标注.svg) · [打开高清核对总图]({prefix}00_名称核对总图_高清.png)', '',
        f'![名称核对总图]({prefix}00_名称核对总图_高清.png)', '',
        '### 分区索引', '',
        '| 片区 | 核对号 | 待确认项数 |', '| --- | --- | --- |',
    ]
    lines += [f'| {name} | {start:02d}—{end:02d} | {len(recs)} |'
              for _, name, recs, start, end in group_meta]
    lines += ['', '表中“暂无可靠候选”表示现有房间级证据不足，不以常见医院配置补造名称。房间、功能块、开放区域沿用当前标注粒度，功能块不等于单一房间。', '']
    for gi, name, recs, start, end in group_meta:
        bb = [bounds(SPACES[r['sid']]) for r in recs]
        crop = (max(0, int(min(b[0] for b in bb)) - 60), max(0, int(min(b[1] for b in bb)) - 60),
                min(IMAGE.width, int(max(b[2] for b in bb)) + 60), min(IMAGE.height, int(max(b[3] for b in bb)) + 60))
        local = IMAGE.crop(crop).resize(((crop[2] - crop[0]) * 3, (crop[3] - crop[1]) * 3))
        overlay(local, recs, crop[:2], 3)
        filename = f'{gi + 1:02d}_{name}_核对{start:02d}-{end:02d}.png'
        local.save(OUT / filename)
        lines += [f'### {gi + 1}. {name}（{start:02d}—{end:02d}）', '',
                  f'![{name}局部核对]({prefix}{filename})', '',
                  '| 核对号 | S编号 | 预估名称（可改） | 备选名称 | 依据与把握 | 我的确认／备注 | 核对号（重复） |',
                  '| --- | --- | --- | --- | --- | --- | --- |']
        for rec in recs:
            sid, number = rec['sid'], rec['number']
            s = SPACES[sid]
            x0, y0, x1, y1 = bounds(s)
            kind = {'room': '房间', 'functional_block': '功能块', 'open_space': '开放区域'}[s['level']]
            location = f'{kind}；原图范围x={x0:.0f}—{x1:.0f}、y={y0:.0f}—{y1:.0f}。'
            if sid in CANDIDATES:
                candidate, alt, evidence = CANDIDATES[sid]
            else:
                candidate, alt = '暂无可靠候选', '—'
                evidence = '原图文字模糊或不足以读出完整名称，暂无可核实的房间级用途证据；不凭相邻房间或片区配置补名。把握：低。'
            note = '待确认'
            if sid in AREA_IDS:
                note += '；请补充露天／挑空、不计室内面积，或室内可步入、计室内面积；若为交通设施或装饰构图请说明'
            lines.append(f'| {number} | {sid} | {candidate} | {alt} | {location}{evidence} | {note} | {number} |')
        lines.append('')
    lines += ['### 区域性质与面积口径另核', '',
              'S031、S065、S086、S090、S119、S130、S173、S176、S185共9项，应先确认实际用途，再确认露天、挑空或室内可步入。名称确认不自动决定面积归属；当前均沿用草稿面积口径。', '',
              '**当前完成边界：**本次完成待确认清单与定位材料补充；130项仍待确认，医院平面标注仍为草稿。', '']
    old = MD.read_text()
    heading = '## 房间名称与区域性质待确认表（2026-11-01）'
    new_section = '\n'.join(lines)
    if heading in old:
        assert old[old.index(heading):] == new_section, 'Protect subsequent user input.'
    else:
        MD.write_text(old.rstrip() + '\n\n' + new_section)
    (OUT / '核对号映射.json').write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n')
    (OUT / '受保护文件哈希.json').write_text(json.dumps(hashes, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'items': len(records), 'levels': dict(Counter(SPACES[r['sid']]['level'] for r in records)),
                      'groups': len(GROUPS), 'document': str(MD)}, ensure_ascii=False))


if __name__ == '__main__':
    generate()
