from pathlib import Path
import json
from shapely.geometry import Polygon,Point
w=Path(__file__).resolve().parent;p=next((w.parents[1]/'标注试样').glob('07_*'));d=json.loads((p/'annotation.json').read_text());ss={s['id']:s for s in d['spaces']};ps={s['id']:Polygon(s['polygon_px']) for s in d['spaces']};rows=[]
for line in (w/'目视开口记录.txt').read_text().splitlines():
 if not line or line.startswith('#'):continue
 z=line.split();a='S'+z[0];q=list(map(float,z[1:3]));pt=Point(q);cands=sorted((ps[s['id']].distance(pt),s['id']) for s in d['spaces'] if s['type'] in ['corridor','hall'] and s['id']!=a)
 b='S'+z[3] if len(z)>3 else cands[0][1]
 da=ps[a].distance(pt);db=ps[b].distance(pt)
 rows.append(dict(source=a,target=b,position_px=q,source_distance=round(da,1),target_distance=round(db,1),candidates=cands[:3]))
 if da>9 or db>12:print('CHECK',a,b,q,round(da,1),round(db,1),cands[:2])
(w/'点位空间对应_工作.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2));print('TOTAL',len(rows))
