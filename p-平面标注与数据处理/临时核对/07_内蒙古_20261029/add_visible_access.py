from pathlib import Path
import json
from shapely.geometry import Polygon,Point
P=Path('p-写作过程/标注试样/07_内蒙古自治区儿童医院、妇产医院、妇幼保健院外迁合建项目/annotation.json');d=json.loads(P.read_text())
polys={s['id']:Polygon([(y,3260-x) for x,y in s['polygon_px']]) for s in d['spaces']}
keys={(frozenset([r['source'],r['target']]),r['type']) for r in d['relations'] if r['type']!='entrance'}
added=[]
# Manually reviewed door-facing rows: obstetric consultation wing and imaging centre only.
for s in d['spaces']:
 p=polys[s['id']];x1,y1,x2,y2=p.bounds;face=None
 if s['scope']=='obstetrics_outpatient' and s['type']=='unknown':
  if y2<220:face='bottom'
  elif 250<y1 and y2<645:
   if x2<980:face='right'
   elif 1025<x1 and x2<1115:face='right'
   elif 1160<x1 and x2<1260:face='left'
   elif 1255<x1 and x2<1338:face='right'
   elif x1>1395:face='left'
   elif x1>1160 and x2<1338 and y2<390:face='left'
 if s['scope']=='medical_imaging' and s['type'] in ['unknown','imaging']:
  if y1<910 and y2<1000:face='top'
  elif 1050<y1 and y2<1155 and s['type']=='imaging':face='bottom'
  elif 1195<y1 and y2<1342 and s['type']=='imaging':face='top'
  elif 1339<y1 and y2<1395:face='bottom'
  elif 1445<y1 and y2<1580 and s['type']=='imaging':face='bottom'
  elif y1>1640 and x2<2160:face='top'
 if not face:continue
 probe=Point({'left':(x1-5,(y1+y2)/2),'right':(x2+5,(y1+y2)/2),'top':((x1+x2)/2,y1-5),'bottom':((x1+x2)/2,y2+5)}[face])
 candidates=[t for t in d['spaces'] if t['type'] in ['corridor','hall'] and polys[t['id']].distance(probe)<9 and polys[t['id']].distance(p)<10]
 if not candidates:continue
 t=min(candidates,key=lambda t:polys[t['id']].distance(probe))
 key=(frozenset([s['id'],t['id']]),'access')
 if key in keys:continue
 rid=f'R{sum(r["type"]!="entrance" for r in d["relations"])+1:03d}'
 d['relations'].append(dict(id=rid,source=s['id'],target=t['id'],type='access'));keys.add(key);added.append((s['id'],t['id']))
P.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
Path('p-写作过程/临时核对/07_内蒙古_20261029/可辨门洞关系复核_临时.md').write_text('已目视检查产科门诊的分隔诊疗房间、影像中心上下排检查室及背面控制用房开口方向；仅保存人员可达关系，不保存门位、门宽或门扇。其他房间暂缺可达关系，不作不可达负例。\n\n'+'\n'.join(a+' ↔ '+b for a,b in added)+'\n')
print('Added visible door access relations:',len(added),'total',len(d['relations']))
