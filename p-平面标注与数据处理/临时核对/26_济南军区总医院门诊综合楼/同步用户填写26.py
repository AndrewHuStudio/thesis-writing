from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from collections import Counter
import json,html,re,shutil,hashlib,sys,importlib.util
import xml.etree.ElementTree as ET
from shapely.geometry import Polygon,box
from shapely.ops import unary_union

BASE=Path(__file__).parent
ROOT=BASE.parents[1]
P=ROOT/'标注试样/26_济南军区总医院门诊综合楼'
SKILL=Path('/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts')
sys.path.insert(0,str(SKILL))
import annotation_tools as at
from review_workflow import load_state,save_state,summary

stamp=datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y%m%d_%H%M%S')
W=BASE/f'{stamp}_填写同步与定稿'
W.mkdir()
backup=W/'用户填写及四文件备份';backup.mkdir()
hashes={}
for f in P.iterdir():
    if f.is_file():
        shutil.copy2(f,backup/f.name);hashes[f.name]=hashlib.sha256(f.read_bytes()).hexdigest()
md=(P/'标注说明.md').read_text()
decoded=html.unescape(md)
before=json.loads((P/'annotation.json').read_text())
d=json.loads(json.dumps(before));ss={s['id']:s for s in d['spaces']}
rows=[]
for line in decoded.splitlines():
    if re.match(r'^\|\s*\d{2}\s*\|\s*S\d{3}\s*\|',line):
        c=[x.strip() for x in line.strip('|').split('|')]
        assert len(c)==7 and c[0]==c[6],c
        rows.append(dict(review_id=c[0],space_id=c[1],candidate=c[2],alternative=c[3],basis=c[4],answer=c[5]))
assert len(rows)==63 and len({r['space_id'] for r in rows})==63
automatic={'补图辨认已同步（非用户确认）','图面辨认已同步（非用户确认）','待确认','待填写',''}
answers={r['space_id']:r for r in rows if r['answer'] not in automatic}
expected={
 'S019':('财务科','office'), 'S020':('储藏','storage'),
 'S022':('医保调解室','office'), 'S023':('病案存储','storage'),
 'S028':('保险柜','storage'), 'S029':('病历审核','office'),
 'S034':('侧翼门厅（通往医技楼）','hall'), 'S055':('门诊检验','laboratory'),
 'S066':('X光储藏','storage'), 'S111':('诊室','consultation'),
 'S096':('办公室','office'),
}
for sid,(name,typ) in expected.items():
    assert answers[sid]['answer']==name,(sid,answers.get(sid))
    ss[sid]['name']=name;ss[sid]['type']=typ
ss['S034']['level']='open_space'
ss['S055']['scope']='ordinary_outpatient'
assert answers['S076']['answer']=='和外部房间直接合并'
assert answers['S109']['answer']=='不是一个房间，和外部的走廊合并'
merges={'S076':'S072','S109':'S083'}
bridge={'S076':box(1469,2212,1544,2219),'S109':box(1761,2488,1800,2498)}
for old,target in merges.items():
    combined=unary_union([Polygon(ss[old]['polygon_px']),Polygon(ss[target]['polygon_px']),bridge[old]])
    assert combined.geom_type=='Polygon' and not combined.interiors and combined.is_valid
    ss[target]['polygon_px']=[[round(x,4),round(y,4)] for x,y in list(combined.exterior.coords)[:-1]]
d['spaces']=[s for s in d['spaces'] if s['id'] not in merges]
removed_relations=[]
for r in d['relations']:
    for key in ['source','target']:
        if r.get(key) in merges:r[key]=merges[r[key]]
    if r.get('source')==r['target']:removed_relations.append(r)
d['relations']=[r for r in d['relations'] if r not in removed_relations]
# Read the user's K01 wording independently from the room table.
k1=decoded.split('### K01｜',1)[1].split('### K02｜',1)[0]
k1answer=k1.split('**我的确认／备注：**',1)[1].strip()
assert '094' in k1answer and '收费' in k1answer and '098厕所前室' in k1answer and '走廊连接' in k1answer
ss['S094']['name']='收费';ss['S094']['type']='registration';ss['S094']['scope']='public_service'
ss['S098']['name']='厕所前室';ss['S098']['type']='vestibule'
d['relations'].append(dict(id='R160',source='S071',target='S098',type='access'))
at.normalize(d)
for f in P.iterdir():
    if f.is_file():assert hashlib.sha256(f.read_bytes()).hexdigest()==hashes[f.name],'File changed while reading; do not overwrite.'
