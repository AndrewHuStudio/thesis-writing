from pathlib import Path
import json,sys,hashlib
from shapely.geometry import Polygon,Point
from shapely.ops import unary_union
import pymupdf
B=Path(__file__).resolve().parents[2];O=Path(__file__).resolve().parent
sys.path.insert(0,'/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts')
for p in sorted((B/'标注试样').iterdir()):
 if p.name[:2] not in ['46','47','48','49','50']:continue
 d=json.loads((p/'annotation.json').read_text());q=O/p.name;sp={s['id']:Polygon(s['polygon_px']) for s in d['spaces']}
 errors=[];far=[];overlaps=[]
 for r in d['relations']:
  if r['type']=='access':
   dist=sp[r['source']].distance(sp[r['target']])
   if dist>25:far.append([r['id'],r['source'],r['target'],round(dist,1)])
  for pt in r.get('openings',[]):
   ds=[round(sp[r[k]].boundary.distance(Point(pt['position_px'])),1) for k in ['source','target']]
   if max(ds)>20:errors.append([pt['id'],r['id'],r['source'],r['target'],pt['position_px'],ds])
 ids=list(sp)
 for i,a in enumerate(ids):
  for b in ids[i+1:]:
   area=sp[a].intersection(sp[b]).area
   if area>1:overlaps.append([a,b,area])
 before=json.loads((q/'修改前备份/annotation.json').read_text())
 oldids={s['id'] for s in before['spaces']}
 audit={'point_boundary_anomalies':errors,'access_pair_gaps':far,'overlaps':overlaps,
  'missing_old_space_ids':sorted(oldids-set(sp)),
  'source_hash_unchanged':hashlib.sha256((p/d['image']['file']).read_bytes()).hexdigest()==hashlib.sha256((q/'修改前备份'/d['image']['file']).read_bytes()).hexdigest(),
  'area_ratio_sum':sum(s.get('area_ratio',0) for s in d['spaces'])}
 (q/'几何与端点审计.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
 print(p.name[:2],json.dumps(audit,ensure_ascii=False))
 doc=pymupdf.open(p/'标注.svg');pix=doc[0].get_pixmap(matrix=pymupdf.Matrix(1,1));pix.save(q/'正式SVG预览.png')
