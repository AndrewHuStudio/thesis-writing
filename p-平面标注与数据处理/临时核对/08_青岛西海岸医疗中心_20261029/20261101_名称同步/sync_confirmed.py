import json,html,re,shutil,importlib.util
from pathlib import Path
from shapely.geometry import Polygon
from shapely.ops import unary_union
root=Path('p-平面标注与数据处理'); sample=root/'标注试样/08_青岛西海岸医疗中心'; work=root/'临时核对/08_青岛西海岸医疗中心_20261029/20261101_名称同步'
backup=work/'用户填写与同步前备份';backup.mkdir(exist_ok=True)
for name in ['标注说明.md','annotation.json','标注.svg']:
 if (backup/name).exists():
  assert (backup/name).read_bytes()==(sample/name).read_bytes(), '源文件有变，禁止覆盖备份或重跑'
 else: shutil.copy2(sample/name,backup/name)
typepath=Path('/Users/hushili/.codex/skills/outpatient-plan-annotation/references/space-types.json');shutil.copy2(typepath,backup/'space-types.json')
original=(sample/'标注说明.md').read_text(); rows={}
for line in original.splitlines():
 c=[html.unescape(v.strip()) for v in line.strip('|').split('|')]
 if len(c)==7 and c[0].isdigit():
  assert c[0]==c[-1];rows[int(c[0])]=c
assert len(rows)==210
jp=sample/'annotation.json';data=json.loads(jp.read_text());spaces={s['id']:s for s in data['spaces']}
# 原表的功能类别顺序；名称始终取用户填写，仅将说明性句子拆出。
bytype={
 'storage':[1,4,19,25,42,46,62,64,69,97,109,110,159,168,170,172,173,175,176,194,199,208],
 'building_services':[2,5,6,7,8,9,10,11,26,28,31,39,40,45,49,57,87,111,112,113,114,115,117,131,138,144,150,152,162,166,188,195,200,203],
 'office':[12,13,14,15,16,17,18,36,41,47,63,71,76,77,83,84,86,99,102,118,122,125,132,140,141,142,145,167,174,186,190,193],
 'staff_support':[143,19,37,53,62,64,92,93,97,98,101,109,123,151,168,169],
 'service':[20,21,55,70,82,133,157,158,163,171,177,178,179,180,181,185,187,202,209],
 'retail_service':[23], 'observation':[161,24,38,52,124,128,130],
 'corridor':[29], 'reserved_space':[3,30,34,35,119,210], 'building_control':[32,33],
 'imaging':[43,44,48,50,58,59,60,61,65,66,67,68,72,73,74,75,78,79,80,81,164],
 'treatment':[51,96,107,126,160,177,196,197,201,204,207],
 'education':[54,189], 'consultation':[88,89,90,91,105,106,147,148,182,183,184,191,192],
 'medication_preparation':[94], 'nurse_station':[95,127], 'pharmacy':[100],
 'examination':[103,134], 'rehabilitation':[104], 'registration':[108,205],
 'pharmacy_counter':[116], 'laboratory':[120,121], 'service_work_area':[129,147,148,165],
 'entrance':[135,206], 'operating_room':[155,198,146,149,153,156],
 'patient_preparation':[154],
}
# 显式覆盖重复列表的语义：介入控制室属于诊疗工作区；普通设备间属于建筑设备用房。
category={n:typ for typ,ns in bytype.items() for n in ns}
category.update({154:'service_work_area',155:'service_work_area',158:'staff_support',159:'service',160:'storage',19:'staff_support',62:'staff_support',64:'staff_support',97:'staff_support',109:'staff_support',168:'staff_support',177:'treatment'})
renames={12:'办公',2:'空调机房',3:'备用',5:'空调机房',6:'空调机房',9:'空调机房',7:'设备间',8:'设备间',10:'设备间',11:'设备间',19:'男更衣+女更衣',22:'室外绿化',27:'室外空间',29:'入口',55:'登记',56:'内庭上空',85:'室外庭院',139:'内庭院',169:'换鞋',188:'通风管道',205:'护士挂号',206:'门诊大厅进入急诊的门斗间',210:'备用'}
for n in range(13,19): renames[n]='办公'
excluded={136,137};merged={5:2,9:6};pending=set()
for n,c in rows.items():
 s=spaces[c[1]]
 if n in excluded or n in merged or n in pending: continue
 name=renames.get(n,c[5]);s['name']=name
 if n==22: s.update(type='landscape',level='landscape')
 elif n in {27,56,85,139}:s.update(type='courtyard',level='open_space')
 else:
  assert n in category, (n,name)
  s['type']=category[n]
  if n==3:s['level']='functional_block'
  if n==29:s['level']='open_space'
  if n in {55,205}:s['level']='semi_open_space'
  if n==188:s['level']='core_block'
  if n in {24,38}:s['scope']='pediatric'
remap={}
for old_n,new_n in merged.items():
 oldid=rows[old_n][1];newid=rows[new_n][1]
 union=unary_union([Polygon(spaces[newid]['polygon_px']),Polygon(spaces[oldid]['polygon_px'])])
 assert union.geom_type=='Polygon' and not union.interiors,(oldid,newid,union.geom_type)
 spaces[newid]['polygon_px']=[list(p) for p in list(union.exterior.coords)[:-1]]
 remap[oldid]=newid
# 169 的右侧窄条向下延伸；女更衣室与换鞋原属同一个错误卫生间轮廓，现按原图分开。
spaces['S259']['polygon_px']=[[660,2514],[686,2514],[686,2590],[660,2590]]
spaces['S265'].update(name='女更',type='staff_support',polygon_px=[[588,2548],[660,2548],[660,2590],[588,2590]])
removed={rows[n][1] for n in excluded}|set(remap)
data['spaces']=[s for s in data['spaces'] if s['id'] not in removed]
rels=[];seen={}
for r in data['relations']:
 if r['source'] in removed-set(remap) or r['target'] in removed-set(remap):continue
 r['source']=remap.get(r['source'],r['source']);r['target']=remap.get(r['target'],r['target'])
 if r['source']==r['target']:continue
 key=(r['id'],) if r['type']=='entrance' else tuple(sorted([str(r['source']),r['target']]))+(r['type'],)
 if key in seen:
  if r.get('openings'): seen[key].setdefault('openings',[]).extend(r['openings'])
 else:seen[key]=r;rels.append(r)
data['relations']=rels
# “备用”是用户确认的预留用途，不用 unknown 替代，也不猜测未来科别。
types=json.loads(typepath.read_text());types.setdefault('reserved_space','备用空间');typepath.write_text(json.dumps(types,ensure_ascii=False,indent=2)+'\n')
spec=importlib.util.spec_from_file_location('annotation_tools','/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts/annotation_tools.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
module.normalize(data);jp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
report={'rows':210,'retained_spaces':len(data['spaces']),'merge_ids':remap,'removed_duct_ids':sorted(removed-set(remap)),'pending_ids':[],'extra_corrected':'S265 女更；S259 换鞋长条向下延伸','non_indoor_ids':['S035','S045','S084','S132','S219']}
(work/'同步记录.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
