from pathlib import Path
import json, importlib.util, re, hashlib
import xml.etree.ElementTree as ET
from collections import Counter

W=Path(__file__).parent
ROOT=W.parents[2]
P=ROOT/'标注试样/26_济南军区总医院门诊综合楼'
SKILL=Path('/Users/hushili/.codex/skills/outpatient-plan-annotation')
spec=importlib.util.spec_from_file_location('annotation_tools',SKILL/'scripts/annotation_tools.py')
at=importlib.util.module_from_spec(spec);spec.loader.exec_module(at)
before=json.loads((W/'补充前四文件/annotation.json').read_text())
d=json.loads(json.dumps(before))
ss={s['id']:s for s in d['spaces']}
# Names are read from this hospital's supplemental photographs.
names={
 1:('办公休息室','staff_support',4),
 4:('新风机房','building_services',4),
 6:('药品库','storage',3),
 8:('值班／更衣室','staff_support',4),
 9:('药库','storage',3),
 10:('贵重药品','storage',3),
 11:('中药房','pharmacy',3),
 12:('急诊药房','pharmacy',3),
 13:('西药房','pharmacy',3),
 14:('办公室','office',3),
 15:('炮制间','medication_preparation',1),
 16:('医保主任办公室','office',1),
 23:('医保办','registration',1),
 25:('结算业务','registration',1),
 27:('值班室','staff_support',1),
 29:('病历审核','office',1),
 48:('污洗间','waste_handling',2),
 49:('洁物间','storage',2),
 50:('隔离','isolation',2),
 51:('缓冲','vestibule',2),
 56:('保洁间／污物暂存','waste_handling',2),
 58:('急诊接待','hall',6),
 61:('准备／洗手','staff_support',5),
 62:('清创室','treatment',5),
 64:('洗胃','treatment',5),
 65:('移动X光拍摄','imaging',5),
 67:('器材室','equipment_room',6),
 68:('诊室','consultation',2),
 69:('诊室','consultation',2),
 72:('EICU（9床）','ward',2),
 74:('EICU床位区','ward',2),
 75:('治疗','treatment',5),
 79:('缓冲','vestibule',5),
 81:('更衣室','staff_support',5),
 82:('卫生间','toilet',2),
 84:('污洗','waste_handling',5),
 85:('化验','laboratory',5),
 86:('观察','observation',5),
 87:('观察','observation',5),
 88:('隔离','isolation',5),
 90:('治疗','treatment',5),
 91:('诊室','consultation',5),
 92:('挂号收费','registration',5),
 98:('污洗','waste_handling',5),
 108:('更衣室','staff_support',2),
 110:('护士站','nurse_station',2),
 112:('发热门诊门厅','hall',2),
}
for n,(name,typ,photo) in names.items():
    s=ss[f'S{n:03}'];s['name']=name;s['type']=typ
    if n in [1,4,6,8,9,10,11,12,13,14,15]:s['scope']='pharmacy_support'
    if n in [16,23,25,27,29]:s['scope']='public_service'
    if n in [48,49,50,51,58,61,62,64,65,67,68,69,72,74,75,79,81,82]:s['scope']='emergency'
    if n in [84,85,86,87,88,90,91,92,108,110,112]:s['scope']='fever_outpatient'

# The former S006 spans a real dividing wall in the new photograph.
ss['S006']['polygon_px']=[[980,368],[1284,368],[1284,520],[980,520]]
s114=dict(id='S114',name='中药煎药室',type='medication_preparation',level='room',scope='pharmacy_support',polygon_px=[[1292,368],[1368,368],[1368,520],[1292,520]])
s115=dict(id='S115',name='处置',type='treatment',level='room',scope='emergency',polygon_px=[[1410,2219],[1461,2219],[1461,2273],[1410,2273]])
d['spaces'] += [s114,s115]
ss.update({s['id']:s for s in [s114,s115]})
# No fixture or room name supports the old toilet label on this tiny core space.
ss['S109']['name']='名称未确认';ss['S109']['type']='unknown'
ss['S078']['name']='医生办公';ss['S078']['type']='office';ss['S078']['scope']='emergency'
ss['S089']['name']='发热门诊内部通道';ss['S089']['scope']='fever_outpatient'
for n in [59,60,63,66,70,71,73,76,77,78,80,83]:ss[f'S{n:03}']['scope']='emergency'
for n in [55,56]:ss[f'S{n:03}']['scope']='hospital_support'

