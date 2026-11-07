from pathlib import Path
from collections import Counter
import json,re,hashlib,base64,xml.etree.ElementTree as ET
from shapely.geometry import Polygon,Point,box

RUN=Path(__file__).resolve().parent;R=RUN.parent;P=R.parent.parent/'标注试样'/R.name
D=json.loads((P/'annotation.json').read_text());old=json.loads((RUN/'修改前备份/annotation.json').read_text())
S={s['id']:s for s in D['spaces']};before={s['id']:s for s in old['spaces']}
assert set(S)-set(before)=={'S153','S154'} and not set(before)-set(S)
assert all(S[sn]['name']==s['name'] and S[sn]['type']==s['type'] for sn,s in before.items())
assert set(D)=={'image','spaces','relations'}
polys={sn:Polygon(s['polygon_px']) for sn,s in S.items()}
old_p={o['id']:(r['id'],r['source'],r['target'],o['kind'],o['position_px']) for r in old['relations'] for o in r.get('openings',[])}
new_p={o['id']:(r['id'],r['source'],r['target'],o['kind'],o['position_px']) for r in D['relations'] for o in r.get('openings',[])}
assert all(new_p[k]==v for k,v in old_p.items())
assert set(new_p)-set(old_p)=={'P147','P148','P149'}
root=ET.parse(P/'标注.svg').getroot();ns={'s':'http://www.w3.org/2000/svg'}
labels_out=[]
for sn,poly in polys.items():
 group=root.find('.//s:g[@id="'+sn+'"]',ns);a=group.find('s:rect',ns).attrib
 x,y,w,h=[float(a[k]) for k in ['x','y','width','height']]
 if not poly.covers(box(x,y,x+w,y+h)):labels_out.append(sn)
assert not labels_out,labels_out
maxdist=0;unrelated=[]
for r in D['relations']:
 for o in r.get('openings',[]):
  p=Point(o['position_px']);a,b=r['source'],r['target']
  maxdist=max(maxdist,polys[a].distance(p),polys[b].distance(p))
  for sn,poly in polys.items():
   if sn not in [a,b] and poly.contains(p) and poly.boundary.distance(p)>.1:unrelated.append((o['id'],sn))
assert maxdist<4.5 and not unrelated,(maxdist,unrelated)
sha=hashlib.sha256((P/D['image']['file']).read_bytes()).hexdigest();assert sha==hashlib.sha256((RUN/'修改前备份'/D['image']['file']).read_bytes()).hexdigest()
background=root.find('.//s:image',ns);uri=background.get('{http://www.w3.org/1999/xlink}href');assert hashlib.sha256(base64.b64decode(uri.split(',',1)[1])).hexdigest()==sha
Q=json.loads((R/'固定核对映射.json').read_text());Q0=json.loads((RUN/'修改前备份/固定核对映射.json').read_text());assert [(q['number'],q['id']) for q in Q[:116]]==[(q['number'],q['id']) for q in Q0]
assert len(Q)==118 and {q['id'] for q in Q}=={s['id'] for s in S.values() if s['type']=='unknown'}
md=(P/'标注说明.md').read_text();links=re.findall(r'!\[[^]]*\]\(([^)]+)\)',md);assert all((P/f).exists() for f in links)
assert len([f for f in P.iterdir() if f.is_file()])==4
ratio=sum(s.get('area_ratio',0) for s in S.values());assert abs(ratio-1)<1e-6
stat={'spaces':len(S),'new_space_ids':['S153','S154'],'unknown':118,
 'relations':len(D['relations']),'relation_types':dict(Counter(r['type'] for r in D['relations'])),
 'openings':len(new_p),'new_opening_ids':['P147','P148','P149'],
 'existing_ids_and_openings_preserved':True,'area_ratio_sum':ratio,
 'regional_outlines':len([e for e in root.iter() if e.get('data-region-id')]),
 'all_space_labels_inside':True,'max_opening_polygon_distance_px':round(maxdist,3),
 'unrelated_space_openings':[],'source_unchanged':True,'source_sha256':sha,
 'svg_background_bytes_match_source':True,'image_links_valid':len(links),'formal_files':sorted(f.name for f in P.iterdir() if f.is_file())}
(RUN/'交付一致性检查.json').write_text(json.dumps(stat,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(stat,ensure_ascii=False,indent=2))
