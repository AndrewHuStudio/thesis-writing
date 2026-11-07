"""Apply the current user's confirmed room names without renumbering."""
from pathlib import Path
import json,sys,copy,shutil,re
from shapely.geometry import Polygon
from shapely.ops import unary_union
OUT=Path(__file__).resolve().parent
BASE=OUT.parents[1]
PROJECT=BASE/'标注试样/16_浙江大学医学院邵逸夫医院下沙院区'
sys.path.insert(0,str(BASE/'临时核对/09-10_连通复核_20261102'))
from 连通工具 import annotation,fit_labels
BACKUP=Path((OUT/'本轮备份路径.txt').read_text())
a=json.loads((BACKUP/'annotation.json').read_text())
rows=json.loads((OUT/'用户填写快照.json').read_text())
spaces={s['id']:s for s in a['spaces']}
types={
'拍片':'imaging','B超':'imaging','控制、读片':'service_work_area','挂号收费':'registration',
'药库':'storage','应急诊室':'consultation','更衣':'staff_support','贵重药品':'storage',
'空调机房':'building_services','咖啡厅':'retail_service','购物中心':'retail_service',
'主任':'office','宣教':'education','心电':'examination','控制室':'service_work_area',
'弱电、强电':'building_services','前室':'vestibule','鲜花超市':'retail_service',
'设备用房':'building_services','医师办公室':'office','安全通道':'corridor',
'护工':'staff_support','门诊办公':'office','会议室':'conference','办公':'office',
'新风机房':'building_services','保健房':'consultation','库房':'storage','电梯前室':'vestibule',
'儿童输液室':'treatment','处置':'treatment','治疗':'treatment','药房':'pharmacy',
'值班':'staff_support','茶水间':'staff_support','复苏室':'resuscitation','检验':'laboratory',
'办公室':'office','弱电':'building_services','急诊手术专用电梯前室':'vestibule',
'护办':'office','医办':'office','VIP室':'observation'}
merges={'S038':'S037','S125':'S124'}
deletes={'S181','S182'}
changes=[]
for c in rows:
 num,sid,estimate,_,_,answer,_=c
 if sid in merges or sid in deletes:continue
 if '据照片识别' in answer:continue
 name=estimate if answer=='已确认' else answer
 assert name in types,(num,name)
 s=spaces[sid]
 changes.append(dict(number=num,id=sid,old_name=s['name'],name=name,type=types[name],answer=answer))
 s.update(name=name,type=types[name])
 if s['type']=='corridor':s['level']='open_space'
 if s['type']=='vestibule':s['level']='room'
for remove,keep in merges.items():
 poly=unary_union([Polygon(spaces[keep]['polygon_px']),Polygon(spaces[remove]['polygon_px'])])
 assert poly.geom_type=='Polygon' and not poly.interiors
 spaces[keep]['polygon_px']=[list(p) for p in list(poly.exterior.coords)[:-1]]
for r in a['relations']:
 for k in ['source','target']:
  r[k]=merges.get(r[k],r[k])
a['spaces']=[s for s in a['spaces'] if s['id'] not in set(merges)|deletes]
a['relations']=[r for r in a['relations'] if not {r['source'],r['target']}&deletes and r['source']!=r['target']]
assert len(a['spaces'])==206 and not any(s['type']=='unknown' for s in a['spaces'])
annotation.normalize(a)
stage=OUT/'待核验成果';stage.mkdir(exist_ok=True)
shutil.copy2(PROJECT/a['image']['file'],stage/a['image']['file'])
path=stage/'annotation.json';path.write_text(json.dumps(a,ensure_ascii=False,indent=2)+'\n')
annotation.render(a,path,stage/'标注.svg');fit_labels(stage/'标注.svg',a)
annotation.summary(a,OUT/'名称同步概览.md')
(OUT/'名称同步记录.json').write_text(json.dumps(dict(changes=changes,merges=merges,exclusions=sorted(deletes),spaces=206,unknown=0),ensure_ascii=False,indent=2))
print('named changes',len(changes),'spaces',len(a['spaces']),'unknown',sum(s['type']=='unknown' for s in a['spaces']))
