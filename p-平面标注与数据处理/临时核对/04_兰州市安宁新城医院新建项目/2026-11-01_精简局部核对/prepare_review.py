from pathlib import Path
import hashlib
import json
import re
import shutil
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw, ImageFont


OUT = Path(__file__).resolve().parent
PROJECT = OUT.parents[2] / '标注试样/04_兰州市安宁新城医院新建项目'
OLD = OUT.parent / '2026-11-01_开口复核'
BACKUP = OUT / '修改前备份'
BACKUP.mkdir(exist_ok=True)
before_md = (PROJECT / '标注说明.md').read_text()
assert not BACKUP.joinpath('标注说明.md').exists(), '已有备份，避免重复执行'
answers = {}
for line in before_md.splitlines():
    cols = [c.strip() for c in line.strip('|').split('|')]
    if len(cols) == 6 and re.fullmatch(r'\d{2}', cols[0]):
        answers[cols[0]] = cols[4]
assert len(answers) == 14
assert set(answers.values()) == {'待确认'}, '发现用户答案，须先合并保留'
for path in PROJECT.iterdir():
    if path.is_file():
        shutil.copy2(path, BACKUP / path.name)

data = json.loads((PROJECT / 'annotation.json').read_text())
spaces = {s['id']: s for s in data['spaces']}
source = Image.open(PROJECT / data['image']['file']).convert('RGB')
font_path = '/System/Library/Fonts/Supplemental/Arial Unicode.ttf'
font = ImageFont.truetype(font_path, 23)
small = ImageFont.truetype(font_path, 21)
colors = {'04': '#6d28d9', '05': '#047857', '13': '#be185d', '14': '#b45309'}


def local_image(filename, box, targets, context, title):
    """Keep plan marks unobstructed; labels use a separate right margin."""
    zoom = 1.65
    pw = round((box[2] - box[0]) * zoom)
    ph = round((box[3] - box[1]) * zoom)
    im = Image.new('RGB', (pw + 370, ph + 110), 'white')
    im.paste(source.crop(box).resize((pw, ph), Image.Resampling.LANCZOS), (0, 60))
    draw = ImageDraw.Draw(im)
    draw.text((12, 12), title, fill='#18314c', font=font)
    for number, sid in targets:
        pts = [(round((x - box[0]) * zoom), round((y - box[1]) * zoom + 60))
               for x, y in spaces[sid]['polygon_px']]
        draw.line(pts + [pts[0]], fill=colors[number], width=4)
        draw.text((pw + 16, 80 + 42 * list(targets).index((number, sid))),
                  f'{number} | {sid} {spaces[sid]["name"]}',
                  fill=colors[number], font=font)
    for i, (text, color) in enumerate(context):
        draw.text((pw + 16, 210 + i * 40), text, fill=color, font=small)
    draw.text((12, ph + 72), '框内为本题目标；只确认连接，不必填写精确门位。',
              fill='#52677b', font=small)
    im.save(OUT / filename)


local_image('04-05_北部交通核.png', (1600, 1130, 2420, 1580),
            [('04', 'S040'), ('05', 'S041')],
            [('S038 住院专用通道（上方）', '#18314c'),
             ('S039 门斗（右上）', '#18314c'),
             ('S212 医疗主街（左侧）', '#18314c'),
             ('S042 中药房（下方）', '#18314c')],
            '04—05｜中药房北侧交通核：只确认对外连接')
local_image('13_急诊拍片.png', (1690, 3110, 2350, 3470), [('13', 'S092')],
            [('S228 北侧急诊通道', '#18314c'),
             ('S231/S229 南侧医技通道', '#18314c'),
             ('S091 CT（目标左侧）', '#18314c')],
            '13｜急诊拍片：确认与哪条通道相通')
local_image('14_东南交通核.png', (2040, 3360, 2410, 3700), [('14', 'S102')],
            [('S232 急诊通道（左侧）', '#18314c'),
             ('S101 急诊药房（上方）', '#18314c'),
             ('室外位于图面右／下侧', '#18314c')],
            '14｜急诊东南交通核：确认对外连接')

# An evidence-based conceptual inference; no invented opening or red dot.
assert not any({r['source'], r['target']} == {'S134', 'S136'}
               and r['type'] == 'access' for r in data['relations'])
data['relations'].append({'id': 'R281', 'source': 'S134', 'target': 'S136',
                          'type': 'access'})
