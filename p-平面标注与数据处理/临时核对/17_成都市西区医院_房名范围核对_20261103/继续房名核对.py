from pathlib import Path
import hashlib
import importlib.util
import json
import re
import sys

from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon, Point


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SAMPLE = ROOT / 'p-平面标注与数据处理/标注试样/17_成都市西区医院'
SKILL = Path('/Users/hushili/.codex/skills/outpatient-plan-annotation')
spec = importlib.util.spec_from_file_location('annotation_tools', SKILL / 'scripts/annotation_tools.py')
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)
data = json.loads((SAMPLE / 'annotation.json').read_text())
before = json.loads(json.dumps(data))
md = (SAMPLE / '标注说明.md').read_text()
assert data['image']['width'] == 2444 and len(data['spaces']) == 49
spaces = {s['id']: s for s in data['spaces']}
spaces['S013']['name'] = '值班'
spaces['S013']['type'] = 'staff_support'
assert before['relations'] == data['relations']
assert all(s['polygon_px'] == spaces[s['id']]['polygon_px'] for s in before['spaces'])
(SAMPLE / 'annotation.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
api.render(data, SAMPLE / 'annotation.json', SAMPLE / '标注.svg')
api.summary(data, OUT / '自动概览_供合并.md')

mapping = [('01', 'S001'), ('02', 'S004'), ('03', 'S012'),
           ('04', 'S013'), ('05', 'S018'), ('06', 'S021')]
colors = {'01': '#b44021', '02': '#b44021', '03': '#2163a3',
          '04': '#2163a3', '05': '#8048a4', '06': '#8048a4'}
# Each badge stays inside its room, away from the original room-name text.
anchors = {'01': (301, 819), '02': (301, 883), '03': (675, 1424),
           '04': (789, 1413), '05': (1470, 823), '06': (1314, 917)}
image = Image.open(SAMPLE / data['image']['file']).convert('RGB')
fontpath = '/System/Library/Fonts/Supplemental/Arial Unicode.ttf'


def review(box, nums, filename, scale=3):
    base = image.crop(box).resize(((box[2]-box[0])*scale, (box[3]-box[1])*scale), Image.Resampling.LANCZOS)
    overlay = Image.new('RGBA', base.size)
    draw = ImageDraw.Draw(overlay)
    font = ImageFont.truetype(fontpath, 17 * scale)
    boxes = {}
    for num, sid in mapping:
        if num not in nums:
            continue
        pts = [((x-box[0])*scale, (y-box[1])*scale) for x, y in spaces[sid]['polygon_px']]
        color = colors[num]
        draw.line(pts+[pts[0]], fill=color, width=2*scale)
        x, y = anchors[num]
        text = draw.textbbox((0, 0), num, font=font)
        w, h = (text[2]-text[0])/scale+8, (text[3]-text[1])/scale+6
        bounds = (x-w/2, y-h/2, x+w/2, y+h/2)
        from shapely.geometry import box as shape_box
        assert Polygon(spaces[sid]['polygon_px']).covers(shape_box(*bounds)), (num, bounds)
        rect = [(bounds[0]-box[0])*scale, (bounds[1]-box[1])*scale,
                (bounds[2]-box[0])*scale, (bounds[3]-box[1])*scale]
        draw.rounded_rectangle(rect, radius=3*scale, fill='white', outline=color, width=scale)
        draw.text(((x-box[0])*scale, (y-box[1])*scale), num, font=font, fill=color, anchor='mm')
        boxes[num] = {'id': sid, 'badge_box_px': bounds, 'inside_room': True}
    Image.alpha_composite(base.convert('RGBA'), overlay).convert('RGB').save(OUT / filename)
    return boxes


checks = review((0, 0, 2444, 3260), [n for n, _ in mapping], '名称核对总图_室内编号.jpg', 2)
review((228, 760, 860, 1170), ['01', '02'], '局部_01-02_室内编号.png')
review((565, 1358, 889, 1625), ['03', '04'], '局部_03-04_室内编号.png')
review((1200, 765, 1585, 1120), ['05', '06'], '局部_05-06_室内编号.png')
for name, box in [('01-02', (228, 760, 860, 1170)),
                  ('03-04', (565, 1358, 889, 1625)),
                  ('05-06', (1200, 765, 1585, 1120))]:
    image.crop(box).resize(((box[2]-box[0])*3, (box[3]-box[1])*3), Image.Resampling.LANCZOS).save(OUT / f'局部_{name}_无标记原图.png')

# Independent range overview: stable S identifiers only, with no room-name guesses.
base = image.copy().convert('RGBA')
overlay = Image.new('RGBA', image.size)
draw = ImageDraw.Draw(overlay)
font = ImageFont.truetype(fontpath, 12)
for s in data['spaces']:
    pts = [tuple(p) for p in s['polygon_px']]
    draw.polygon(pts, fill=(30, 100, 180, 24))
    draw.line(pts+[pts[0]], fill='#2163a3', width=2)
    p = Polygon(pts).representative_point()
    draw.text((p.x, p.y), s['id'], fill='#174775', font=font, anchor='mm', stroke_width=2, stroke_fill='white')
ranges = Image.alpha_composite(base, overlay).convert('RGB')
ranges.save(OUT / '空间范围总图.jpg')
ranges.crop((225, 760, 1755, 1730)).resize((2295, 1455)).save(OUT / '范围目检_北部.jpg')
ranges.crop((225, 1690, 1790, 2700)).resize((2347, 1515)).save(OUT / '范围目检_南部.jpg')

prefix = '../../临时核对/17_成都市西区医院_房名范围核对_20261103/'
oldprefix = '../../临时核对/16-20_名称核对_20261103/17_成都市西区医院/'
md = md.replace(oldprefix+'名称核对总图.jpg', prefix+'名称核对总图_室内编号.jpg')
for group in ['01-02', '03-04', '05-06']:
    md = md.replace(oldprefix+f'局部_{group}.jpg', prefix+f'局部_{group}_室内编号.png')
md = md.replace(oldprefix.rstrip('/'), prefix.rstrip('/'))
md = md.replace('6 个空间名称尚未确认', '5 个空间名称尚未确认')
md = md.replace('未确认功能 6 个', '未确认功能 5 个')
md = md.replace('工作人员支持用房 1 个', '工作人员支持用房 2 个')
md = md.replace('、S013 名称未确认', '')
md = md.replace('本轮整理：2026-11-03。现有草稿含 6 项待确认名称；固定核对号和 S 编号沿用原记录。',
                '本轮续作：2026-11-03。当前为5项待确认名称；04／S013已由助手按原图辨读为“值班”并同步。01—06固定映射全部保留，剩余项不重排。')
md = md.replace('![6项名称核对总图]', '![01—06固定核对号总图：5项待确认、04已自主辨读]')
md = md.replace('例如 `16号：01=诊室，02=治疗室`', '例如 `17号：01=诊室，02=治疗室`')
md = md.replace('候选和依据从本图历史核对记录恢复，仍需对照原图核实；候选未写入 JSON。所有未确认项继续保留 `unknown`，SVG 继续显示“名称未确认”。',
                '本轮已放大本目录原图重新判读。候选仅留在此表，未确认项在JSON中继续保留 `unknown`；04为助手据原图辨读，不记作用户确认。核对数字位于房间内部，不使用外侧标签或长引线；旁附无标记原图便于查看原字。')
md = md.replace('| 01 | S001 | 暂无可靠候选 | — | 无房名、无明确家具符号；边界独立 暂无可靠房间用途依据，请填写实际名称。 把握：低。 | 待确认 | 01 |',
                '| 01 | S001 | 暂无可靠候选 | 卫生间辅助空间／竖井（仅范围疑点） | 无可读房名和家具；位于卫生间西北角，北侧为独立小矩形。仅凭邻接不能定用途，也不能确定是否应作为房间计入。请同时说明保留、合并或排除范围；当前保持原轮廓与面积口径。把握：低。 | 待确认 | 01 |')
md = md.replace('| 03 | S012 | 值班室 | 休息室 | 两组床形家具，临近值房与更衣 上述候选共用此线索，现有证据不能区分。 把握：中。 | 待确认 | 03 |',
                '| 03 | S012 | 人流（新辨读候选） | 原候选：值班室／休息室 | 放大后两字更似“人流”，两组长形家具可解释为诊疗床或休息床；家具本身不能区分用途。“人流”依据字形，值班／休息仅依床形与相邻更衣推测。原字仍不够清楚，暂不定名。把握：中。 | 待确认 | 03 |')
md = md.replace('| 04 | S013 | 值班室（图字似“值房”） | — | 床形家具；两字房名末字似“房” 把握：中。 | 待确认 | 04 |',
                '| 04 | S013 | 值班 | 原候选：值班室（图字似“值房”） | 本轮放大后可辨“值班”，结合床形家具；按原图两字同步名称“值班”，类别为工作人员支持用房。把握：高。 | 助手据原图已同步（非用户确认；原栏为“待确认”） | 04 |')
md = md.replace('| 06 | S021 | 妇科诊室 | 内科诊室 | “科”可辨；首字受座椅图形干扰 仅为待核候选，当前文字或房间级证据不足。 上述候选共用此线索，现有证据不能区分。 把握：低。 | 待确认 | 06 |',
                '| 06 | S021 | 骨科（新辨读候选） | 原候选：妇科诊室／内科诊室 | 首字被椅子符号干扰，放大后上部框形更似“骨”；“科”可辨。妇科／内科为历史弱候选，不能仅由急诊位置确定。S023另有清晰“内科”文字，但不能据此排除同名。把握：低。 | 待确认 | 06 |')
for group in ['01-02', '03-04', '05-06']:
    pattern = rf'(!\[[^\n]*\]\({re.escape(prefix)}局部_{group}_室内编号.png\))'
    md = re.sub(pattern, r'\1\n\n[查看同范围无标记原图]('+prefix+f'局部_{group}_无标记原图.png)', md)
md += '''
## 本轮范围与类别复核

![49个空间范围与稳定S编号](空间范围图路径)

**范围结果：**已对照原图检查左侧完整首层主体的49个既有空间轮廓；本轮不改S编号、多边形、面积比例或空间层级。卫生间仍按组团、楼梯电梯按交通核、连续大厅与通道按概念分区保存。右侧截断七层图、北侧斜线屋盖、室外台阶及雨棚仍不计入。

**尚待判断的范围：**01／S001的室内属性及用途仍不清楚，可能影响是否单列房间和室内面积；请在原01行确认栏写明保留、合并到哪个S编号或排除。未得到明确范围意见前，不自行删除或合并。其他5个名称核对号对应的现有房间边界可定位，名称待定不等于范围已获用户确认。

**类别结果：**S013“值班”归入 `staff_support`；其余已命名空间沿用本图现有共享类别。5项未定名称继续为 `unknown`，不以候选类别替代。

**连通性状态：**本轮未开展连通复核，89条既有关系原样保留；当前无定位开口红点，53条既有access均无openings，不能据此称门洞已核验。待用户明确说“房间标注完毕”后，再读取最新填写同步名称、合并或范围排除，并复核主要路径与清晰开口。

**文件与填写保护：**修改前四文件和既有核对材料已备份到本轮外部核对目录；现有确认栏均为默认“待确认”，未发现用户已填写答案。01—06及其S编号映射不变，原候选有调整的行保留历史候选说明。
'''.replace('空间范围图路径', prefix+'空间范围总图.jpg')
(SAMPLE / '标注说明.md').write_text(md)
(OUT / '固定核对映射.json').write_text(json.dumps([
    {'number': n, 'id': sid, 'status': '助手据原图已同步' if sid == 'S013' else '待确认',
     **checks[n]} for n, sid in mapping], ensure_ascii=False, indent=2)+'\n')
print(json.dumps({'pending': [s['id'] for s in api.unresolved(data)],
                  'relations_unchanged': before['relations'] == data['relations'],
                  'polygons_unchanged': True, 'review_badges_inside': checks}, ensure_ascii=False, indent=2))
