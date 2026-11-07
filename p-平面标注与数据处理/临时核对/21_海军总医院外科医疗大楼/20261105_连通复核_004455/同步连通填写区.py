"""Publish reviewed 21 relations and retain every user-entered room-name row."""
import base64
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

WORK=Path(__file__).resolve().parent
PROJECT=next((WORK.parents[2]/'标注试样').glob('21_*'))
SKILL=Path('/Users/hushili/.codex/skills/outpatient-plan-annotation')
sys.path.insert(0,str(SKILL/'scripts'))
import annotation_tools as at

data=json.loads((WORK/'连通复核候选.json').read_text())
backup=WORK/'复核前四文件与用户填写'
old_data=json.loads((backup/'annotation.json').read_text())
old_md=(backup/'标注说明.md').read_text()
current_md=(PROJECT/'标注说明.md').read_text()
assert current_md==old_md,'User edited Markdown during review; read latest before writing'
assert json.loads((PROJECT/'annotation.json').read_text())==old_data
assert all(s['id']==data['spaces'][i]['id'] for i,s in enumerate(old_data['spaces']))
assert all(s['name']==data['spaces'][i]['name'] and s['type']==data['spaces'][i]['type']
           for i,s in enumerate(old_data['spaces']))
assert data['image']==old_data['image']
source=PROJECT/data['image']['file']
assert source.read_bytes()==(backup/source.name).read_bytes()
questions=json.loads((WORK/'关键连通疑点.json').read_text())
assert len(questions)==6 and len({q['key'] for q in questions})==6
openings=[o for r in data['relations'] for o in r.get('openings',[])]
access=[r for r in data['relations'] if r['type']=='access']
located=sum(bool(r.get('openings')) for r in access)
distance=json.loads((WORK/'门位距离审计.json').read_text())
assert len(openings)==135 and all(max(p['source_distance'],p['target_distance'])<=18 for p in distance)
jsonfile=PROJECT/'annotation.json'
jsonfile.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
at.render(data,jsonfile,PROJECT/'标注.svg')
styled=ET.parse(PROJECT/'标注.svg')
for group in styled.getroot().iter():
    if group.get('data-opening-id'):
        for label in group.findall('{'+at.NS+'}text'):
            label.set('font-size','9')
            label.set('stroke-width','0.7')
styled.write(PROJECT/'标注.svg',encoding='unicode')
at.summary(data,WORK/'本轮概览.md')
summary=(WORK/'本轮概览.md').read_text().replace('# 平面标注概览','# 21_海军总医院外科医疗大楼｜连通复核')
summary=summary.replace('空间名称已齐；结构与关系仍以原图及人工核对为依据。',
    '**房名已齐；连通复核进行中，尚有4组、6处关键判断待填写。整图暂未完成。**')
def rel(file):
    return os.path.relpath(file,PROJECT)
section=[
    '## 连通性确认（2026-11-05）','',
    '原有房间S编号、已确认名称及19行用户填写保持不变。图中红点P仅表示已辨认并定位的门洞／无门开口；没有红点的概念连接不等于不相通。',
    '',f'本轮保存{len(access)}条人员可达关系，其中{located}条带定位点、{len(access)-located}条保留为无定位的概念连接；共{len(openings)}个开口。服务联系7条、共墙15条、建筑入口6条分别记录。',
    '', '**范围补齐：**原稿漏画了部分连续交通区域，本轮续编S155急诊北侧后勤通道、S156中央西侧交通厅、S157体检西侧过道、S158整形北侧后勤通道；补齐S068门厅西端、S075东侧开放通行带、S112通道西端。已重新归一化相对面积；其余既有房间轮廓不变。',
    '', '**已自主修正的主要路径：**骨科S034北门接急诊大厅S014，向中部通道的路径经外科S033；第五间观察室S005接办公前通道S057；点痣S131和激光S130的可见西门接皮护S125；医办S141接整形主通道S117。体检候诊廊与内部通道之间按S083—S157—S084分步记录。窗口和共墙未替代人员通行。',
    '', '**概念连接与布局推断：**大厅、候诊区与通道间的连续开放边界、半开放柜台的可达边界不编造门位。护士站S039南侧工作入口接S025为布局推断；主任S058、护士长S064与会议S061保留其转角入口的概念联系，不强行定位。交通核整体记录，内部前室、楼梯及电梯不展开内部路线。',
    '', '**S076范围说明：**沿用原稿整体节点；其范围含图上导医台及楼梯前室外侧通行区。本轮仅定位真实外边界上的门，不把柜台隔线当作人员门，也不将该块内部的每处家具分隔另建节点。',
    '', '**本轮不细究的内部细节：**S015库房、S059值班、S111煤表间、S122更衣、S140开水的入口证据不足；S143咨询已保留窗口服务关系，操作区内部入口不展开。本轮未补其不清楚的access，不表示不可达，也不作为已确认负例。',
    '',f'![21号门洞定位总图，红点与JSON开口对应]({rel(WORK/"门洞原图定位总图.png")})',
    '', '### 需要填写的关键判断','',
    '以下4组共6处填写栏。图片内直接标有01、02、03A、03B、04A、04B及对应S编号。只需确认直接相连的空间或通行顺序，无须指定精确门位；可分批填写。',
]
for q in questions:
    section+=['',f'### {q["key"]}｜{q["title"]}','',
              f'![{q["key"]}：房内编号与相关空间]({rel(WORK/q["image"])})','',
              f'[查看同范围无标记原图]({rel(WORK/(q["key"]+"_无标记原图.png"))})','',
              '**问题：**'+q['question'],'','**我的判断：**'+q['judgment'],'',
              '**我的确认／备注：**'+q['answer']]
section+=['','**核验边界：**正式结构校验通过不等于上述6处已经确认；收到填写后再同步关系及红点，保留本轮P编号。','']
room_history=old_md[old_md.index('## 房名与范围核对（2026-11-05）'):]
md=summary.rstrip()+'\n\n'+'\n'.join(section)+'\n'+room_history
raw_rows=[line for line in old_md.splitlines() if re.match(r'^\|\s*\d+\s*\|\s*S\d+',line)]
assert len(raw_rows)==19 and all(line in md for line in raw_rows)
(PROJECT/'标注说明.md').write_text(md)
report,code=at.check(data,jsonfile,check_dir=True)
assert code==0,report
svg=ET.parse(PROJECT/'标注.svg').getroot()
for s in data['spaces']:
    group=next(e for e in svg.iter() if e.get('id')==s['id'])
    text=''.join(e.text or '' for e in group.iter() if e.tag=='{'+at.NS+'}text')
    assert s['name'] in text,s['id']
embedded=svg.find('.//{'+at.NS+'}image').get('{'+at.XL+'}href')
assert base64.b64decode(embedded.split(',',1)[1])==source.read_bytes()
for image in re.findall(r'!\[[^\]]*\]\(([^)]+)\)',md):
    assert (PROJECT/image).is_file(),image
assert source.read_bytes()==(backup/source.name).read_bytes()
report.update(dict(openings=len(openings),located_access=located,concept_access=len(access)-located,
                   connectivity_pending=[q['key'] for q in questions],user_name_rows_preserved=19,
                   source_unchanged=True,geometry_max_opening_distance=max(max(x['source_distance'],x['target_distance']) for x in distance)))
(WORK/'正式校验与本轮状态.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
(WORK/'无定位概念连接.json').write_text(json.dumps([r for r in access if not r.get('openings')],ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2))
