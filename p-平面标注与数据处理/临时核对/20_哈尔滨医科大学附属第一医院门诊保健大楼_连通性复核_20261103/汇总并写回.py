from pathlib import Path
from collections import Counter
import hashlib
import html
import json
import re
import shutil

import 开口与关系判读 as C

OUT = Path(__file__).resolve().parent
PROJECT = OUT.parents[2] / 'p-平面标注与数据处理/标注试样/20_哈尔滨医科大学附属第一医院门诊保健大楼'
MD = PROJECT / '标注说明.md'
data = json.loads((OUT / '连通性拟定数据.json').read_text())
mapping = json.loads((OUT / '用户填写与合并映射.json').read_text())
types = json.loads(Path('/Users/hushili/.codex/skills/outpatient-plan-annotation/references/space-types.json').read_text())
spaces = {s['id']: s for s in data['spaces']}
aliases = mapping['aliases']
old_md = MD.read_text()
old_hash = hashlib.sha256(MD.read_bytes()).hexdigest()
rows = {}
for line in old_md.splitlines():
    cells = [html.unescape(x.strip()) for x in line.strip('|').split('|')]
    if len(cells) == 7 and re.fullmatch(r'\d+', cells[0]):
        rows[cells[1]] = cells
assert rows == mapping['rows'], '用户填写又有更新，请先重新读取，禁止覆盖。'

history = old_md.split('## 名称核对填写表', 1)[1].split('### 01—06', 1)[1]
history = '### 01—06' + history.split('## 本轮状态与后续顺序', 1)[0]
lines = []
for line in history.splitlines():
    cells = [x.strip() for x in line.strip('|').split('|')]
    if len(cells) == 7 and re.fullmatch(r'\d+', cells[0]):
        sid = cells[1]
        final = aliases.get(sid, sid)
        s = spaces[final]
        final_text = f'{final} {s["name"]}〔{types[s["type"]]}〕'
        if final != sid:
            final_text = f'{sid}已并入' + final_text
        evidence = cells[4].replace('【未确认】', '【历史候选】').replace('【图面已同步】', '【此前图面判断】')
        evidence = evidence.replace('JSON继续unknown。', '当时保留unknown，现已落实。')
        cells[4] = f'【本轮落实】{final_text}。原判读：{evidence}'
        line = '| ' + ' | '.join(cells) + ' |'
    elif '| 核对号 |' in line:
        line = line.replace('预估名称（可改）', '填写时预估名称（保留）')
    elif line.startswith('**范围核对F01'):
        line = '**范围核对F01落实结果：**按本图清晰连续范围，将S109并入S107急诊药局；两片间为轴网线和柱，未见实体隔墙。原83、85核对号及填写仍保留。这是图面自主修正，不记作用户已确认合并。'
    elif line.startswith('**我的确认／备注：**'):
        line = line.replace('**我的确认／备注：**', '**F01原填写（历史记录，原文保留）：**')
    lines.append(line)
history = '\n'.join(lines).strip()

counts = Counter(s['type'] for s in data['spaces'])
scale = '、'.join(f'{types[t]}{n}个' for t, n in counts.items())
prefix = f'''# 20号｜哈尔滨医科大学附属第一医院门诊保健大楼

**已按本图概念精度完成房名、范围和主要连通性复核。名称待确认0项；影响主要通路的待确认项0项。**

本轮已读取最新回填（包括32／S039乳腺扫描、33／S040管井、54／S066并入内科、82／S106并入护士分诊）。只依据20号原图、四张局部照片及本MD回填；19号未修改。保留原S编号和01—88核对号，合并后退役编号不复用，原填写继续保存在本文末段。

[查看原图](20_哈尔滨医科大学附属第一医院门诊保健大楼_原图.jpg)｜[查看最终标注](标注.svg)

## 房名、范围与规模

现有100个空间／区域，均有明确名称和标准功能类别：{scale}。原113片落实13项合并后为100片；没有通过重新编号改变既有空间身份。

已同步用户明确修正：S012离休干部保健诊、S021脑外暗室、S035厕所前室、S039乳腺扫描、S040管井、S077男科、S093担架轮椅室、S096库房、S103分发室等。S098按回填原文保存“后候药大厅”，未擅自删除“后”字。

范围保留本图室内主体；生活水箱间、消控及机房等不混作急诊。S028卫生间与S035厕所前室按真实隔墙和门位对齐；S093从原错含公共支廊的范围收窄，支廊归入S048；补齐S048横廊、S086南端门前厅区，并校正S090/S097之间实际门墙位置。外部台阶、坡道、雨篷、尺寸轴网不计入室内面积；未推定图外楼层。

JSON保留原图2444×3260像素坐标；SVG完整底图逆时针转正，显示变换为`(x转正,y转正)=(y原,2444-x原)`。原图未改动。室内相对面积已重新归一化，合计1；概念轮廓不代表实测面积。

### 合并落实与稳定编号

| 原核对号 | 退役S编号 | 保留S编号及最终名称 | 落实依据 |
| --- | --- | --- | --- |
'''
for m in mapping['merges']:
    prefix += f'| {m["original_review_number"]} | {m["retired_id"]} | {m["retained_id"]} {m["name"]} | {m["basis"]} |\n'
