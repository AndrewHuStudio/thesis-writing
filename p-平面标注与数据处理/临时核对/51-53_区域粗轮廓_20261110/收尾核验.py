from pathlib import Path
import json,hashlib,subprocess,sys
from shapely.geometry import Polygon,Point
from 本轮工具 import BASE,OUT

notes={51:'仅综合楼完整首层，下沿另一层残片不纳入。图例30“采光天井”已排除室内面积。',
       52:'仅完整首层及道路另一侧设备与后勤用房。S014、S019、S020继续unknown；药房概念分界及服务窗口不等于实墙或人员通行。',
       53:'仅二层，E编号表示本层边界接口。S038、S082、S085、S122的屋面／室内外属性仍不明确，保留unknown；当前面积比例依这些粗范围计算，不能作为已确认的室内面积真值。'}

for n in [51,52,53]:
    sample=next((BASE/'标注试样').glob(f'{n}_*'));q=OUT/sample.name;p=sample/'annotation.json'
    d=json.loads(p.read_text());st=json.loads((q/'review_state.json').read_text())
    sp={s['id']:Polygon(s['polygon_px']) for s in d['spaces']};old=json.loads((q/'修改前备份/annotation.json').read_text())
    overlaps=[(a,b,pa.intersection(pb).area) for a,pa in sp.items() for b,pb in sp.items() if a<b and pa.intersection(pb).area>1]
    gaps=[(r['id'],r['source'],r['target'],sp[r['source']].distance(sp[r['target']])) for r in d['relations'] if r['type']=='access' and sp[r['source']].distance(sp[r['target']])>25]
    badpoints=[(v['id'],r['id']) for r in d['relations'] for v in r.get('openings',[]) if max(sp[r[k]].boundary.distance(Point(v['position_px'])) for k in ['source','target'])>20]
    missing=sorted({s['id'] for s in old['spaces']}-set(sp))
    image_hash=hashlib.sha256((sample/d['image']['file']).read_bytes()).hexdigest()
    unchanged=image_hash==hashlib.sha256((q/'修改前备份'/d['image']['file']).read_bytes()).hexdigest()
    members={i for z in st['regions'] for i in z['member_space_ids']}
    ratio=sum(s.get('area_ratio',0) for s in d['spaces'])
    audit={'overlaps':overlaps,'access_pair_gaps':gaps,'opening_endpoint_errors':badpoints,
       'missing_old_ids':missing,'source_hash_unchanged':unchanged,'unassigned_region_members':sorted(set(sp)-members),
       'area_ratio_sum':ratio,'source_sha256':image_hash}
    assert not overlaps and not gaps and not badpoints and not missing and unchanged and members==set(sp)
    assert abs(ratio-1)<.00001
    (q/'几何与端点审计.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
    st['checks']={'individual_outline_reviewed':True,'region_outline_reviewed':True,
       'connectivity_reviewed':True,'visual_reviewed':True}
    st['visual_review_evidence']={'date':'2026-11-10','full_image':'正式SVG全图.png',
       'dense_crops':sorted(x.name for x in q.glob('正式SVG局部*.png')),
       'reviewed_items':['本图原图全图与放大局部','独立空间及区域外框','房内稳定S号与名称','P红点坐标和两端空间','E边界接口','无明显空间重叠及漏框']}
    st['non_target_details']='缺名、管井/设备小间内部开门、交通核内部路径及未知屋面通行不逐项追问；不代表确认不相通。'
    st['name_items']=[]
    st['unknown_space_ids']=[s['id'] for s in d['spaces'] if s['type']=='unknown']
    (q/'review_state.json').write_text(json.dumps(st,ensure_ascii=False,indent=2)+'\n')
    openings=sum(len(r.get('openings',[])) for r in d['relations'])
    located=sum(bool(r.get('openings')) for r in d['relations'] if r['type']=='access')
    concepts=sum(not r.get('openings') for r in d['relations'] if r['type']=='access')
    (sample/'标注说明.md').write_text('# 标注说明\n\n<!-- annotation:summary:start -->\n'
       '**状态：**本轮逐空间粗轮廓＋区域概览完成；具体房名未全部识别。\n\n'
       f'**规模：**{len(sp)}个空间／单元，{len(st["regions"])}个区域外框，{len(d["relations"])}条关系。'
       f'{openings}个定位门洞／开口，对应{located}条access；另有{concepts}条无定位概念access。\n\n'
       f'[原图]({d["image"]["file"]}) · [标注图](标注.svg) · [结构化数据](annotation.json)\n'
       '<!-- annotation:summary:end -->\n\n'
       f'**缺失信息：**{len(st["unknown_space_ids"])}个单元保留unknown，原图缺名不列为必答题。'
       ' `names_complete=false`，`full_semantics_complete=false`。\n\n'
       f'**范围：**{notes[n]}\n\n'
       '粗轮廓为概念近似。区域外框不重复计面积，未记录关系不表示不连通。'
       '原图、旧编号和旧说明已保留，修改前备份及核对记录存于正式样本目录外的临时核对目录。\n')
    cmd=[sys.executable,'/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts/annotation_tools.py',
       'validate',str(p),'--review-state',str(q/'review_state.json'),'--check-dir']
    result=subprocess.run(cmd,capture_output=True,text=True)
    (q/'正式校验.json').write_text(result.stdout)
    print(n,'exit',result.returncode,result.stdout,result.stderr)
    assert result.returncode==0
    val=json.loads(result.stdout)
    assert val['valid'] and val['complete'] and not val['names_complete'] and not val['full_semantics_complete']
    hashes={x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in sample.iterdir() if x.is_file()}
    assert len(hashes)==4
    (q/'交付哈希.json').write_text(json.dumps(hashes,ensure_ascii=False,indent=2)+'\n')
