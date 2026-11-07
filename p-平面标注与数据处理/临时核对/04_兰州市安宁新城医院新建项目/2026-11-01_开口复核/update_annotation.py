from pathlib import Path
from collections import Counter
import json, importlib.util, hashlib
from shapely.geometry import Polygon, Point

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[2]/'标注试样/04_兰州市安宁新城医院新建项目'
SKILL=Path('/Users/hushili/.codex/skills/outpatient-plan-annotation')
spec=importlib.util.spec_from_file_location('ann',SKILL/'scripts/annotation_tools.py')
ann=importlib.util.module_from_spec(spec);spec.loader.exec_module(ann)
d=json.loads((HERE/'修改前备份/annotation.json').read_text())
by={s['id']:s for s in d['spaces']}
old=json.loads(json.dumps(d))
# Names and all existing polygons are retained. Classification follows confirmed facts.
by['S034']['type']='conference'
by['S187']['type']='courtyard';by['S187']['level']='open_space'
# Control-room outlines previously stopped 28 px short of the visible south wall.
# Extend within the old corridor notch; the total footprint is unchanged.
for sid in ['S181','S183']:
    by[sid]['polygon_px']=[[x,1928 if y==1900 else y] for x,y in by[sid]['polygon_px']]
for sid in ['S243','S244']:
    by[sid]['polygon_px']=[[x,y] for x,y in by[sid]['polygon_px'] if y!=1900]
# The north DSA service cells were offset one small bay to the east. Re-align
# their shared boundaries to the visible walls; retain IDs, names and footprint.
def rect(sid,x1,y1,x2,y2):by[sid]['polygon_px']=[[x1,y1],[x2,y1],[x2,y2],[x1,y2]]
rect('S169',1176,1540,1270,1620)
rect('S170',1270,1540,1314,1580)
rect('S171',1314,1540,1358,1580)
rect('S172',1358,1540,1404,1620)
rect('S242',1270,1580,1358,1620)
new=[]
for x,y in by['S244']['polygon_px']:
    if x==1420 and y in [1540,1620]:
        new.append([1404,y])
        if y==1620:new.append([1420,1620])
    else:new.append([x,y])
by['S244']['polygon_px']=new

# These old edges cross intervening spaces, or a continuous wall / counter.
# They are archived here; uncertainty is discussed in the review table, not encoded as fact.
remove={35,52,59,60,68,89,104,113,117,123,125,126,127,128,149,151,154,157,158,171,172,173,175,179,190,197,202,203,209}
removed=[r for r in d['relations'] if r['id'].startswith('R') and int(r['id'][1:]) in remove]
d['relations']=[r for r in d['relations'] if r not in removed]
# The pediatric fee counter has no readable staff door. Keep service separately.
for r in d['relations']:
    if r['id']=='R026':r['type']='service'
    if r['id']=='R072':r['target']='S232'
    if r['id']=='R141':r['target']='S244'

next_r=211
def relation(a,b,typ='access'):
    global next_r
    a=f'S{a:03d}' if isinstance(a,int) else a
    b=f'S{b:03d}' if isinstance(b,int) else b
    found=[r for r in d['relations'] if r['type']==typ and {r['source'],r['target']}=={a,b}]
    if found:return found[0]
    r=dict(id=f'R{next_r:03d}',source=a,target=b,type=typ);next_r+=1
    d['relations'].append(r);return r

