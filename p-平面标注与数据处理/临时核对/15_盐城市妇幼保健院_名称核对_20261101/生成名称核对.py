from pathlib import Path
from collections import Counter
from hashlib import sha256
import json
import re
import shutil

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[3]
PROJECT = ROOT / 'p-平面标注与数据处理/标注试样/15_盐城市妇幼保健院'
OUT = Path(__file__).resolve().parent
MD = PROJECT / '标注说明.md'
FONT = '/System/Library/Fonts/STHeiti Medium.ttc'
DATA = json.loads((PROJECT / 'annotation.json').read_text())
SOURCE = Image.open(PROJECT / DATA['image']['file']).convert('RGB')
UNKNOWN = [s for s in DATA['spaces'] if s['type'] == 'unknown']
GROUPS = [
    '中央北段', '西北横翼', '东北横翼', '中西蓝色片区',
    '中东蓝色片区', '中西紫色片区', '中央中段', '中东黄色片区',
    '西纵翼上片区', '中央南段及东侧独立区', '西纵翼下片区',
    '西侧绿色片区', '西南粉色片区', '南端东侧及最南端',
]
COLORS = ['#c33825', '#1763ab', '#8545a0', '#00867d', '#ad3962',
          '#765225', '#214fa0', '#ab6500', '#6c43a1', '#14796a',
          '#b13e28', '#32669b', '#9c3565', '#5b6b21']
LEVELS = {'room': '房间', 'functional_block': '功能块',
          'open_space': '开放区域', 'semi_open_space': '半开放服务区'}


def bounds(s):
    xs, ys = zip(*s['polygon_px'])
    return min(xs), min(ys), max(xs), max(ys)


def group(s):
    x, y, _, _ = bounds(s)
    if y < 970 and 1100 <= x < 1340:
        return 0
    if y < 600:
        return 1 if x < 1100 else 2
    if y < 1400:
        if x < 680:
            return 5
        if x < 1100:
            return 3
        if x < 1350:
            return 6
        return 4 if x < 1760 else 7
    if x > 1000 and y < 1900:
        return 9
    if y < 1870:
        return 8
    if y < 2257:
        return 10
    if y < 2527:
        return 11
    if x < 700 and y < 2895:
        return 12
    return 13


def inside(point, polygon):
    x, y = point
    result = False
    for (ax, ay), (bx, by) in zip(polygon, polygon[1:] + polygon[:1]):
        if (ay > y) != (by > y) and x < (bx-ax)*(y-ay)/(by-ay)+ax:
            result = not result
    return result


def label_position(s):
    x1, y1, x2, y2 = bounds(s)
    # Place labels inside the polygon, including concave open regions.
    candidates = [(x1 + 12, y1 + 9), ((x1+x2)/2, (y1+y2)/2)]
    candidates += [(x, y) for y in range(int(y1)+9, int(y2)-5, 12)
                   for x in range(int(x1)+12, int(x2)-8, 15)]
    for x, y in candidates:
        if all(inside((x+dx, y+dy), s['polygon_px'])
               for dx in [-9, 9] for dy in [-5, 5]):
            return x, y
    return (x1+x2)/2, (y1+y2)/2


items = []
for gi in range(len(GROUPS)):
    subset = sorted([s for s in UNKNOWN if group(s) == gi],
                    key=lambda s: (bounds(s)[1], bounds(s)[0], s['id']))
    for s in subset:
        items.append({'number': f'{len(items)+1:02d}', 'id': s['id'],
                      'group': gi, 'space': s})
assert len(items) == 336


def overlay(selected, crop, scale, sidebar=False):
    x1, y1, x2, y2 = crop
    margin = 210 if sidebar else 0
    image = Image.new('RGB', (int((x2-x1+margin)*scale),
                             int((y2-y1)*scale)), 'white')
    image.paste(SOURCE.crop(tuple(map(int, crop))).resize(
        (int((x2-x1)*scale), int((y2-y1)*scale)), Image.Resampling.LANCZOS),
        (int(margin*scale), 0))
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(FONT, int(8*scale))
    for item in selected:
        s = item['space']
        color = COLORS[item['group']]
        polygon = [((x-x1+margin)*scale, (y-y1)*scale)
                   for x, y in s['polygon_px']]
        draw.line(polygon + polygon[:1], fill=color, width=max(2, int(scale)))
        x, y = label_position(s)
        x, y = (x-x1+margin)*scale, (y-y1)*scale
        label = item['number']
        box = draw.textbbox((x, y), label, font=font, anchor='mm')
        draw.rounded_rectangle((box[0]-2, box[1]-1, box[2]+2, box[3]+1),
                               radius=2, fill='white', outline=color)
        draw.text((x, y), label, font=font, fill=color, anchor='mm')
    return image


before = MD.read_text()
if '## 名称核对填写表' in before:
    raise RuntimeError('已有填写表，须读取并保留已有填写后再续作。')
backup = OUT / '修改前备份'
backup.mkdir(exist_ok=True)
shutil.copy2(MD, backup / MD.name)
hashes = {p.name: sha256(p.read_bytes()).hexdigest()
          for p in PROJECT.iterdir() if p.name != MD.name}

overview = overlay(items, (0, 0, SOURCE.width, SOURCE.height), 2, sidebar=True)
draw = ImageDraw.Draw(overview)
font = ImageFont.truetype(FONT, 23)
draw.text((20, 30), '15 盐城市妇幼保健院', fill='#222222', font=font)
draw.text((20, 70), '名称未确认：336项', fill='#222222', font=font)
draw.text((20, 110), '框内数字对应填写表', fill='#222222', font=font)
for gi, title in enumerate(GROUPS):
    ss = [item for item in items if item['group'] == gi]
    y = 180 + gi * 118
    draw.text((20, y), f'{gi+1:02d} {title}', font=font, fill=COLORS[gi])
    draw.text((20, y+34), f"核对 {ss[0]['number']}—{ss[-1]['number']}",
              font=font, fill=COLORS[gi])
