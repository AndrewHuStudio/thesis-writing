from pathlib import Path
from collections import Counter
import importlib.util
import json
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SAMPLE = ROOT / 'p-平面标注与数据处理/标注试样/17_成都市西区医院'
SKILL = Path('/Users/hushili/.codex/skills/outpatient-plan-annotation')
spec = importlib.util.spec_from_file_location('annotation_tools', SKILL / 'scripts/annotation_tools.py')
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)
data = json.loads((SAMPLE / 'annotation.json').read_text())
corrections = {'P019': [1203, 1090], 'P024': [1023, 1169],
               'P033': [1228, 1719], 'P034': [1206, 1914]}
for r in data['relations']:
    for o in r.get('openings', []):
        if o['id'] in corrections:
            o['position_px'] = corrections[o['id']]
(SAMPLE / 'annotation.json').write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
evidence = json.loads((OUT / '开口与连通判读依据.json').read_text())
for item in evidence:
    if item.get('opening') in corrections:
        item['position_px'] = corrections[item['opening']]
(OUT / '开口与连通判读依据.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2)+'\n')
api.render(data, SAMPLE / 'annotation.json', SAMPLE / '标注.svg')
api.summary(data, OUT / '正式概览_供合并.md')

# A backing rectangle keeps P identifiers legible in renderers that do not
# implement SVG paint-order; all point coordinates and relation data stay intact.
NS = 'http://www.w3.org/2000/svg'
svg = ET.parse(SAMPLE / '标注.svg')
for group in svg.getroot().iter(f'{{{NS}}}g'):
    if 'data-opening-id' not in group.attrib:
        continue
    label = group.find(f'{{{NS}}}text')
    circle = group.find(f'{{{NS}}}circle')
    x, y = float(circle.get('cx')), float(circle.get('cy'))
    offsets = {'P007': (6, 20), 'P011': (-36, -7), 'P014': (6, 20), 'P020': (6, 20),
               'P026': (-36, 14), 'P027': (6, 24), 'P031': (-36, -7)}
    dx, dy = offsets.get(group.get('data-opening-id'), (6, -7))
    label.set('x', str(x+dx))
    label.set('y', str(y+dy))
    label.set('font-size', '10')
    label.set('fill', '#991b1b')
    for attr in ['stroke', 'stroke-width', 'paint-order']:
        label.attrib.pop(attr, None)
    backing = ET.Element(f'{{{NS}}}rect', {
        'x': str(x+dx-2), 'y': str(y+dy-10), 'width': '30', 'height': '13',
        'rx': '1', 'fill': 'white', 'fill-opacity': '.96'})
    group.insert(list(group).index(label), backing)
svg.write(SAMPLE / '标注.svg', encoding='unicode')

prefix = '../../临时核对/17_成都市西区医院_确认与连通复核_20261103/'
summary = (OUT / '正式概览_供合并.md').read_text()
summary = summary.replace('# 平面标注概览', '# 17_成都市西区医院｜首层概念标注')
summary = summary.replace('空间名称已齐；结构与关系仍以原图及人工核对为依据。',
                          '房间名称、类别、目标范围及主要连通复核已落实；本图按现有概念精度完成，关键待确认项0。')
summary += '''
**图纸范围：**仅含原图左侧完整首层主体：门诊公共服务、急诊、影像、住院手续及建筑支持。右侧截断七层平面、北侧斜线屋盖、室外台阶和雨棚不计入；不代表七层或整院完成。

**范围与编号：**保留S001—S049及01—06固定核对映射。按用户填写保留S001“管井”为建筑设备用房，不作为日常人员通行节点；未擅自删除、合并或排除其范围。护士站S028南端依半墙终点收至y约1310，南侧通往抢救室的无墙通行带归入急诊门厅S030，其余空间轮廓不变；室内相对面积已重新归一化。

**用户名称确认：**下表按最新“我的确认／备注”实际填写同步，原名不扩写；S013沿用前轮辨读“值班”，本轮用户说明“所有标注已完成”后保留。含候选、依据和原始填写的整份MD已原样保存于[本轮确认原文](用户确认原文路径)。

| 固定核对号 | S编号 | 最终名称 | 标准类别 | 原我的确认／备注 |
| --- | --- | --- | --- | --- |
| 01 | S001 | 管井 | 建筑设备用房 | 管井 |
| 02 | S004 | 汇流排间 | 建筑设备用房 | 汇流排间 |
| 03 | S012 | 值班 | 工作人员支持用房 | 值班 |
| 04 | S013 | 值班 | 工作人员支持用房 | 助手据原图已同步（非用户确认；原栏为“待确认”） |
| 05 | S018 | 清创室 | 处置治疗 | 清创室 |
| 06 | S021 | 内科 | 诊室 | 内科 |

**主要通行组织：**门诊入口E004进入S049，经S048、S046到电梯组及中部交通核；西侧S038、北侧S039及后勤S033贯通影像和急诊公共空间。急诊入口E002接S034、S030，住院入口E003接S036及电梯厅。48个具有日常人员可达意义的节点均能由已记录入口经access到达；S001管井不要求人员连通。关系不表达患者或医护门禁权限。

**连通修正：**保留既有关系编号，移除R052（中部电梯组S045南侧为实墙及座椅，不能直接进入S048）；通过S046绕行至S048。新增R088（S044门诊药房西南人员门到S049），并补入导诊、问讯及西侧扶梯的概念接口R089—R091。药房、挂号收费、检验和住院手续的人员门与服务窗口分别记录；影像控制侧窗、共墙不作为人员门。

**布局推断与未定位连接：**16条access未附门位。其中S028—S030、S035—S036、S047—S049为半墙服务区的布局推断；S038—S041、S041—S049按整体扶梯及到达区衔接推断。其余为大厅、走廊之间可见连续布局，S046—S048沿电梯组两端绕行，不穿越电梯井。概念分区线不虚构成门洞；逐条依据保存在[本轮判读记录](判读记录路径)。

**本轮不细究的内部细节：**卫生间组团内部、小型设备与管井检修、交通核内部精确路线和服务台小门不细分。汇流排间外侧检修门不增加为主要公共入口；该房间南侧的清晰人员门已定位。未记录的内部关系不视为不可达，也不记作用户已确认的负例。

**确认状态：**名称待确认0、范围关键待确认0、主要连通关键待确认0。SVG实际显示49个空间名称和类别、47个P红点及5个E入口；开口位置和两端空间均对应JSON。

[查看原图](17_成都市西区医院_原图.jpg)｜[查看最终标注](标注.svg)｜[查看本轮备份及复核图](本轮目录路径)
'''
summary = summary.replace('用户确认原文路径', prefix+'用户确认原文.md')
summary = summary.replace('判读记录路径', prefix+'开口与连通判读依据.json')
summary = summary.replace('本轮目录路径', prefix.rstrip('/'))
(SAMPLE / '标注说明.md').write_text(summary)
print('名称确认、最终概览、开口编号可读样式已同步；待最终核验与目检。')
