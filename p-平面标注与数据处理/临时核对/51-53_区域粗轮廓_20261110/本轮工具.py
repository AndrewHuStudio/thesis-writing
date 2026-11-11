"""本轮逐图数据编辑；51/52编辑坐标为逆时针转正后的像素，输出仍用原图坐标。"""
from pathlib import Path
import sys,json,copy
from shapely.geometry import Polygon,box,Point,LineString
from shapely.ops import unary_union,split
sys.path.insert(0,'/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts')
from annotation_tools import normalize,render
import 局部标签
from review_workflow import load_state,save_state
BASE=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent

def sid(v):return v if isinstance(v,str) else f'S{v:03}'

def parts(g):
    if g.geom_type=='Polygon':return [g]
    return [p for p in g.geoms if p.geom_type=='Polygon' and p.area>1]

def noholes(g):
    if not g.interiors:return [g]
    q=Polygon(g.interiors[0]).representative_point()
    seg=LineString([(g.bounds[0]-1,q.y),(g.bounds[2]+1,q.y)])
    return [v for p in split(g,seg).geoms for v in noholes(p)]

class Editor:
    def __init__(self,n):
        self.n=n;self.sample=next((BASE/'标注试样').glob(f'{n}_*'));self.review=OUT/self.sample.name
        self.data=json.loads((self.review/'修改前备份/annotation.json').read_text())
        self.old=copy.deepcopy(self.data);self.sp={s['id']:s for s in self.data['spaces']}
        self.geo={s['id']:Polygon(self.upright(s['polygon_px'])) for s in self.data['spaces']}
        self.num=max(int(s[1:]) for s in self.sp);self.log=[];self.groups={};self.regions=[]
        self.rnum=max(int(r['id'][1:]) for r in self.data['relations'] if r['id'].startswith('R'))
        self.pnum=max((int(p['id'][1:]) for r in self.data['relations'] for p in r.get('openings',[])),default=0)
        self.evidence=[]
    def upright(self,pts):
        return [(y,self.data['image']['width']-x) for x,y in pts] if self.n in [51,52] else pts
    def raw(self,pts):
        return [(self.data['image']['width']-y,x) for x,y in pts] if self.n in [51,52] else pts
    def set(self,i,poly=None,**fields):
        i=sid(i);self.sp[i].update(fields)
        if poly is not None:self.geo[i]=box(*poly) if len(poly)==4 and isinstance(poly[0],(int,float)) else Polygon(poly)
    def new(self,g,scope,name='名称未确认',typ='unknown',level='room',parent=None):
        self.num+=1;i=sid(self.num)
        self.sp[i]={'id':i,'name':name,'type':typ,'level':level,'scope':scope};self.geo[i]=g
        self.data['spaces'].append(self.sp[i]);self.log.append({'new_space':i,'parent_space':parent})
        return i
    def carve(self,i,rects):
        """手工判读的独立单元；不据此自动建立通行。"""
        i=sid(i);g=self.geo[i];ids=[]
        for spec in rects:
            rect=spec[:4];meta=spec[4] if len(spec)>4 else {}
            cut=g.intersection(box(*rect))
            assert cut.geom_type=='Polygon' and cut.area>20,(i,rect,cut.geom_type)
            ids.append(self.new(cut,self.sp[i]['scope'],parent=i,**meta));g=g.difference(cut)
        pp=sorted([x for p in parts(g) for x in noholes(p)],key=lambda p:p.area,reverse=True)
        assert pp,(i,'empty')
        self.geo[i]=pp[0]
        for p in pp[1:]:
            assert p.area>70,(i,'sliver',p.area)
            ids.append(self.new(p,self.sp[i]['scope'],name='区内通道',typ='corridor',level='open_space',parent=i))
        self.groups[i]=[i]+ids
        self.log.append({'split_parent':i,'children':ids,'reason':'本图可辨隔墙与房门；区域名称不下放成每间房的专名。'})
        return ids
    def rel(self,a,b,pt=None,kind='door',reason='原图可辨门洞或开口'):
        a,b=sid(a),sid(b)
        r=next((r for r in self.data['relations'] if r['type']=='access' and {r['source'],r['target']}=={a,b}),None)
        if r is None:
            self.rnum+=1;r={'id':f'R{self.rnum:03}','source':a,'target':b,'type':'access'};self.data['relations'].append(r)
        if pt is not None:
            self.pnum+=1;r.setdefault('openings',[]).append({'id':f'P{self.pnum:03}','kind':kind,'position_px':list(self.raw([pt])[0])})
        self.evidence.append({'relation_id':r['id'],'source':a,'target':b,'basis':reason,'positioned':pt is not None})
        return r
    def remove_rel(self,rid,reason):
        r=next(r for r in self.data['relations'] if r['id']==rid);self.data['relations'].remove(r)
        self.log.append({'removed_relation':r,'reason':reason})
    def region(self,name,ids):
        expanded=[]
        for i in ids:expanded+=self.groups.get(sid(i),[sid(i)])
        expanded=list(dict.fromkeys(expanded));g=unary_union([self.geo[i] for i in expanded])
        # 只跨墙厚缝隙；不会覆盖其它房间或庭院。
        g=g.buffer(6,join_style=2).buffer(-6,join_style=2)
        other=unary_union([p for i,p in self.geo.items() if i not in expanded]);g=g.difference(other)
        polys=[v for p in parts(g) for v in noholes(p)]
        self.regions.append({'id':f'Z{len(self.regions)+1:02}','name':name,'member_space_ids':expanded,
            'polygons_px':[[list(c) for c in self.raw(list(p.exterior.coords)[:-1])] for p in polys],
            'boundary_basis':'本图隔墙、交通带和成员外边界；概念近似，多片段不跨覆其它功能。'})
    def save(self,limitations):
        for i,s in self.sp.items():
            g=self.geo[i];assert g.is_valid and g.geom_type=='Polygon' and not g.interiors,(i,g.geom_type)
            s['polygon_px']=[list(p) for p in self.raw(list(g.exterior.coords)[:-1])]
        normalize(self.data);p=self.sample/'annotation.json';p.write_text(json.dumps(self.data,ensure_ascii=False,indent=2)+'\n')
        state=load_state(self.review/'review_state.json',self.data,p)
        state.update(annotation_mode='regional_coarse',regions=self.regions,
            source_limitations=limitations,incremental_changes=self.log,connectivity_evidence=self.evidence,
            historical_mapping_note='当前正式目录未见固定房名核对映射，旧说明提到的临时目录已不在；不重建或猜测旧核对号。旧S号、原文完整留存修改前备份。',
            checks={'individual_outline_reviewed':False,'region_outline_reviewed':False,'connectivity_reviewed':False,'visual_reviewed':False})
        save_state(self.review/'review_state.json',state)
        render(self.data,p,self.sample/'标注.svg',self.review/'review_state.json')
        print(self.n,'spaces',len(self.sp),'relations',len(self.data['relations']),'openings',self.pnum,'regions',len(self.regions))
