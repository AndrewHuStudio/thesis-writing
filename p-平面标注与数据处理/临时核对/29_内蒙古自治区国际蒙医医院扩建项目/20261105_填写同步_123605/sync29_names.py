from pathlib import Path
import json,html,re,hashlib
from shapely.geometry import Polygon,box
from shapely.ops import unary_union,transform
base=Path('/Users/hushili/Documents/研究-论文写作/大论文/p-平面标注与数据处理');root=base/'标注试样/29_内蒙古自治区国际蒙医医院扩建项目';w=base/'临时核对/29_内蒙古自治区国际蒙医医院扩建项目';run=Path((w/'当前续作目录.txt').read_text().strip());d=json.loads((run/'修改前备份/annotation.json').read_text());rows=json.loads((run/'用户填写原文.json').read_text());by={s['id']:s for s in d['spaces']}
corrections={'46':'设备间','62':'挂号收款','86':'外科','76':'中庭','77':'中庭'}
merge_answers={'38':'VIP用房','65':'鲜花超市','66':'鲜花超市','67':'鲜花超市','68':'鲜花超市','69':'中庭','70':'门诊主入口大厅','71':'门诊主入口大厅','72':'中庭','73':'中庭','74':'中庭','76':'中庭','77':'中庭','79':'急诊手术','84':'急诊手术','85':'急诊手术'}
bytype={
'consultation':['S001','S002','S165','S187','S141','S152','S162','S173','S180','S181'],
'registration':['S011','S005','S043','S053','S098','S143','S163','S209'],
'pharmacy':['S003','S006','S013','S183'],
'office':['S024','S032','S075','S078','S081','S082','S085','S088','S091','S182','S190','S155','S164','S195','S211','S212'],
'toilet':['S018','S019','S188','S189','S133','S134'],
'retail_service':['S021','S102','S103','S104','S109'],
'building_control':['S022','S214'],
'auxiliary_room':['S028','S034','S035','S040','S046','S047','S048'],
'imaging':['S030','S037','S041','S042','S059','S060','S061','S079','S080','S148','S193'],
'examination':['S049','S050','S051','S058','S062','S063','S064','S067','S068','S076','S083','S036'],
'hall':['S033','S065','S077','S092','S093','S111','S112','S136','S159','S185','S204'],
'patient_preparation':['S069'],
'equipment_room':['S071','S072','S073'],
'service_work_area':['S086','S087','S194'],
'storage':['S096','S206'],
'pharmacy_counter':['S105'],
'courtyard':['S113','S114','S116','S117','S121','S122','S179'],
'nurse_station':['S125'],
'operating_room':['S149','S150','S156'],
'treatment':['S146','S166','S169','S171','S199','S196'],
'laboratory':['S147','S139'],
'medication_preparation':['S168','S198'],
'resuscitation':['S175','S177'],
'observation':['S130','S132','S138','S151','S158','S178'],
'staff_support':['S140','S142','S191','S192'],
'service':['S202']}
types={sid:t for t,ids in bytype.items() for sid in ids};assert len(types)==136
for row in rows:
 sid=row['space_id'];name=corrections.get(row['review_id'],merge_answers.get(row['review_id'],row['answer']));s=by[sid];s['name']=name;s['type']=types[sid]
 if s['type']=='courtyard':s['level']='open_space';s.pop('area_ratio',None)
 elif s['type']=='hall':s['level']='open_space'
 elif sid in ['S011','S005','S105','S125']:s['level']='semi_open_space'
 elif sid=='S196':s['level']='functional_block'
 if sid in ['S001','S002','S049','S050','S051','S058','S062','S063','S064','S067','S068','S076','S083']:s['scope']='ordinary_outpatient'
 elif sid in ['S102','S103','S104','S109','S021','S022','S024','S032','S033','S043','S111','S112','S113','S114','S116','S117','S121','S122','S202','S209','S211','S212','S214']:s['scope']='public_service'
 elif sid in ['S125','S196','S198','S199','S204']:s['scope']='emergency'
 elif int(sid[1:])>=130 and int(sid[1:])<=195:s['scope']='emergency'
 else:s['scope']='medical_support'
