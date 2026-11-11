"""41—45 本轮有图面证据的增量标注；所有坐标均为各自原图坐标。"""
from pathlib import Path
import sys,json,hashlib,copy
from shapely.geometry import Polygon,box,Point
from shapely.ops import unary_union
sys.path.insert(0,'/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts')
from review_workflow import load_state,sync_names,save_state
from annotation_tools import normalize,render
BASE=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent

def run(n,cfg):
    sample=next((BASE/'标注试样').glob(n+'_*'))
    review=OUT/sample.name
    data=json.loads((review/'修改前备份/annotation.json').read_text())
    spaces={s['id']:s for s in data['spaces']}
    log=[]
    def sid(v):return f'S{int(v):03}'
    for i,fields in cfg.get('update_spaces',{}).items():
        spaces[sid(i)].update(fields)
        log.append({'space':sid(i),'updated_fields':list(fields)})
    for fields in cfg.get('new_spaces',[]):
        fields=copy.deepcopy(fields)
        fields.setdefault('name','名称未确认');fields.setdefault('type','unknown')
        fields.setdefault('level','room')
        if 'rect' in fields:fields['polygon_px']=list(map(list,box(*fields.pop('rect')).exterior.coords))[:-1]
        assert fields['id'] not in spaces
        spaces[fields['id']]=fields;data['spaces'].append(fields)
        log.append({'new_space':fields['id']})
    for i,rect in cfg.get('subtract',[]):
        s=spaces[sid(i)];g=Polygon(s['polygon_px']).difference(box(*rect))
        assert g.geom_type=='Polygon' and not g.interiors
        s['polygon_px']=[list(p) for p in list(g.exterior.coords)[:-1]]
    for i,rect in cfg.get('extend',[]):
        s=spaces[sid(i)];g=Polygon(s['polygon_px']).union(box(*rect))
        assert g.geom_type=='Polygon' and not g.interiors
        s['polygon_px']=[list(p) for p in list(g.exterior.coords)[:-1]]
    rels={r['id']:r for r in data['relations']}
    for i,fields in cfg.get('update_relations',{}).items():
        rels[f'R{int(i):03}'].update(fields)
        log.append({'relation':f'R{int(i):03}','update':fields})
    for i,reason in cfg.get('remove_relations',{}).items():
        r=rels.pop(f'R{int(i):03}');data['relations'].remove(r)
        log.append({'removed_relation':r,'reason':reason})
    count=max((int(r['id'][1:]) for r in data['relations'] if r['id'].startswith('R')),default=0)
    for a,b,kind,reason in cfg.get('new_relations',[]):
        assert not any(r['type']==kind and {r['source'],r['target']}=={sid(a),sid(b)} for r in data['relations'])
        count+=1;r={'id':f'R{count:03}','source':sid(a),'target':sid(b),'type':kind}
        data['relations'].append(r);rels[r['id']]=r
        log.append({'new_relation':r['id'],'source':sid(a),'target':sid(b),'evidence':reason})
    pnum=0
    for rid,points in cfg.get('doors',{}).items():
        r=rels[f'R{int(rid):03}'];assert r['type']=='access'
        if isinstance(points[0],(int,float)):points=[points]
        for pt in points:
            kind='door'
            if len(pt)==3:pt,kind=pt[:2],pt[2]
            pnum+=1;r.setdefault('openings',[]).append({'id':f'P{pnum:03}','kind':kind,'position_px':pt})
    normalize(data)
    (sample/'annotation.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    state_path=review/'review_state.json'
    state=load_state(state_path,data,sample/'annotation.json')
    state['annotation_mode']='regional_coarse'
    if not state['name_items']:
        old=json.loads((review/'修改前备份/annotation.json').read_text())
        old_unknown=[s for s in old['spaces'] if s['type']=='unknown']
        state['name_items']=[{'review_id':f'{k:02}','space_id':s['id'],'status':'pending',
           'reason':'原图无可靠专门房名；沿用旧草稿顺序，候选原文保存于修改前备份。'} for k,s in enumerate(old_unknown,1)]
    sync_names(state,data)
    regions=[]
    for name,ids in cfg['regions']:
        ids=[sid(i) for i in ids]
        # 小间隙只连接墙厚，不跨越未标注的大厅或图外空白。
        g=unary_union([Polygon(spaces[i]['polygon_px']) for i in ids])
        parts=[g] if g.geom_type=='Polygon' else list(g.geoms)
        # 使用各成员并集的实际外边界；有内洞时按房间片段保存以免跨覆相邻功能。
        polys=[]
        for part in parts:
            if part.interiors:
                polys.extend([spaces[i]['polygon_px'] for i in ids if Polygon(spaces[i]['polygon_px']).intersects(part)])
            else:polys.append([list(p) for p in list(part.exterior.coords)[:-1]])
        regions.append({'id':f'Z{len(regions)+1:02}','name':name,'member_space_ids':ids,
            'polygons_px':polys,'boundary_basis':'本图已复核成员范围的并集；概念外轮廓，不另计面积。'})
    state['regions']=regions
    state['checks']={'individual_outline_reviewed':False,'region_outline_reviewed':False,
                     'connectivity_reviewed':False,'visual_reviewed':False}
    state['source_limitations']=cfg.get('limitations',[])
    state['incremental_changes']=log
    state['review_basis']='2026-11-08逐图原图总览、原图密集局部和现有编号图实查；本轮区域级概念精度。'
    state['connectivity_inferences']=[{'relation_id':r['id'],'source':r['source'],'target':r['target'],
        'reason':'现有概念关系经本图交通组织复核；不定位无法辨明的门位。'}
        for r in data['relations'] if r['type']=='access' and not r.get('openings')]
    save_state(state_path,state)
    render(data,sample/'annotation.json',sample/'标注.svg',state_path)
    print(n,len(data['spaces']),len(data['relations']),pnum,len(regions))

if __name__=='__main__':
    n=sys.argv[1];cfg=json.loads((OUT/f'配置{n}.json').read_text());run(n,cfg)