# Every coordinate below was read from this hospital's original image, never generated
# from centroids, shared-wall midpoints or another hospital. o means a visible open passage.
# Coordinates are approximate: existing conceptual polygons can differ from wall ink by 10-20 px.
points='''
2 215 1872 478 o
3 215 1935 478
4 215 1957 478
5 214 2062 478
6 214 2085 478
7 215 1784 503
8 215 1755 620
9 215 1827 620
10 215 1936 620
11 215 1995 530
12 214 2062 620
13 214 2085 620
14 214 2250 574
1 14 2278 530
16 214 2250 690
17 214 2250 727
18 214 2250 766
19 215 1936 670
20 215 1957 670
19 20 1946 736
21 217 1946 758
22 214 2112 670
23 214 2202 670
24 212 1738 776
215 212 1738 642
214 218 2231 822
27 25 1989 904
28 25 2032 904
29 25 2078 904
30 25 2138 904
25 218 2216 918
25 218 2216 1144
31 218 2250 838
32 218 2250 889
33 218 2250 946
34 218 2250 1038
35 218 2250 1077
36 218 2250 1107
37 218 2250 1150
26 38 1850 1164
218 38 2232 1164
39 38 2250 1206
26 212 1738 838
26 212 1738 1144
43 212 1738 1371
43 212 1738 1504
48 38 2206 1252
48 42 2166 1286
49 42 2166 1390
50 42 2166 1460
51 42 2166 1488
44 43 1770 1352
52 43 1820 1536
52 223 2154 1610
53 212 1738 1576
54 223 2207 1610
235 212 1610 1096
38 212 1738 1205 o
58 223 1909 2444
59 213 1738 2483
60 58 1892 2513
61 62 1816 2569
61 225 1802 2620
62 225 1829 2620
63 225 1798 2666
64 225 1820 2666
65 63 1780 2718
67 58 1906 2666
67 68 1946 2677
58 70 2027 2666
58 71 2240 2635
70 226 2027 2796
70 226 2224 2796
72 73 2271 2796
73 226 2240 2834
78 226 1772 2884
227 226 1832 2884
74 226 2221 2884
79 227 1814 2980
81 227 1814 3049
82 227 1814 3096
83 77 1916 2926
84 76 1916 3003
85 84 1867 3044
86 76 1916 3095
76 74 2182 2974
76 227 1944 3184
75 74 2344 3112
75 74 2344 3191
88 87 2344 3241
88 87 2344 3331
74 227 2182 3202
90 231 1907 3352
91 228 1941 3256
89 231 1782 3352 o
95 231 1749 3407
96 231 1774 3512
97 231 1994 3407
98 231 2018 3407
99 232 2084 3484
100 232 2169 3484
101 232 2240 3475
103 231 1868 3545 o
104 231 1935 3545
105 231 1957 3545
106 232 2061 3545
107 232 2085 3545
108 232 2178 3545
109 232 2204 3545
213 225 1738 2643
213 227 1738 3195
213 231 1738 3375
240 213 1610 2980
112 234 496 1060 o
113 234 548 1060
113 234 594 1060
114 234 795 957
115 234 917 956
115 234 960 956
115 235 1005 956
116 235 1165 946
117 235 1375 1060
118 235 1580 1060 o
120 234 466 1114
121 234 525 1114
121 234 638 1114
122 234 716 1114
123 234 748 1114
123 126 806 1144
124 126 806 1173
125 126 806 1200
126 234 823 1114
126 235 1095 1114
127 235 1120 1114
127 235 1164 1114
128 235 1188 1114
129 235 1313 1114
130 235 1340 1114
130 235 1480 1114
131 239 496 2960 o
132 239 548 2960
132 239 594 2960
133 136 806 2844
135 136 806 2903
136 239 821 2918
136 240 1095 2918
137 240 1160 2918
138 240 1375 2960
139 240 1580 2960 o
141 239 466 3004
142 239 525 3004
142 239 716 3004
143 239 795 3080
144 239 917 3080
144 239 960 3080
144 240 1005 3080
145 240 1165 3080
146 240 1188 3004
147 240 1313 3004
148 240 1340 3004
148 240 1480 3004
149 243 688 1630
150 243 688 1743
151 243 688 1825
152 153 660 1954
153 243 688 1979
154 243 688 2128
155 243 688 2185
156 243 688 2260
157 243 688 2315
158 243 688 2460
159 244 1464 1630
160 244 1464 2420
210 159 1478 1540
211 160 1478 2534
162 243 913 1575
162 243 916 1680
161 162 878 1667
163 243 937 1575
163 243 944 1680
164 243 971 1575
164 243 986 1680
164 165 1028 1667
166 243 828 1695
167 244 1076 1695
169 241 1176 1555
170 242 1299 1578
171 242 1324 1578
172 242 1358 1589
168 242 1291 1615
173 244 1420 1632
174 168 1338 1655
175 244 1420 1725
180 243 868 1816
180 176 826 1827
180 177 908 1827
181 243 864 1928
181 176 826 1910
181 177 908 1910
182 244 1161 1816
182 178 1118 1827
182 179 1200 1827
183 244 1157 1928
183 178 1118 1910
183 179 1200 1910
184 244 1348 1928
186 243 847 1964
186 243 847 2110
188 244 1326 1964
188 244 1326 2110
189 243 790 2158
190 243 812 2158
191 243 940 2158
192 243 965 2158
193 244 1087 2158
194 244 1114 2158
195 244 1237 2158
196 244 1261 2158
197 244 1351 2158
185 224 1610 1789
185 224 1610 2273
198 243 815 2480
199 200 865 2424
201 243 893 2480
202 243 1008 2368
204 244 1042 2480
205 206 1178 2391
205 206 1178 2430
205 244 1159 2480
206 244 1200 2480
207 244 1308 2368
208 207 1295 2448
209 244 1342 2480
'''