# Geometry in reading orientation, converted back to the unchanged source pixels.
def original(p):return transform(lambda x,y,z=None:(2444-y,x),p)
def merge(survivor,ids,name,typ,reading_box=None):
 polys=[Polygon(by[s]['polygon_px']) for s in ids]
 if reading_box is None:
  geom=unary_union(polys)
  if geom.geom_type!='Polygon' or geom.interiors:geom=geom.buffer(.12,join_style=2).buffer(-.12,join_style=2)
 else:geom=original(box(*reading_box))
 assert geom.geom_type=='Polygon' and not geom.interiors,(survivor,geom.geom_type)
 s=by[survivor];s.update(name=name,type=typ,polygon_px=[[round(x,2),round(y,2)] for x,y in list(geom.exterior.coords)[:-1]])
 if typ in ['hall','courtyard']:s['level']='open_space'
 else:s['level']='functional_block'
 for sid in ids:
  if sid!=survivor:aliases[sid]=survivor
 merge_log.append({'survivor':survivor,'members':ids,'name':name,'previous_union_area':sum(p.area for p in polys),'result_area':geom.area})
aliases={};merge_log=[]
merge('S067',['S067','S083'],'VIP用房','examination',(1237,1709,1398,1774))
merge('S102',['S102','S103','S104','S109'],'鲜花超市','retail_service',(1582,765,1750,984))
# Fill only the one-pixel seams of the deliberately adjacent draft pieces.
geom=original(Polygon([(1582,765),(1669,765),(1669,842),(1750,842),(1750,984),(1582,984)]));by['S102']['polygon_px']=[[round(x,2),round(y,2)] for x,y in list(geom.exterior.coords)[:-1]]
merge('S113',['S113','S114'],'中庭','courtyard',(1735,1336,1853,1475))
merge('S116',['S116','S117'],'中庭','courtyard',(1734,1048,1853,1227))
merge('S121',['S121','S122'],'中庭','courtyard',(1750,568,2004,659))
merge('S150',['S149','S150','S156'],'急诊手术','operating_room',(2036,1442,2112,1575))
merge('S111',['S100','S101','S106','S107','S111','S112','S123','S124','S127','S128'],'门诊主入口大厅','hall')
d['spaces']=[s for s in d['spaces'] if s['id'] not in aliases]
# Remap facts to surviving nodes, preserving relation IDs where a relation remains.
rels=[];seen={};retired=[]
for r in d['relations']:
 for k in ['source','target']:
  if r[k] in aliases:r[k]=aliases[r[k]]
 if r['source']==r['target']:retired.append(r);continue
 key=(r['type'],tuple(sorted([r['source'],r['target']]))) if r['type']!='entrance' else ('entrance',r['id'])
 if key in seen:retired.append(r);continue
 seen[key]=r;rels.append(r)
d['relations']=rels
nextid=max(int(r['id'][1:]) for r in rels if r['id'].startswith('R'))+1
d['relations'].append({'id':f'R{nextid:03d}','source':'S017','target':'S052','type':'access'})
# Import the exact fixed mapping. Retired rows retain original numbers and wording in a separate history.
state={'image_signature':dict(d['image'],sha256=hashlib.sha256((root/d['image']['file']).read_bytes()).hexdigest()),'name_items':[],'retired_name_items':[],'connectivity_items':[{'review_id':'K01','source':'S017','target':'S052','status':'confirmed_connected','answer':'直接相通','basis':'本轮标注说明填写'}],'checks':{'connectivity_reviewed':False,'visual_reviewed':False},'space_aliases':aliases,'merge_history':merge_log,'followup_answers':{'text_corrections':'按上述文字修正','round_entrance':'整个圆形区域合为主入口大厅'}}
state['image_signature']['file']=state['image_signature'].pop('file')
for row in rows:
 sid=row['space_id'];target=aliases.get(sid,sid);item=dict(row,status='confirmed',confirmed_name=by[target]['name'],applied=True)
 if sid in aliases:item.update(merged_into=target);state['retired_name_items'].append(item)
 else:state['name_items'].append(item)
(w/'review_state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n');(run/'空间合并与关系退出记录.json').write_text(json.dumps({'aliases':aliases,'merges':merge_log,'retired_relations':retired},ensure_ascii=False,indent=2)+'\n');(root/'annotation.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
print({'spaces':len(d['spaces']),'aliases':len(aliases),'unknown':sum(s['type']=='unknown' for s in d['spaces']),'relations':len(d['relations']),'name_records':len(state['name_items']),'retired_names':len(state['retired_name_items'])})
