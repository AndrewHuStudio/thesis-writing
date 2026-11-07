from pathlib import Path
from collections import Counter
import json,sys,hashlib,xml.etree.ElementTree as ET
from shapely.geometry import Polygon,Point

W=Path(__file__).resolve().parent
P=W.parents[1]/'标注试样/23_西安经开医院'
sys.path.insert(0,'/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts')
import annotation_tools as at
d=json.loads((W/'名称同步后.json').read_text())
old=json.loads((P/'annotation.json').read_text())
spaces={s['id']:s for s in d['spaces']}
courts=['S092','S096','S133','S146','S150','S197','S202']
for sid in courts:
    spaces[sid].update(type='courtyard',level='open_space')
remove={55:'手术房间北侧未见可确认门口，南侧入口范围待K01确认',
        96:'S086仅见东侧内门至S087',99:'S089仅见东侧内门至S090',
        109:'S101仅见西侧内门至S100',111:'S103通过相邻诊室进出',
        114:'S106仅见西侧内门至S105',119:'管井S115未见明确人员入口，本轮不细究',
        157:'药库S164北侧封闭，人员门开向S163及S165',
        194:'S207通过西侧S206进出',197:'S210通过相邻诊室进出',
        200:'S213通过东侧S214进出',203:'S216经西侧S215进出',
        221:'S138与S166此段共墙；清晰开口位于S139一段，保留R220'}
removed=[]
for r in d['relations']:
    if r['id'].startswith('R') and int(r['id'][1:]) in remove:
        removed.append(dict(r,reason=remove[int(r['id'][1:])]))
d['relations']=[r for r in d['relations'] if r['id'] not in {r['id'] for r in removed}]
rels={tuple(sorted([r['source'],r['target']])):r for r in d['relations'] if r['type']=='access'}
rid=230
new=[]
def relation(a,b,typ='access'):
    global rid
    pair=tuple(sorted([a,b]))
    if typ=='access' and pair in rels:return rels[pair]
    r=dict(id=f'R{rid:03}',source=a,target=b,type=typ);rid+=1
    d['relations'].append(r);new.append(r)
    if typ=='access':rels[pair]=r
    return r
points=[]
for line in (W/'门洞判读.txt').read_text().splitlines():
    if not line.strip() or line.startswith('#'):continue
    a,b,x,y,*kind=line.split()
    points.append((f'S{int(a):03}',f'S{int(b):03}',int(x),int(y),kind[0] if kind else 'door'))
# 稳定P号首次按图面由上到下，同排由左到右分配。
points.sort(key=lambda row:(row[3],row[2],row[0],row[1]))
audits=[]
for n,(a,b,x,y,kind) in enumerate(points,1):
    r=relation(a,b)
    opening=dict(id=f'P{n:03}',kind=kind,position_px=[x,y])
    r.setdefault('openings',[]).append(opening)
    distances={sid:round(Polygon(spaces[sid]['polygon_px']).distance(Point(x,y)),2) for sid in (a,b)}
    bounds={sid:round(Polygon(spaces[sid]['polygon_px']).boundary.distance(Point(x,y)),2) for sid in (a,b)}
    audits.append(dict(opening=opening['id'],relation=r['id'],pair=[a,b],position=[x,y],distances=distances,boundary_distances=bounds))
# 电梯面向前室、服务柜台端部通行采用概念连接，不虚构门位。
relation('S011','S013')
relation('S074','S078')
relation('S073','S078','service')
relation('S165','S166','service')
# 二次放大已确认S157西侧单门直达公共大厅；沿用先前已分配P号。
r=relation('S157','S138')
r['openings']=[dict(id='P226',kind='door',position_px=[1380,2220])]
points.append(('S157','S138',1380,2220,'door'))
audits.append(dict(opening='P226',relation=r['id'],pair=['S157','S138'],position=[1380,2220],
    distances={sid:round(Polygon(spaces[sid]['polygon_px']).distance(Point(1380,2220)),2) for sid in ('S157','S138')},
    boundary_distances={sid:round(Polygon(spaces[sid]['polygon_px']).boundary.distance(Point(1380,2220)),2) for sid in ('S157','S138')}))
# 既有入口移至图面实际开口中心；同门厅的第二个外门单列。
for r in d['relations']:
    if r['id']=='E03':r['position_px']=[1834,1550]
    if r['id']=='E04':r['position_px']=[2282,715]
    if r['id']=='E06':r['position_px']=[193,2594]
    if r['id']=='E07':r['position_px']=[2282,2578]
entrances=[('东侧门厅南门','S077',[1834,1650]),
 ('药房西侧入口','S134',[193,1960]),('中药房北侧入口','S120',[930,1789]),
 ('中段门诊东侧入口','S166',[2134,1950]),('中段门诊南侧入口','S166',[2035,2207]),
 ('老年门诊西侧南门','S180',[193,2665]),('放射南侧入口','S066',[325,1673])]
for n,(name,target,pos) in enumerate(entrances,8):
    d['relations'].append(dict(id=f'E{n:02}',source=None,target=target,type='entrance',
                               name=name,entrance_type='department',position_px=pos))
at.normalize(d)
assert len(d['spaces'])==219 and all(s['type']!='unknown' for s in d['spaces'])
assert all(s['polygon_px']==spaces[s['id']]['polygon_px'] for s in old['spaces'])
path=P/'annotation.json';path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
at.render(d,path,P/'标注.svg')
# 本图P标签字号较小，缩减白色描边，确保离线渲染后仍显示深红字。
tree=ET.parse(P/'标注.svg')
for group in tree.getroot().iter():
    if group.get('data-opening-id'):
        for label in group:
            if label.tag=='{'+at.NS+'}text':
                label.set('stroke-width','0.6');label.set('fill','#991b1b')
tree.write(P/'标注.svg',encoding='unicode')
at.summary(d,W/'生成概览.md')
report,code=at.check(d,path,check_dir=True)
(W/'几何门位审计.json').write_text(json.dumps(audits,ensure_ascii=False,indent=2))
(W/'关系调整记录.json').write_text(json.dumps(dict(removed=removed,added=new),ensure_ascii=False,indent=2))
(W/'正式校验.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(dict(**report,types=Counter(s['type'] for s in d['spaces']),
 relations_by_type=Counter(r['type'] for r in d['relations']),openings=len(points),
 removed=len(removed),new_relations=len(new),
 far_openings=[a for a in audits if max(a['distances'].values())>12]),ensure_ascii=False,indent=2))
