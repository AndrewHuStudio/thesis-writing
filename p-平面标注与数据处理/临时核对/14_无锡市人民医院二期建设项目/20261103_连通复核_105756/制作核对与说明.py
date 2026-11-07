from pathlib import Path
from collections import Counter
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon
import json
import os
import re

WORK = Path(__file__).resolve().parent
PLAN = WORK.parents[2] / '标注试样/14_无锡市人民医院二期建设项目'
data = json.loads((PLAN / 'annotation.json').read_text())
original = Image.open(PLAN / data['image']['file']).convert('RGB')
font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 22)
questions = [
    {
        'id': 'L01', 'title': '北侧 TPN 配置空间 S005 的主要人员入口',
        'box': (1450, 145, 1840, 380), 'targets': ['S005', 'S006', 'S012'],
        'question': 'S005 是否直接通向配液区内通道 S012？若经其他空间进入，请写直接相连的空间。',
        'judgment': '东北角能见门，南侧边界为双线，不能可靠判断是人员开口还是台面／窗口；原 R003 暂撤下，未把旁边厕所区当作通行路径。',
        'answer': '待填写（如：直接通 S012；或：先通 Sxxx，再到通道）',
    },
    {
        'id': 'L02', 'title': '北侧护士及办公组团 S037 的对外入口',
        'box': (2130, 385, 2510, 590), 'targets': ['S025', 'S027', 'S037', 'S033', 'S034', 'S035', 'S036'],
        'question': '护士空间 S037 的主要入口直接连入口门廊 S025，还是西侧公共通道 S027，或其他空间？',
        'judgment': '四间办公用房通向 S037 的门清楚；S037 北侧较像窗墙，西端入口亦不够清楚。原 R021 暂撤下，不据共墙补连。',
        'answer': '待填写（填写 S037 直接相连空间；若通 S025 可直接写“通 S025”）',
    },
    {
        'id': 'L03', 'title': 'EICU／抢救组团的主要外部入口',
        'box': (960, 1615, 1280, 1980), 'targets': ['S152', 'S153', 'S154', 'S155', 'S156', 'S157', 'S158', 'S165', 'S166'],
        'question': 'EICU S152／抢救 S155 组团从哪条公共通道进入，门首先进入哪个空间？',
        'judgment': '污洗、处置改接 EICU；治疗、器械改接抢救组团内部。东侧边界看似连续实体墙，不能继续把这些小间直接接东侧通道 S166。倾向组团由南侧 S165 进入，但开口不足以确认，暂未补该外部连接。',
        'answer': '待填写（如：S165→S155→S152；或：S166→S152；也可写实际路径）',
    },
    {
        'id': 'L04', 'title': '急诊药房 S170 的人员入口',
        'box': (455, 1890, 870, 2175), 'targets': ['S169', 'S170', 'S173', 'S165', 'S172'],
        'question': '药房 S170 的工作人员从哪个空间直接进入？',
        'judgment': '药房与急诊大厅 S172 的服务联系保留；北侧服务界面不能直接认作人员开门，现图也不足以判定是否经一次候诊 S173 或侧向辅助路线进入，因此不补猜测的人员连接。',
        'answer': '待填写（填写直接相连空间；若为独立外门也请注明）',
    },
    {
        'id': 'L05', 'title': '南部门厅 S197 与扶梯交通核 S196',
        'box': (1555, 1595, 1840, 2175), 'targets': ['S174', 'S105', 'S196', 'S197', 'S198', 'S199'],
        'question': '门厅 S197 能否直接进入上方扶梯交通核 S196？若另有室内连接，请写相连空间。',
        'judgment': 'S196 北门已确认接 S105；S197 东侧双门和 S198 东侧独立外门清楚。S197 与 S196 交界线较重，是否仍可进入扶梯下端不清楚，原 R177 暂撤下；不能用门厅名称推定相通。S198 未见向西通 S197 的门，已改为独立外入口。',
        'answer': '待填写（如：S197 与 S196 相通；或：不通，仅分别外开；可补其他实际连接）',
    },
]

parts = [
    '## 连通性关键待确认（L01—L05）', '',
    '本轮先完成可依据图面判断的连接、门洞及误连修正，只保留以下 5 项会改变主要可达关系的问题。请直接在每题图片下的“我的确认／备注”填写；可以分批回答，原名称核对号 01—55 不变。', '',
    '图中蓝框只标 S 编号，未画推测的门位；无标记原图可用于辨认细节。未确认的候选关系暂不写入核心 JSON。', '',
]
for q in questions:
    x0, y0, x1, y1 = q['box']
    scale = 3 if y1 - y0 < 400 else 2
    crop = original.crop(q['box']).resize(((x1-x0)*scale, (y1-y0)*scale))
    raw_path = WORK / f'{q["id"]}_无标记原图.png'
    crop.save(raw_path)
    draw = ImageDraw.Draw(crop)
    for s in data['spaces']:
        pt = Polygon(s['polygon_px']).representative_point()
        if not (x0 < pt.x < x1 and y0 < pt.y < y1):
            continue
        x, y = (pt.x-x0)*scale, (pt.y-y0)*scale
        color = '#b45309' if s['id'] in q['targets'] else '#1d4ed8'
        draw.rectangle((x-30,y-15,x+33,y+15), fill='white', outline=color, width=2)
        draw.text((x-28,y-13), s['id'], fill=color, font=font)
    labelled = WORK / f'{q["id"]}_局部.png'
    crop.save(labelled)
    img = Path(os.path.relpath(labelled, PLAN)).as_posix()
    raw = Path(os.path.relpath(raw_path, PLAN)).as_posix()
    parts += [f'### {q["id"]}｜{q["title"]}', '', f'![{q["id"]}：{q["title"]}]({img})', '',
              f'[查看无标记原图]({raw})', '', f'**问题：**{q["question"]}', '',
              f'**我的判断：**{q["judgment"]}', '', f'**我的确认／备注：**{q["answer"]}', '']

