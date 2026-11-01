from pathlib import Path
import json,collections,importlib.util
from shapely.geometry import Polygon,box
from shapely.ops import unary_union
out=Path(__file__).parent;p=out.parents[2]/'02_嘉兴市第一医院迁建工程'
d=json.loads((out/'修改前备份'/'annotation.json').read_text());a=json.loads((out/'逐点目读.json').read_text())
# Values indexed by initial manual read order; revisions made after enlarged original-image review.
remove={14,15,91,100,101,114,115,157,164,176,187,185,191,197,202,219,220,224,227,237}
# IDs above are temporary review indices, not P identifiers (P identifiers assigned only below).
fix={18:(50,255,490,777),99:(118,124,2470,537),108:(127,138,2306,749),113:(10,263,2320,886),118:(137,263,1886,886),
156:(166,267,2041,1200),184:(183,184,1920,1480),190:(188,17,2189,1464),192:(189,265,2265,1477),193:(191,265,2265,1517),
221:(218,272,2144,1666),222:(218,217,2092,1680),223:(219,220,2306,1767),225:(34,271,2446,1700)}
rec=[]
for i,(s,t,x,y,k) in enumerate(a['points'],1):
 if i in remove:continue
 if i in fix:
  v=fix[i];s,t=f'S{v[0]:03}',f'S{v[1]:03}';x,y=v[2:]
 rec.append([s,t,x,y,k])
extra='''
038 040 509 430
038 039 476 451
041 258 984 420
254 258 984 520
259 263 1767 898
259 264 1767 1010
259 264 1767 1149
260 264 1767 1260
260 264 1767 1425
260 266 1767 1567
260 272 1767 1654
256 259 984 1048
257 260 984 1360
257 260 984 1578
183 264 1918 1450
186 264 2050 1450
106 276 1271 1781
107 276 1345 1781
107 276 1415 1781
107 276 1456 1781
047 254 938 539
049 258 984 671
007 255 847 897
066 067 949 880
073 256 847 1098
053 255 445 976
053 255 445 1004
053 255 445 925
111 116 1817 396
112 116 1894 396
121 123 2320 552
122 123 2416 552
011 138 2202 758
012 138 2237 758
129 262 2464 679
133 262 2464 935
149 153 2331 919
016 264 1888 1450
016 182 1809 1544
016 184 1908 1544
017 264 2104 1450
017 190 2189 1520
214 212 1880 1716
213 212 1880 1696
214 216 1924 1769
215 216 1966 1706
215 217 1977 1676
217 276 1991 1781
216 276 1950 1781
214 276 1900 1781
217 026 2092 1764
026 276 2144 1781
219 276 2263 1781
025 276 2371 1781
034 276 2420 1781
023 273 2501 1710
273 024 2518 1721
023 271 2464 1695
208 272 2292 1666
224 274 2078 1976
224 274 2009 1976
222 274 1844 1976
225 276 2112 1891
231 230 1818 2572
232 230 1842 2572
238 275 1410 2693
239 275 1445 2693
239 275 1728 2693
245 246 532 2077
245 246 532 2199
246 248 818 2153
250 276 975 2125
'''
for l in extra.strip().splitlines():
 s,t,x,y=map(int,l.split());rec.append([f'S{s:03}',f'S{t:03}',x,y,'door'])
# A visible open threshold at the main east passage to the emergency suite; not the colour boundary.
rec.append(['S255','S258',984,753,'door'])
rec.append(['S256','S260',984,1184,'door']) # reviewed later: segment assignment QA below
# Scope geometry: recover the omitted MR side and south passage as part of stable S265.
s265=next(s for s in d['spaces'] if s['id']=='S265');g=unary_union([Polygon(s265['polygon_px']),box(2265.471,1450.387,2309.284,1554.507),box(2309.284,1532.587,2427.943,1554.507)])
assert g.geom_type=='Polygon';s265['polygon_px']=[[round(x,3),round(y,3)] for x,y in list(g.exterior.coords)[:-1]]
s050=next(s for s in d['spaces'] if s['id']=='S050');s255=next(s for s in d['spaces'] if s['id']=='S255')
cut=box(480,777,538.529,800.087)
for sp,geom in [(s050,Polygon(s050['polygon_px']).difference(cut)),(s255,unary_union([Polygon(s255['polygon_px']),cut]))]:
 assert geom.geom_type=='Polygon';sp['polygon_px']=[[round(x,3),round(y,3)] for x,y in list(geom.exterior.coords)[:-1]]
# All specific names remain unchanged. These six names unambiguously map to existing shared categories.
type_updates={'S023':'waste_handling','S094':'waste_handling','S133':'waste_handling','S086':'operating_room','S107':'education','S203':'education','S246':'education'}
for s in d['spaces']:
 if s['id'] in type_updates:s['type']=type_updates[s['id']]
concept=[tuple(x) for x in a['concept_pairs']]
# One claimed corridor is only a triangular sliver in the old segmentation; no inferred access retained.
concept=[v for v in concept if set(v) not in [set(['S255','S254']),set(['S243','S276'])]]
concept.extend([('S265','S268')])
# Continuity along this region is real, but drawn room geometry is imperfect; isolate in questions instead.
old_by_pair={tuple(sorted((r['source'],r['target']))):r for r in d['relations'] if r['type']=='access'}
newnum=max(int(r['id'][1:]) for r in d['relations'] if r['id'].startswith('R'))
rels={};points=[]
for s,t,x,y,k in rec:
 pair=tuple(sorted([s,t]));
 if pair not in rels:
  old=old_by_pair.get(pair)
  if old:rels[pair]={'id':old['id'],'source':old['source'],'target':old['target'],'type':'access'}
  else:newnum+=1;rels[pair]={'id':f'R{newnum:03}','source':s,'target':t,'type':'access'}
 r=rels[pair];oid=f'P{len(points)+1:03}';o={'id':oid,'kind':k,'position_px':[x,y]};r.setdefault('openings',[]).append(o);points.append((r['id'],s,t,o))
for s,t in concept:
 pair=tuple(sorted([s,t]))
 if pair in rels:continue
 old=old_by_pair.get(pair)
 if old:rels[pair]={'id':old['id'],'source':old['source'],'target':old['target'],'type':'access'}
 else:newnum+=1;rels[pair]={'id':f'R{newnum:03}','source':s,'target':t,'type':'access'}
oldaccess=[r for r in d['relations'] if r['type']=='access'];removed=[r for r in oldaccess if tuple(sorted((r['source'],r['target']))) not in rels]
d['relations']=[r for r in d['relations'] if r['type']!='access']+list(rels.values());d['relations'].sort(key=lambda r:(r['type']=='entrance',int(r['id'][1:])))
(out/'更新草稿.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
(out/'旧关系复核待定.json').write_text(json.dumps(removed,ensure_ascii=False,indent=2)+'\n')
from shapely.geometry import Point
pol={s['id']:Polygon(s['polygon_px']) for s in d['spaces']}
for rid,s,t,o in points:
 x,y=o['position_px'];dist=[pol[z].distance(Point(x,y)) for z in [s,t]]
 if max(dist)>15:print('distance QA',o['id'],s,t,[x,y],[round(v,1) for v in dist])
print('points',len(points),'relations',collections.Counter(r['type'] for r in d['relations']),'removed old access',len(removed));print('removed',[(r['id'],r['source'],r['target']) for r in removed]);print('class changes',type_updates)
