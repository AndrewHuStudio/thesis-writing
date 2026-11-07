from pathlib import Path
import json,math,heapq,sys
from shapely import constrained_delaunay_triangles,STRtree
from shapely.geometry import Polygon,Point,LineString,box
from shapely.ops import unary_union
from shapely.prepared import prep
T=Path('/Users/hushili/Documents/研究-论文写作/大论文/p-平面标注与数据处理/临时核对/36_南雄市中医院医共体总院')
pending=json.loads((T/'核对号对应.json').read_text())

def finish(name,items,crop,sc,W,H,leftgs=None):
    cw=(crop[2]-crop[0])*sc;ch=(crop[3]-crop[1])*sc;ox=(W-cw)/2;oy=(H-ch)/2
    sidew=max(600,min(1040,ox-45))
    if leftgs:
        sides=[[m for m in items if m['group'][0] in leftgs],[m for m in items if m['group'][0] not in leftgs]]
    else:sides=[items[:math.ceil(len(items)/2)],items[math.ceil(len(items)/2):]]
    specs=[];cards=[]
    for side,ls in enumerate(sides):
        gap=min(140,(H-220)/max(1,len(ls)));sy=max(140,(H-gap*len(ls))/2)
        for j,m in enumerate(ls):
            y=sy+j*gap;bx=25 if side==0 else W-sidew-25
            cards.append(box(bx,y,bx+sidew,y+gap-5))
            poly=Polygon([(ox+(x-crop[0])*sc,oy+(y-crop[1])*sc) for x,y in m['shape']]);c=poly.representative_point()
            specs.append(dict(id=m['id'],start=(bx+sidew+5,y+gap*.42) if side==0 else (bx-5,y+gap*.42),anchor=(c.x,c.y)))
    partial=T/f'partial_{W}_{H}.json';paths=json.loads(partial.read_text()) if partial.exists() else {}
    domain=box(-1800,-1800,W+1800,H+1800)
    for sp in sorted(specs,key=lambda s:s['start'][1]):
        if sp['id'] in paths:continue
        start=Point(sp['start']);end=Point(sp['anchor'])
        future=[Point(q[k]).buffer(.25,quad_segs=1) for q in specs if q['id'] not in paths and q['id']!=sp['id'] for k in ['start','anchor']]
        selected=None
        for clearance,protect_cards in [(1.4,True),(.3,True),(.08,True),(.08,False)]:
            obs=[LineString(p).buffer(clearance,cap_style='round',join_style='mitre',quad_segs=1) for p in paths.values()]+future+(cards if protect_cards else [])
            free=domain.difference(unary_union(obs))
            components=list(free.geoms) if free.geom_type=='MultiPolygon' else [free]
            selected=next((p for p in components if p.covers(start) and p.covers(end)),None)
            if selected is not None:break
        if selected is None:raise RuntimeError(('no connected vector region',sp['id']))
        triangles=list(constrained_delaunay_triangles(selected).geoms)
        tree=STRtree(triangles)
        starts=[int(i) for i in tree.query(start,predicate='intersects')];ends=[int(i) for i in tree.query(end,predicate='intersects')]
        if not starts or not ends:raise RuntimeError(('triangle location',sp['id']))
        goal=ends[0];src=starts[0]
        centers=[p.centroid.coords[0] for p in triangles]
        edge_owner={};neighbors=[[] for _ in triangles];portal={}
        for i,tr in enumerate(triangles):
            pts=list(tr.exterior.coords)
            for a,b in zip(pts,pts[1:]):
                key=tuple(sorted((tuple(round(v,8) for v in a),tuple(round(v,8) for v in b))))
                if key in edge_owner:
                    j=edge_owner.pop(key);neighbors[i].append(j);neighbors[j].append(i)
                    portal[tuple(sorted((i,j)))]=((a[0]+b[0])/2,(a[1]+b[1])/2)
                else:edge_owner[key]=i
        queue=[(0,src)];dist={src:0};parent={};visited=set()
        while queue:
            _,v=heapq.heappop(queue)
            if v in visited:continue
            if v==goal:break
            visited.add(v)
            for w in neighbors[v]:
                ng=dist[v]+math.dist(centers[v],centers[w])
                if ng<dist.get(w,float('inf')):
                    dist[w]=ng;parent[w]=v
                    heapq.heappush(queue,(ng+math.dist(centers[w],centers[goal]),w))
        chain=[goal]
        while chain[-1]!=src:chain.append(parent[chain[-1]])
        chain.reverse()
        pts=[sp['start']]+[portal[tuple(sorted((a,b)))] for a,b in zip(chain,chain[1:])]+[sp['anchor']]
        prepared=prep(selected);simple=[pts[0]];i=0
        while i<len(pts)-1:
            candidate=range(len(pts)-1,i,-1)
            for j in candidate:
                if prepared.covers(LineString([pts[i],pts[j]])):
                    simple.append(pts[j]);i=j;break
            else:raise RuntimeError(('visibility path',sp['id'],i))
        result=LineString(simple)
        assert result.is_simple
        for sid,p in paths.items():
            assert not result.intersects(LineString(p)),(sp['id'],sid)
        paths[sp['id']]=simple;partial.write_text(json.dumps(paths))
        print(name,len(paths),'/',len(specs),sp['id'],'triangles',len(triangles),flush=True)
    assert len(paths)==len(specs)
    for i,(a,pa) in enumerate(paths.items()):
        for b,pb in list(paths.items())[i+1:]:assert not LineString(pa).intersects(LineString(pb)),(a,b)
    (T/(name+'_引线检查.json')).write_text(json.dumps(dict(count=len(paths),crossings=0,stats=[],paths=paths)))


if __name__ == '__main__':
    finish('36_高清核对总图',pending,(0,0,2000,1500),2.2,6600,4500,{'A','B','D','E','G'})
