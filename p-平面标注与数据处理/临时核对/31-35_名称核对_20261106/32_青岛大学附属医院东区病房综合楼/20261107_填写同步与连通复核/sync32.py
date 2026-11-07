from pathlib import Path
import json,re,shutil,sys
from shapely.geometry import Polygon
from shapely.ops import unary_union
BASE=Path('/Users/hushili/Documents/研究-论文写作/大论文/p-平面标注与数据处理')
P=BASE/'标注试样/32_青岛大学附属医院东区病房综合楼'
R=BASE/'临时核对/31-35_名称核对_20261106/32_青岛大学附属医院东区病房综合楼'
W=R/'20261107_填写同步与连通复核'
backup=W/'同步前备份'; backup.mkdir(exist_ok=False)
for f in P.iterdir():shutil.copy2(f,backup/f.name)
for name in ['review_state.json','固定核对映射.json']:shutil.copy2(R/name,backup/name)
d=json.loads((P/'annotation.json').read_text());state=json.loads((R/'review_state.json').read_text())
rows=[]
for line in (P/'标注说明.md').read_text().splitlines():
 c=[x.strip() for x in line.strip().strip('|').split('|')]
 if len(c)==7 and re.fullmatch(r'S\d+',c[1]):
  assert c[0]==c[-1]
  rows.append(dict(review_id=c[0],space_id=c[1],candidate=c[2],answer=c[5],raw=line))
assert len(rows)==115
names={
 '挂号收费':'registration','机房':'building_services','更衣':'staff_support','中庭':'courtyard',
 '洗刷':'sterile_supply','护士站':'nurse_station','诊疗室':'treatment','配药':'medication_preparation',
 '卫生间':'toilet','值班':'staff_support','乳腺钼靶':'imaging','数字胃肠':'imaging','MIR':'imaging',
 '存档':'storage','设备':'building_services','准备':'patient_preparation','办公':'office',
 '药房':'pharmacy','无障碍卫生间':'toilet','消防控制室':'building_control','主任办公':'office',
 'DR':'imaging','会议室':'conference','医生办公':'office','CT':'imaging','预留':'reserved_space',
 '露天中庭':'courtyard','注射':'treatment','财务':'office','会诊室':'consultation','主任办公室':'office',
 '诊室':'consultation'}
spaces={s['id']:s for s in d['spaces']};items={i['review_id']:i for i in state['name_items']}
for row in rows:
 rid=row['review_id']; answer=row['answer']
 if rid in {'20','21','22','52','53','54'} or answer in {'待确认','待填写','待定',''}:continue
 name=row['candidate'] if answer=='已确认' else answer
 s=spaces[row['space_id']];s['name']=name;s['type']=names[name]
 s['level']='open_space' if s['type']=='courtyard' else 'semi_open_space' if s['type'] in {'registration','nurse_station'} else 'functional_block' if s['type']=='pharmacy' else 'room'
 s['scope']='public_service' if s['type'] in {'courtyard','registration','toilet','building_control','building_services','pharmacy'} else 'ordinary_outpatient'
 if s['type']=='courtyard':s.pop('area_ratio',None)
 items[rid].update(status='confirmed',answer=answer,confirmed_name=name,applied=True,source='标注说明.md 我的确认／备注 2026-11-07')
# 三个稳定核对号的合并指令：S084存活，S085/S086退役，历史映射保留于外部。
union=unary_union([Polygon(spaces[sid]['polygon_px']) for sid in ['S084','S085','S086']]);assert union.geom_type=='Polygon'
spaces['S084'].update(name='电梯',type='vertical_core',level='core_block',scope='public_service',polygon_px=[list(q) for q in list(union.exterior.coords)[:-1]])
d['spaces']=[s for s in d['spaces'] if s['id'] not in {'S085','S086'}]
assert all(r['source'] not in {'S085','S086'} and r['target'] not in {'S085','S086'} for r in d['relations'])
state.setdefault('retired_name_items',[])
for rid in ['53','54']:
 item=items[rid].copy();item.update(answer='52-53-54合并成电梯',status='merged',merged_into='S084',merged_review_id='52');state['retired_name_items'].append(item)
state['name_items']=[i for i in state['name_items'] if i['review_id'] not in {'53','54'}]
items['52'].update(status='confirmed',answer='52-53-54合并成电梯',confirmed_name='电梯',applied=True,merged_from=['S084','S085','S086'])
state.setdefault('merges',[]).append({'retained':'S084','retired':['S085','S086'],'review_ids':['52','53','54'],'answer':'52-53-54合并成电梯','date':'2026-11-07'})
state['checks']={'connectivity_reviewed':False,'visual_reviewed':False}
(W/'用户填写读取.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
(P/'annotation.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
(R/'review_state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
print('已同步108项名称确认及3行合并指令；空间172个；20/21/22等待澄清，33保留未确认。')
