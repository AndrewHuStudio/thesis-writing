import json
from pathlib import Path
p=Path('/tmp/outpatient23-review/review_mapping.json');rs=json.loads(p.read_text());out=[]
for group in dict.fromkeys(r['group'] for r in rs):
 a=sorted([r for r in rs if r['group']==group],key=lambda r:(min(y for x,y in r['polygon_px']),min(x for x,y in r['polygon_px'])))
 bands=[]
 for r in a:
  y=min(y for x,y in r['polygon_px'])
  if not bands or y-bands[-1][0]>20:bands.append([y,[]])
  bands[-1][1].append(r)
 for _,b in bands:
  b.sort(key=lambda r:(min(x for x,y in r['polygon_px']),min(y for x,y in r['polygon_px'])))
  out.extend(b)
for i,r in enumerate(out,1):r['number']=f'{i:02d}'
p.write_text(json.dumps(out,ensure_ascii=False,indent=2))
print([(r['number'],r['id'],r['key']) for r in out[:29]])