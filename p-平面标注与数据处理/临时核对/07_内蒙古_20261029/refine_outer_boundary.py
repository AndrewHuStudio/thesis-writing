from pathlib import Path
import json
from shapely.geometry import Polygon,box
from shapely.ops import unary_union
P=Path('p-写作过程/标注试样/07_内蒙古自治区儿童医院、妇产医院、妇幼保健院外迁合建项目/annotation.json');T=Path('p-写作过程/临时核对/07_内蒙古_20261029');d=json.loads(P.read_text())
A=Polygon([(315,155),(550,155),(585,164),(610,188),(626,218),(626,258),(845,258),(845,790),(245,790),(245,218),(258,181),(282,162)])
F=Polygon([(245,2058),(845,2058),(845,2589),(626,2589),(626,2627),(611,2662),(585,2680),(550,2690),(315,2690),(282,2680),(258,2660),(245,2627)])
B=Polygon([(974,155),(1390,155),(1432,165),(1457,188),(1470,218),(1470,790),(888,790),(888,218),(901,181),(929,162)])
G=Polygon([(888,2058),(1470,2058),(1470,2627),(1457,2660),(1432,2680),(1390,2690),(974,2690),(929,2680),(901,2660),(888,2627)])
C=unary_union([Polygon([(1818,155),(2257,155),(2298,165),(2324,188),(2335,218),(2335,790),(1740,790),(1740,218),(1753,181),(1778,162)]),box(1468,650,1740,790)])
H=unary_union([Polygon([(1740,2058),(2335,2058),(2335,2627),(2324,2660),(2298,2680),(2257,2690),(1818,2690),(1778,2680),(1753,2660),(1740,2627)]),box(1468,2058,1740,2197)])
bounds={'emergency_pediatrics':F,'emergency_obstetrics_gynecology':A,'obstetrics_outpatient':B,'perinatal_care':C,'obstetric_ultrasound':C,'infusion_center':G,'fever_outpatient':H,'pediatric_asthma_outpatient':H}
kept=[];removed=[]
for s in d['spaces']:
 p=Polygon([(y,3260-x) for x,y in s['polygon_px']])
 if s['scope'] in bounds:p=p.intersection(bounds[s['scope']])
 if p.is_empty or p.area<150:
  if s['type']=='unknown':raise RuntimeError('Unknown unexpectedly outside outline '+s['id'])
  removed.append(s['id']);continue
 if hasattr(p,'geoms'):p=max(p.geoms,key=lambda q:q.area)
 s['polygon_px']=[[round(3260-y,2),round(x,2)] for x,y in list(p.exterior.coords)[:-1]];kept.append(s)
d['spaces']=kept;ids={s['id'] for s in kept};d['relations']=[r for r in d['relations'] if r['target'] in ids and (r['source'] is None or r['source'] in ids)]
P.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
reviews=json.loads((T/'核对对应_临时.json').read_text());byid={s['id']:s for s in kept}
for q in reviews:q['polygon_px']=byid[q['id']]['polygon_px']
(T/'核对对应_临时.json').write_text(json.dumps(reviews,ensure_ascii=False,indent=2)+'\n')
print('Refined exterior; removed empty exterior circulation pieces:',removed,'spaces',len(kept),'relations',len(d['relations']))