point_records=[]
for line in points.strip().splitlines():
    a,b,x,y,*kind=line.split();a,b,x,y=map(int,[a,b,x,y])
    r=relation(a,b)
    oid=f'P{len(point_records)+1:03d}'
    o=dict(id=oid,kind='open_passage' if kind else 'door',position_px=[x,y])
    r.setdefault('openings',[]).append(o)
    point_records.append((oid,r['id'],r['source'],r['target'],x,y,o['kind']))

# Actual unpartitioned continua, escalator landing access, and half-wall work areas.
for a,b in [(20,217),(217,22),(218,25),(169,242),(58,225),
            (74,87),(87,229),(214,215),(77,76),(93,87),(94,87)]:
    relation(a,b)
# Counter service is not a staff entrance. Preserve both types where an actual staff
# door is separately located (e.g. S052 and settlement desks).
for a,b in [(15,214),(20,22),(93,87),(94,87)]:
    relation(a,b,'service')

# R003 already holds the nurse-station service window; do not imply the whole counter
# is a wall door. R170 is retained because a separate end staff door is visible.
ann.normalize(d)
(PROJECT/'annotation.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
ann.render(d,PROJECT/'annotation.json',PROJECT/'标注.svg')
ann.summary(d,HERE/'自动概览.md')
(HERE/'移除的旧连接.json').write_text(json.dumps(removed,ensure_ascii=False,indent=2)+'\n')
(HERE/'开口复核记录.tsv').write_text('开口\t关系\t起点\t终点\tx\ty\t类别\n'+'\n'.join('\t'.join(map(str,row)) for row in point_records)+'\n')
polys={s['id']:Polygon(s['polygon_px']) for s in d['spaces']}
warnings=[]
for oid,rid,a,b,x,y,k in point_records:
    da,db=[polys[s].distance(Point(x,y)) for s in (a,b)]
    if max(da,db)>22:warnings.append((oid,rid,a,b,x,y,round(da,1),round(db,1)))
print('points',len(point_records),'relations',Counter(r['type'] for r in d['relations']))
print('Geometry distance >22px:',warnings)
print('Unlocated access',[(r['id'],r['source'],r['target']) for r in d['relations'] if r['type']=='access' and not r.get('openings')])
print('names retained',all(by[s['id']]['name']==s['name'] for s in old['spaces']))
print('modified polygons',[s['id'] for s in old['spaces'] if by[s['id']]['polygon_px']!=s['polygon_px']])
