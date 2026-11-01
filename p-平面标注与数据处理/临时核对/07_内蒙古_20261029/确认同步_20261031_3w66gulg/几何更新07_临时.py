from pathlib import Path
import copy,json
from shapely.geometry import Polygon,box
B=Path(__file__).resolve().parent
D=json.loads((B/'同步中_临时.json').read_text()); by={s['id']:s for s in D['spaces']}; changes=[]
assert max(int(s[1:]) for s in by)==406
next_id=407
def rectcoords(x0,y0,x1,y1):return [[x0,y0],[x1,y0],[x1,y1],[x0,y1]]
def newspace(template,name,typ,coords):
 global next_id
 s=copy.deepcopy(template);s.update(id=f'S{next_id:03}',name=name,type=typ,polygon_px=coords,level='room');next_id+=1
 D['spaces'].append(s);by[s['id']]=s;return s
# 66号：原图可辨左上刷手、左下更衣、右侧准备，保留原S084给刷手。
parent=copy.deepcopy(by['S084'])
by['S084'].update(name='刷手',type='staff_support',polygon_px=rectcoords(2474,629,2547,652))
a=newspace(parent,'更衣','staff_support',rectcoords(2474,657,2547,700))
b=newspace(parent,'准备间','patient_preparation',rectcoords(2556,629,2607,700))
changes.append({'number':'66','old':['S084'],'new':['S084',a['id'],b['id']],'names':['刷手','更衣','准备间']})
# 203号：上方阅片室、下方办公室；208属于该办公室，合并同一室内的错误分区。
parent=copy.deepcopy(by['S295'])
by['S295'].update(name='阅片室',type='office',polygon_px=rectcoords(1538,1689,1614,1742))
office=newspace(parent,'办公室','office',rectcoords(1538,1747,1614,1881))
old=by.pop('S302'); D['spaces']=[s for s in D['spaces'] if s['id']!='S302']
for rel in D['relations']:
 for k in ['source','target']:
  if rel[k]=='S302':rel[k]=office['id']
changes.append({'number':'203/208','old':['S295','S302'],'new':['S295',office['id']],'names':['阅片室','办公室']})
# 新室内范围仅用于修正对应原分区；若侵入原走廊的错误缝隙，裁去该处重叠，避免重复计面积。
for sid in ['S267','S268']:
 s=by[sid]; poly=Polygon(s['polygon_px']); over=poly.intersection(Polygon(office['polygon_px'])).area
 if over>0:
  trimmed=poly.difference(Polygon(office['polygon_px']))
  assert trimmed.geom_type=='Polygon' and not trimmed.interiors,(sid,trimmed.geom_type)
  s['polygon_px']=[list(pt) for pt in list(trimmed.exterior.coords)[:-1]]
  changes.append({'corridor_trim':sid,'removed_overlap_px2':over})
# 只增加原图开口明确支持的关系，不以相邻代替可达。
next_rel=max(int(r['id'][1:]) for r in D['relations'] if r['id'].startswith('R'))+1
for a,b in [('S084',b['id']),('S407','S408'),('S408','S051')]:
 D['relations'].append({'id':f'R{next_rel:03}','source':a,'target':b,'type':'access'});next_rel+=1
# 持久化后续待确认数据，不写入正式样本。
(B/'几何已调整_临时.json').write_text(json.dumps(D,ensure_ascii=False,indent=2))
(B/'几何变更_临时.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2))
print('CHANGES',json.dumps(changes,ensure_ascii=False))
print('WORKING_COUNTS',len(D['spaces']),len(D['relations']))