rels={r['id']:r for r in d['relations']}
rel=rels['R005'];moved=[o for o in rel['openings'] if o['position_px'][0]>1290]
assert len(moved)==1
rel['openings']=[o for o in rel['openings'] if o not in moved]
d['relations'].append(dict(id='R158',source='S114',target='S007',type='access',openings=moved))
d['relations'].append(dict(id='R159',source='S115',target='S076',type='access',openings=[dict(id='P110',kind='door',position_px=[1465,2235])]))
# P049 was floating in an open piece of the EICU; R065 remains as conceptual continuity.
removed=[]
for r in d['relations']:
    if r['id']=='R065':removed.extend(r.pop('openings',[]))
# A solid divider separates the two changing rooms; a diagonal line is not evidence of a toilet.
withdraw={'R148','R153'}
removed_relations=[r for r in d['relations'] if r['id'] in withdraw]
d['relations']=[r for r in d['relations'] if r['id'] not in withdraw]
rels['E007']['name']='发热门诊入口'
at.normalize(d)
(P/'annotation.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
at.render(d,P/'annotation.json',P/'标注.svg')
tree=ET.parse(P/'标注.svg')
for node in tree.iter():
    if node.tag.endswith('text') and node.text and re.fullmatch(r'P\d{3,}',node.text):node.set('stroke-width','0.65')
tree.write(P/'标注.svg',encoding='utf-8',xml_declaration=True)
counts=Counter(r['type'] for r in d['relations'])
pending=at.unresolved(d)
openings=[o for r in d['relations'] for o in r.get('openings',[])]
located=sum(bool(r.get('openings')) for r in d['relations'])
overview='# 平面标注概览\n\n'
overview+=f'未完成：{len(pending)}个空间名称及K01连通问题仍待确认。\n\n'
overview+=f'**标注规模：**{len(d["spaces"])}个空间／区域。\n\n'
overview+=f'**连接关系：**{len(d["relations"])}条；人员可达{counts["access"]}条、服务联系{counts["service"]}条、共墙{counts["shared_wall"]}条、入口{counts["entrance"]}条。\n\n'
overview+=f'**门洞与开口：**{len(openings)}个红点，对应{located}条人员可达关系；其余{counts["access"]-located}条为无定位红点的概念连接。\n\n'
overview+='**相对规模：**室内非重叠区域的area_ratio合计为1；不保存平方米面积或施工门构造。\n\n'
overview+='**名称待确认：**'+'、'.join(s['id'] for s in pending)+'。\n'
(W/'补图后概览.md').write_text(overview)
changes=[dict(id=s['id'],before=next((o for o in before['spaces'] if o['id']==s['id']),None),after=s) for s in d['spaces'] if not any(s==o for o in before['spaces'])]
report=dict(names_read_from_photos={f'S{n:03}':dict(name=v[0],type=v[1],photo=v[2]) for n,v in names.items()},space_changes=changes,added_space_ids=['S114','S115'],retired_openings=removed,withdrawn_relations=removed_relations,moved_openings=moved,source_sha256=hashlib.sha256((P/d['image']['file']).read_bytes()).hexdigest())
(W/'补图变更记录.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
result,code=at.check(d,P/'annotation.json',check_dir=True)
print(json.dumps(result,ensure_ascii=False,indent=2));print('formal_exit_code',code)