(PROJECT / 'annotation.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
svg = (PROJECT / '标注.svg').read_text()
old_status = '246 个具名空间；本轮开口复核有 14 组连通疑点待确认'
assert old_status in svg
svg = svg.replace(old_status, '246 个具名空间；概念连通复核剩 4 项关键疑点待确认', 1)
note = ('R281：S134 更衣与 S136 出入院结算按布局推断概念可达；'
        '依据为同组更衣／值班小间统一朝结算工作区组织，未定位门洞，不新增红点。'
        '此判断不是用户确认。其他非目标内部细节见标注说明。')
end = svg.index('>') + 1
svg = svg[:end] + '<desc id="conceptual-connectivity-note">' + escape(note) + '</desc>' + svg[end:]
(PROJECT / '标注.svg').write_text(svg)

prefix = before_md.split('## 本轮补充')[0]
prefix = prefix.replace('空间名称已齐；本轮可确定开口与连接已更新，仍有 14 组连通性疑点待确认，整图连通复核尚未完成。',
                        '空间名称已齐；按概念级精度复核后，剩 **4 项关键连接**需要确认。请直接在下方局部图旁填写，整图尚未完成。')
prefix = prefix.replace('261 条，服务联系 8 条、人员可达 241 条',
                        '262 条，服务联系 8 条、人员可达 242 条')
rel = '../../临时核对/04_兰州市安宁新城医院新建项目/2026-11-01_精简局部核对/'
md = prefix + f'''## 本轮精度与处理

主要功能空间、交通核与通道的可达关系是本轮重点，不逐项追问管井、设备间或辅助小间内部的开门细节。246 个 S 编号、名称和轮廓沿用。

**开口：**233 个红点（225 个门洞、8 个无门开口），对应 211 条可达关系；另有 31 条无定位红点的概念连接。没有可辨门位时不增加红点。

**本次布局推断：**S134“更衣”与 S136“出入院结算”按同组小间面向结算工作区的组织关系，补入概念可达 R281；相邻的 S133、S135 已分别连接该工作区。S134 的具体门位不确定，未增加红点，此项不是用户已确认。

**退出逐项提问的旧号：**01 收费人员入口、02 药房边界窄分片、03／06／09／11／12 设备及检修小间、07／08 放射辅助小间，均按本轮不细究的内部细节保留，证据不足的连接继续留空；07 已有的两石膏单元内门保留。10 更衣按上述布局推断处理。退出提问不表示已确认或不相通。

[原图](04_兰州市安宁新城医院新建项目_原图.jpg) · [具名标注 SVG](标注.svg) · [原14项核对材料备份]({rel}修改前备份/标注说明.md)

## 只需填写以下 4 项

沿用旧核对号 **04、05、13、14**，避免与此前总图错配。每处可填写“同意”、实际相连的空间名称／S 编号，或“待确认”。不必补具体门位和内部路线；以下“我的判断”是助手建议，空白或未作答不代表你同意。

### 04—05｜中药房北侧两处交通核

![04和05：交通核、住院专用通道与药房]({rel}04-05_北部交通核.png)

**04 问题：S040 交通核是否从北侧 S038“住院人行专用通道”进入？**

我的判断：倾向连接北侧通道；南侧为设备带和药房支持空间，主街侧也未见明确入口。图上不能排除其他接入方式，因此只确认整体连接。

**我的确认／备注（04）：** 待填写（同意，或写实际相连空间，可多处）

**05 问题：S041 交通核是否从北侧 S039“门斗”进入？**

我的判断：倾向从北侧门斗衔接；西侧隔着药房支持小间，不能据此直接连中药房。北侧分界仍不清楚。

**我的确认／备注（05）：** 待填写（同意，或写实际相连空间，可多处）

### 13｜急诊拍片 S092

![13：拍片、CT及南北通道]({rel}13_急诊拍片.png)

**问题：S092“拍片”连接南侧医技通道，还是北侧急诊通道？**

我的判断：倾向南侧 S231／S229 医技通道；南侧是该排检查用房的公共通行带，但拍片室门线不足以确定。北侧通道为 S228，左侧 CT 为 S091。

**我的确认／备注（13）：** 待填写（南侧／北侧／两侧，或写实际相连空间）

### 14｜急诊东南交通核 S102

![14：东南交通核及急诊通道、药房]({rel}14_东南交通核.png)

**问题：S102 交通核是否直接连接西侧 S232“急诊通道”？**

我的判断：倾向服务西侧急诊诊疗区；但该侧未见清晰开口，仍可能经北侧药房或室外独立进入。这会改变交通核对外连接，需要你判断。

**我的确认／备注（14）：** 待填写（同意，或写实际相连空间／仅通室外）

**完成边界：**上述 4 项仍待确认；其余未记录连接不作为不可通行负例。你填写并保存后，再同步明确答案并完成校验与目检。
'''
(PROJECT / '标注说明.md').write_text(md)

report = {
    'pending_review_numbers': ['04', '05', '13', '14'],
    'removed_from_questions': ['01', '02', '03', '06', '07', '08', '09', '10', '11', '12'],
    'inferred_relation': data['relations'][-1],
    'opening_count': sum(len(r.get('openings', [])) for r in data['relations']),
    'source_sha256': hashlib.sha256((PROJECT / data['image']['file']).read_bytes()).hexdigest(),
}
(OUT / '本轮处理记录.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(report, ensure_ascii=False, indent=2))
