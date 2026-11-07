"""Apply six completed connectivity responses, preserving existing S/P identifiers."""
import base64
from collections import Counter
import hashlib
import html
import json
import os
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

WORK=Path(__file__).resolve().parent
PROJECT=next((WORK.parents[2]/'标注试样').glob('21_*'))
BACKUP=WORK/'同步前四文件与用户填写'
SKILL=Path('/Users/hushili/.codex/skills/outpatient-plan-annotation')
sys.path.insert(0,str(SKILL/'scripts'))
import annotation_tools as at

old_md=(BACKUP/'标注说明.md').read_text()
assert (PROJECT/'标注说明.md').read_text()==old_md,'Read latest user file before updating'
old_data=json.loads((BACKUP/'annotation.json').read_text())
assert json.loads((PROJECT/'annotation.json').read_text())==old_data
data=json.loads(json.dumps(old_data))
answers=json.loads((WORK/'读取确认.json').read_text())
assert answers['K01'].lower()=='s10进入'
assert answers['K02']=='S116进入'
assert 'S124' in answers['K03-A'] and 'S129' in answers['K03-B']
assert answers['K04-A']=='直接相通' and 'S151' in answers['K04-B']
rels=data['relations']
changes=[]


def connect(source,target,restore=None,basis='用户确认'):
    assert not any(r['type']=='access' and {r['source'],r['target']}=={source,target} for r in rels)
    if restore:
        assert not any(r['id']==restore for r in rels)
        rid=restore
    else:
        rid='R'+str(max(int(r['id'][1:]) for r in rels if r['id'].startswith('R'))+1).zfill(3)
    row=dict(id=rid,source=source,target=target,type='access')
    rels.append(row)
    changes.append(dict(relation=rid,source=source,target=target,basis=basis))
    return row


connect('S010','S012',basis='K01确认由抢救S010进入；准备间是与抢救相接的上游空间。')
connect('S012','S011',basis='布局推断：结合用户确认的S010入口及上下空间顺序，经准备间进入手术间；未定位门。')
connect('S116','S115',basis='K02确认由首长门厅S116进入。')
connect('S124','S123',basis='K03-A确认经过育发S124进入护发。')
connect('S129','S128',basis='K03-B确认经过激光S129进入纹眉。')
connect('S117','S151',restore='R067',basis='K04-A确认直接相通，恢复原R067为无定位概念关系；邻近卫生间门不误作通道门。')
connect('S151','S147',restore='R121',basis='K04-B明确写开向通道S151，按具体指向同步，保留原始用字；恢复原R121。')

# Confirmation establishes connectivity; no new door is located from these answers.
assert max(int(o['id'][1:]) for r in rels for o in r.get('openings',[]))==135
at.normalize(data)
assert data['spaces']==old_data['spaces'] and data['image']==old_data['image']
old_map={r['id']:r for r in old_data['relations']}
new_map={r['id']:r for r in rels}
assert all(new_map[key]==value for key,value in old_map.items())
old_points={o['id']:o for r in old_data['relations'] for o in r.get('openings',[])}
new_points={o['id']:o for r in rels for o in r.get('openings',[])}
assert all(new_points[key]==value for key,value in old_points.items())

# Preserve the filled document as a readable archive, repairing only its relative links.
def relocate(match):
    value=match[1]
    if value.startswith(('http:','https:','#')):
        return match[0]
    return os.path.relpath((PROJECT/value).resolve(),WORK)
archive=re.sub(r'(?<=\]\()([^)]+)(?=\))',relocate,old_md)
(WORK/'用户填写与图文归档.md').write_text(archive)
raw_answers=[line for line in old_md.splitlines() if '我的确认／备注：' in line]
name_rows=[line for line in old_md.splitlines() if re.match(r'^\|\s*\d+\s*\|\s*S\d+',line)]
assert len(raw_answers)==6 and len(name_rows)==19
assert all(line in archive for line in raw_answers+name_rows)
for image in re.findall(r'!\[[^\]]*\]\(([^)]+)\)',archive):
    assert (WORK/image).is_file(),image