prefix += '''
46／S057的回填原文“妇产科和46合并”为自指；按同名相邻主间45／S056落实，原文保留在后面的填写栏。S107/S109按清晰连续图面自主合并；其余合并依据用户明确填写。合并后的同一功能块内部自连接和重复关系已去除。

## 连通性复核结果

现有109条关系：98条人员可达（access）、2条柜台服务（service）、9条建筑入口（entrance）。87条人员可达关系包含92个清晰门洞，已在JSON记录P001—P092原图近似坐标，并在SVG对应位置画红点和P编号；另外11条为无门位的概念连接，依据如下。建筑入口使用E01—E09，未混用室内P编号。

主要大厅、通道、诊疗及整体交通核在人员可达图中形成91个空间的同一连通分量，各入口接入这一通路。该检查只核本图标注关系；不借助“通常医院如此”补门，也不把未记关系当作不相通的负例。

- 急诊药局S107面向S108门厅的界面按柜台服务记录，工作人员门由北段S104进入；未把取药窗口当作人员穿行口。
- 挂号收费S110与S108同时保留柜台服务关系和下端独立人员门，两者不混同。
- 重新核实机房、厕所前室、中央交通核及右翼支廊的实际连接；撤回S048至S094转角处无直接门洞证据的旧关系，改由S104衔接。
- 右翼合并诊室之间仍清晰存在的跨功能块门，以及中央交通核朝门诊大厅的两组门，均保留定位；合并并未删除这些对外门洞。

### 无定位红点的概念连接

“布局推断”只表示有本图通行组织依据，不表示用户已确认；没有据此编造门位。

| 关系 | 空间对 | 图面依据 |
| --- | --- | --- |
'''
relations = {r['id']: r for r in data['relations']}
for rid, reason in C.CONCEPT.items():
    r = relations[rid]
    prefix += f'| {rid} | {r["source"]}—{r["target"]} | {reason} |\n'
prefix += '| R108 | S097—S098 | 门诊大厅与后候药大厅在交通核西南端连续，无实体分隔。 |\n'
prefix += '''
### 本轮不细究的内部细节

S014、S019、S029、S040、S053、S065、S089、S112为8处井道／检修空间，S047为污水泵间值班室。未见足够清晰且影响主要通路的人员入口，暂不补可达边、不编造门位；这9处不纳入上述91空间连通分量，也不要求逐项确认。这不表示其实际不相通。整体交通核与已合并功能块不再穷尽内部小间路线。

## 连通性局部图

局部图直接截自本轮SVG，红点为门洞、P号可回查JSON关系；S号和房名在对应空间内。以下均为已完成的复核展示，没有新增需重复填写的问题。原房名核对照片及确认栏继续保留在后文。

'''
parts = [
    ('A上', '左上功能翼上段', '诊室、生活水箱间和楼梯前室；门洞按图保留，井道不凭共墙推断入口。'),
    ('A下', '左上功能翼下段', '电梯候梯区、空调机房及其门洞；机房与楼梯、公共通道的门分别记录。'),
    ('B', '左中诊疗与厕所前室', '乳腺扫描、管井及修正后的厕所前室范围；候诊带向大厅连续开放。'),
    ('C上', '右上诊疗翼上段', '合并后的儿科、耳科、眼科、妇产科和心内；附间之间仍存在的门按功能块外连接保存。'),
    ('C下', '右侧诊疗翼中段', '抢救、治疗、检验、合并诊室及交通核；柜台界面不代替人员入口。'),
    ('D上', '中央交通核与北门厅', '北门厅、高干门厅、出入院办公及中央交通核；交通核按整体保存，未细分内部路线。'),
    ('D下E', '中央大厅、候药与中心药房', '门诊大厅、后候药大厅及南侧交通核；分发室经清晰单门连向中心药房。'),
    ('F', '右下急诊与公共服务', '担架轮椅室、护士分诊、急诊药局、挂号收费及急诊门厅；已分开柜台服务与人员通行。'),
]
for key, title, note in parts:
    prefix += f'### {title}\n\n![{title}门洞与空间](../../临时核对/{OUT.name}/连通局部_{key}.png)\n\n{note}\n\n'
prefix += '''## 校验与交付状态

正式校验待最后运行。全图及8组局部已逐处查看房名、范围、红点和入口；92个开口均已检查所属空间对，未发现距离任一端概念轮廓超过15像素的点。该距离只辅助发现错配，不代替门洞目检。

修改前四文件、最新原始回填、合并映射、逐关系判读及校验记录均保存在样本外的临时核对目录；样本目录保持原图、JSON、SVG、MD四文件。主要通路关键待确认项0项；名称待确认0项。下述辅助细节未穷尽，不影响本轮概念精度收尾。

## 原名称核对填写记录（保留）

以下01—88为原固定核对号，仍对应原S编号，用户“我的确认／备注”内容原样保留，包括尚未逐行改写的“待确认”。它们是历史填写原文，**不再表示当前尚未确认**；每行“依据与把握”开头已附本轮落实名称及合并去向。填写时预估和原判读仅供追溯，当前名称、范围与连通性以本文前段及现有JSON／SVG为准。

原内部核对数字图是合并前房名核对记录；现有合并范围见前述连通局部及最终SVG。

'''
new_md = prefix + history + '\n'
new_rows = {}
for line in new_md.splitlines():
    c = [html.unescape(x.strip()) for x in line.strip('|').split('|')]
    if len(c) == 7 and re.fullmatch(r'\d+', c[0]):
        new_rows[c[1]] = c
assert len(new_rows) == 88
for sid, old in rows.items():
    assert new_rows[sid][0] == old[0] and new_rows[sid][5:] == old[5:], sid
(OUT / '标注说明_拟定.md').write_text(new_md)
assert hashlib.sha256(MD.read_bytes()).hexdigest() == old_hash
(OUT / '写入前最新回填原文.md').write_text(old_md)
shutil.copy2(OUT / '连通性拟定数据.json', PROJECT / 'annotation.json')
shutil.copy2(OUT / '连通性复核预览.svg', PROJECT / '标注.svg')
MD.write_text(new_md)
print('WROTE JSON SVG MD; preserved 88 answers; original image untouched')