md = (PLAN / '标注说明.md').read_text()
backup_md = (WORK / '修改前备份/标注说明.md').read_text()
assert md == backup_md, '用户在复核期间修改了说明，需重读后增量合并。'
counts = Counter(r['type'] for r in data['relations'])
opening_count = sum(len(r.get('openings', [])) for r in data['relations'])
located = sum(bool(r.get('openings')) for r in data['relations'] if r['type'] == 'access')
md = md.replace('｜名称已确认，连通待复核', '｜名称已确认，连通复核中')
md = re.sub(r'^名称确认已同步：[^\n]*', f'199 个空间／区域名称已齐。本轮已复核可辨连接并补录 {opening_count} 个门洞；仍有 5 项关键连通关系待确认，整图尚未完成。', md, flags=re.M)
md = re.sub(r'\*\*连接关系：\*\*[^\n]*', f'**连接关系：**{len(data["relations"])} 条，人员可达 {counts["access"]} 条、服务联系 {counts["service"]} 条、共墙 {counts["shared_wall"]} 条、入口连接 {counts["entrance"]} 条。', md)
md = re.sub(r'\*\*入口：\*\*[^\n]*', '**入口：**' + '、'.join(r['name'] for r in data['relations'] if r['type']=='entrance') + '。入口类别按用途归纳，不表达门禁权限。', md)
md = re.sub(r'\*\*名称待确认：\*\*[^\n]*', '**名称待确认：**0 项。199 个空间的原有名称、类别、编号、边界、面积、层级与范围保留；本轮更新连接、入口和门洞。', md)
md = re.sub(r'\*\*门洞与连通状态：\*\*[^\n]*', f'**门洞与连通状态：**{opening_count} 个已定位门洞红点，对应 {located} 条人员可达关系；另有 {counts["access"]-located} 条人员可达关系未定位门洞。连续开放区域、半墙及整体交通核的概念连接不编造门位；已定位点均依据原图放大查看，非几何中心自动生成。L01—L05 尚未确认。', md)
md = md.replace('本轮仅同步名称和功能类别，保留空间编号、边界、面积、层级、范围及原有关系。', '本轮名称记录保留，连通关系已按下述复核结果更新。')
md = re.sub(r'\*\*状态：\*\*[^\n]*', '**状态：**55 项名称填写及其固定映射完整保留，名称待确认 0 项。连通复核结果见上方；L01—L05 待填写，不表示整图完成。', md)
review = [
    '## 本轮连通复核说明', '',
    '**已据图修正：**库房 S068 改接东侧南北公共通道；值班 S044 改接输液候诊区；卫生间 S028、S074 和交通核 S071 的连接改至实际开口侧；体液 S083 改接检验内部通道；南侧内科 S102 改接体检南侧候诊通道。一次候诊 S173 与大厅之间改记人员可达，服务窗口及共墙仍不等于通行。', '',
    '**急救组团：**污洗、处置接 EICU；治疗、器械接抢救组团内部。原来接东侧公共通道的关系已修正。组团与外部公共通道的主要入口留作 L03，未为了补齐网络而猜测建连。', '',
    '**布局推断（非用户已确认）：**S016／S017 按用户“同一摆药区”及图面轴线分界记连续可达；S070 收费区域东侧与 S072 大厅无实体分隔，服务关系另保留；S152／S155 经护士站旁连续缺口形成内部概念连接；S173 东侧通过未见实体分隔的地面接 S165；S104 早餐厅东南侧有边界缺口，概念接 S132，西侧 S106 连续墙边的旧关系已撤下。以上不编造精确门位。', '',
    '**本轮不细究的内部细节：**北侧厕所分格的内部路线；更衣／换鞋及过渡带的逐门构造；交通核内部的电梯、扶梯、楼梯及门前小过渡带；小器材间 S103、外缘狭通道 S075 等缺乏证据的细部连接。S199 沿用既有“前室”名称，但图中字样疑似“风”，未见人员开口，原通行关系撤下；功能纠正留待后续局部复核，不伪造可达。未记关系不作为“不相通”或训练负例。', '',
    '**入口复核：**消防控制室、备用用房、空调机房及南端楼梯的清晰外开门分别记独立外部入口；体检补记北侧、东侧入口。E05 移至门厅实际东侧双门处。外部端点不合并为共享室外节点。', '',
]
anchor = '## 名称确认记录（核对号 01—55）'
assert anchor in md
md = md.replace(anchor, '\n'.join(parts+review) + '\n' + anchor, 1)
rows = [line for line in backup_md.splitlines() if re.match(r'^\| \d{2}\s*\| S\d+', line)]
assert len(rows)==55 and all(line in md for line in rows)
(PLAN / '标注说明.md').write_text(md)
(WORK / '关键问题映射.json').write_text(json.dumps(questions, ensure_ascii=False, indent=2)+'\n')
print(f'已加入 {len(questions)} 项关键问题，原 55 项名称填写全部保留。')