overview.save(OUT / '名称核对总图.png')
overview.thumbnail((1600, 2200))
overview.save(OUT / '总图检查.jpg')

for gi, title in enumerate(GROUPS):
    ss = [item for item in items if item['group'] == gi]
    boxes = [bounds(item['space']) for item in ss]
    crop = (max(0, min(b[0] for b in boxes)-25),
            max(0, min(b[1] for b in boxes)-25),
            min(SOURCE.width, max(b[2] for b in boxes)+25),
            min(SOURCE.height, max(b[3] for b in boxes)+25))
    filename = f'{gi+1:02d}_{title}_核对{ss[0]["number"]}-{ss[-1]["number"]}.png'
    overlay(ss, crop, 3).save(OUT / filename)
    for item in ss:
        item['detail'] = filename

relative = Path('../../临时核对') / OUT.name
intro = [
    '## 名称核对填写表', '',
    '**本次清单：336 项未确认名称，其中房间 308 项、功能块 12 项、开放区域 11 项、半开放服务区 5 项。**', '',
    '这份表列出当前 JSON 中全部 `unknown` 项；“未确认”表示尚无可采用的确定名称，'
    '不等同于每一处原图文字都完全无法辨认。当前原图文字较模糊，不能仅凭色块、家具或常见配置确定房名。', '',
    '按相邻片区分组，片区内先上后下，同一排从左到右；原 S 编号全部保留。'
    '旧 `/tmp/outpatient15-review` 已不存在，无法恢复其中旧核对号。'
    '以下为本次重新建立并持久保存的核对号；若沿用旧聊天答复，请用 S 编号，避免新旧核对号混淆。', '',
    '可直接填写“预估名称（可改）”，再将“我的确认／备注”改为“已确认”；'
    '也可在确认栏直接填实际名称，或在聊天中按 `01=名称，02=名称` 分批回复。'
    '最右侧只是同一核对号的重复显示，不是答案栏。没有可靠候选的项不强行猜名。', '',
    '图上彩框内数字与表格核对号一致；密集房间采用框内编号，避免跨房间引线遮挡原图。'
    '各片区附三倍放大定位图；放大便于定位，但不能恢复原图已丢失的文字细节。', '',
    f'[原图]({DATA["image"]["file"]}) · [现有标注 SVG](标注.svg) · '
    f'[高清核对总图]({relative}/名称核对总图.png)', '',
    f'![15号医院名称核对总图]({relative}/名称核对总图.png)', '',
    '| 片区 | 核对号 | 数量 |', '| --- | --- | --- |',
]
for gi, title in enumerate(GROUPS):
    ss = [i for i in items if i['group'] == gi]
    intro.append(f'| {gi+1:02d} {title} | {ss[0]["number"]}—{ss[-1]["number"]} | {len(ss)} |')

for gi, title in enumerate(GROUPS):
    ss = [i for i in items if i['group'] == gi]
    intro += ['', f'### {gi+1:02d} {title}（{len(ss)}项）', '',
              f'![{title}名称定位]({relative}/{ss[0]["detail"]})', '',
              '| 核对号 | S编号 | 预估名称（可改） | 备选名称 | 依据与把握 | 我的确认／备注 | 核对号（重复） |',
              '| --- | --- | --- | --- | --- | --- | --- |']
    for item in ss:
        s, number = item['space'], item['number']
        x, y, _, _ = bounds(s)
        evidence = (f'{title}，{LEVELS[s["level"]]}，原图左上定位约({int(x)}, {int(y)})；'
                    '暂无可靠的房间级文字依据，位置及色块不能确定用途。把握：低。')
        note = '待确认'
        if s['id'] == 'S274':
            note += '；另请注明露天／挑空不计室内面积，或室内可步入计室内面积'
        intro.append(f'| {number} | {s["id"]} | 暂无可靠候选 | — | {evidence} | {note} | {number} |')

section = '\n'.join(intro) + '\n\n'
lines = before.splitlines()
result = []
for line in lines:
    if line.startswith('**名称待确认：**'):
        result.append('**名称待确认：**共 336 项，详见上方分区核对表；当前仍为未完成草稿。')
    elif line.startswith('**当前状态：**'):
        result.append('**当前状态：**标注草稿，336 个名称未确认；结构检查通过不代表名称、'
                      '功能范围或整张图的标注已完成。本次核对号与 S 编号映射、总图及局部图'
                      f'保存于 `{relative}`；已有 S001—S426 全部保留。')
    else:
        result.append(line)
result = '\n'.join(result) + '\n'
anchor = '**类型与数量：**'
index = result.index(anchor)
result = result[:index] + section + result[index:]
MD.write_text(result)
mapping = [{k: v for k, v in item.items() if k != 'space'} for item in items]
(OUT / '核对号映射.json').write_text(json.dumps(mapping, ensure_ascii=False, indent=2)+'\n')
(OUT / '修改前文件哈希.json').write_text(json.dumps(hashes, ensure_ascii=False, indent=2)+'\n')
print(json.dumps({'items': len(items), 'by_level': dict(Counter(s['level'] for s in UNKNOWN)),
                  'groups': {title: sum(i['group']==gi for i in items)
                             for gi, title in enumerate(GROUPS)},
                  'markdown': str(MD)}, ensure_ascii=False, indent=2))