jsonfile=PROJECT/'annotation.json'
jsonfile.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
at.render(data,jsonfile,PROJECT/'标注.svg')
tree=ET.parse(PROJECT/'标注.svg')
for group in tree.getroot().iter():
    if group.get('data-opening-id'):
        for label in group.findall('{'+at.NS+'}text'):
            label.set('font-size','9');label.set('stroke-width','0.7')
tree.write(PROJECT/'标注.svg',encoding='unicode')
at.summary(data,WORK/'最终概览.md')
overview=(WORK/'最终概览.md').read_text().replace('# 平面标注概览','# 21_海军总医院外科医疗大楼｜一层标注完成')
overview=overview.replace('空间名称已齐；结构与关系仍以原图及人工核对为依据。',
    '**状态：已按概念级精度完成。名称及属性待确认0项，关键连通待确认0项；19项房名与6处连通填写均已处理。**')
link=os.path.relpath(WORK/'用户填写与图文归档.md',PROJECT)
notes=[
    '**图面范围：**当前原图所示整层，包括急诊、住院大厅及公共服务、体检、整形、行政及首长专用服务空间；由scope区分。外围道路、绿化和尺寸线不纳入室内空间。大厅内树状家具／景观图案不据此视为露天中庭。',
    '**范围与编号：**保留既有房间S编号、用户原名和轮廓。连通复核时续编S155—S158，补齐急诊北侧后勤通道、中央西侧交通厅、体检西侧过道、整形北侧后勤通道，并补齐S068、S075、S112的连续通行范围。面积已统一归一化；本次确认未再更改范围。',
    '**本轮确认的连接：**首长门厅S116连首长电梯及前室S115；护发S123经育发S124进入；纹眉S128经激光S129进入；整形主通道S117与东侧通道S151直接相通，处理室S147直接连S151。本轮新增的7条已确认或有布局依据的连接均保留为无定位的概念关系；不把相邻卫生间门误作通道门。P001—P135位置、编号和所属关系均未改动。',
    '**手术区路径与推断：**K01用户确认从抢救S010进入。结合现有空间顺序，保存S010—S012手术准备间—S011手术的概念路径；其中S012—S011为布局推断，未标精确门位。护士站S039南侧入口接S025，以及主任S058、护士长S064经转角接会议S061，沿用有图面依据的概念连接。',
    '**交通核与开放区域：**交通核整体保存，内部前室、楼梯及电梯不展开全部内部路线。S076沿用整体范围，含图上导医台与楼梯前室外侧通行区；不把柜台隔线当作人员门。开放连续区域和半开放服务区可保留无定位access。',
    '**未展开的内部细节：**S015库房、S059值班、S111煤表间、S122更衣、S140开水的入口证据不足，未补无依据的access；S143保留窗口服务关系，不展开操作区内部入口。未记关系不表示不可达，也不作已确认负例。',
    '**精度与核验：**原图未修改。几何与面积、空间及关系编号、SVG可见名称、135个开口与红点对应和四文件目录均已核验；门位为原图像素上的近似位置。共墙、服务窗口与人员可达分别保存；入口不通过室外总节点互连。',
    f'**填写留存：**[查看原始房名与连通填写及局部图归档]({link})。保留原始填写用字，包括K04-B的“待接开向通道S151”；本轮按其明确指向S151处理。',
]
(PROJECT/'标注说明.md').write_text(overview.rstrip()+'\n\n'+'\n\n'.join(notes)+'\n')
report,code=at.check(data,jsonfile,check_dir=True)
assert code==0,report
source=PROJECT/data['image']['file']
assert source.read_bytes()==(BACKUP/source.name).read_bytes()
svg=tree.getroot()
embedded=svg.find('.//{'+at.NS+'}image').get('{'+at.XL+'}href')
assert base64.b64decode(embedded.split(',',1)[1])==source.read_bytes()
for node in data['spaces']:
    group=next(e for e in svg.iter() if e.get('id')==node['id'])
    visible=''.join(e.text or '' for e in group.iter() if e.tag=='{'+at.NS+'}text')
    assert node['name'] in visible,node['id']
report.update(openings=len(new_points),connectivity_pending=0,confirmed_fields=6,
              new_access=7,stable_old_openings=135,user_name_rows_archived=19,
              source_unchanged=True,relations_by_type=dict(Counter(r['type'] for r in rels)))
(WORK/'最终核验.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
(WORK/'本轮连接依据.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2))