(P/'annotation.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
at.render(d,P/'annotation.json',P/'标注.svg')
tree=ET.parse(P/'标注.svg')
for node in tree.iter():
    if node.tag.endswith('text') and node.text and re.fullmatch(r'P\d{3,}',node.text):node.set('stroke-width','0.65')
tree.write(P/'标注.svg',encoding='utf-8',xml_declaration=True)

statepath=BASE/'review_state.json'
state=load_state(statepath,d,P/'annotation.json')
assert not state['name_items'] and not state['connectivity_items'],'Existing review state must be merged explicitly.'
state['name_items']=[];state['retired_name_items']=[]
for row in rows:
    sid=row['space_id'];rid=row['review_id']
    if sid in merges:
        state['retired_name_items'].append(dict(**row,status='merged',merged_into=merges[sid]))
        continue
    item=dict(review_id=rid,space_id=sid,basis=row['basis'])
    if sid in answers:
        item.update(status='confirmed',answer=row['answer'],confirmed_name=ss[sid]['name'],applied=True)
    else:item.update(status='resolved',confirmed_name=ss[sid]['name'],reason='原图或补图辨认；非用户确认')
    state['name_items'].append(item)
state['connectivity_items']=[
 dict(review_id='K01',source='S071',target='S098',status='confirmed_connected',answer=k1answer,
      reason='S094为独立收费；S098为厕所前室，用户明确连向外部走廊S071。门位未明确，不新增红点。'),
 dict(review_id='K02',source='S072',target='S074',status='not_required',reason='补图明确同一EICU内连续床位分块；S076已按用户填写并入S072，无剩余关键疑点。'),
 dict(review_id='K03',source='S083',target='S089',status='not_required',reason='补图已完成复核：发热门诊由S112/E007进入，未见S083—S089直接通口；不作为用户确认不连接。'),
]
state['additional_name_confirmations']=[dict(source_review='K01',space_id='S094',name='收费',answer=k1answer),dict(source_review='K01',space_id='S098',name='厕所前室',answer=k1answer)]
state['merges']=[dict(source=k,target=v,answer=answers[k]['answer'],reason='并入外侧连续空间，合并轮廓并重接关系；原核对号保留归档。') for k,v in merges.items()]
state['archive']={'user_markdown':str(backup/'标注说明.md'),'raw_format':'原始MD原样保存，包括HTML字符实体及用户全部填写','sync_folder':str(W)}
state['checks']={'connectivity_reviewed':False,'visual_reviewed':False}
state['layout_findings']=[
 dict(spaces=['S072','S074'],basis='补图2明确EICU（9床），连续床位范围，无内部隔墙。'),
 dict(spaces=['S072','S079'],basis='S076并入S072后，P105仍为EICU到缓冲区的可见门。'),
 dict(spaces=['S072','S115'],basis='P110仍为处置房到EICU的可见门，按合并结果改挂空间对。'),
 dict(spaces=['S037','S051'],basis='布局推断：服务前区与大厅开放连续；无定位红点。'),
]
state['not_required_details']='交通核内部精确路线、卫生和更衣小隔间、柜台内部逐席位组织不继续拆分；未记录关系不视为不可达。'
save_state(statepath,state)
(W/'读取用户填写.json').write_text(json.dumps(dict(name_answers=answers,k01_answer=k1answer,merge_map=merges,removed_relations=removed_relations,source_hashes_before=hashes),ensure_ascii=False,indent=2)+'\n')
# Preserve and archive the entire user-filled document before compacting after QA.
summary(d,P/'annotation.json',P/'标注说明.md',statepath)
result,code=at.check(d,P/'annotation.json',check_dir=True)
assert result['valid'] and result['names_complete'],result
(W/'结构与名称检查.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(work=str(W),spaces=len(d['spaces']),relations=len(d['relations']),openings=sum(len(r.get('openings',[])) for r in d['relations']),explicit_names=len(expected)+2,merged=merges,valid=result['valid'],names_complete=result['names_complete']),ensure_ascii=False))
