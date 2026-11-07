from pathlib import Path
import json, shutil, html, re
from shapely.geometry import Polygon

BASE=Path('/Users/hushili/Documents/研究-论文写作/大论文/p-平面标注与数据处理')
SAMPLE=BASE/'标注试样/35_阳春京伦妇产医院'
REVIEW=BASE/'临时核对/31-35_名称核对_20261106/35_阳春京伦妇产医院'
OUT=REVIEW/'20261107_填写同步与连通验收'
BACKUP=OUT/'用户填写及四文件备份'
BACKUP.mkdir(exist_ok=True)
for f in list(SAMPLE.iterdir())+[REVIEW/'review_state.json',REVIEW/'固定核对映射.json']:
    if f.is_file() and not (BACKUP/f.name).exists():
        shutil.copy2(f,BACKUP/f.name)
raw=(SAMPLE/'标注说明.md').read_text()
md=html.unescape(raw)
rows=[]
for line in md.splitlines():
    if not line.startswith('|'):
        continue
    cells=[s.strip() for s in line.strip().strip('|').split('|')]
    if len(cells)==7 and re.fullmatch(r'0[1-7]',cells[0]):
        assert cells[0]==cells[6]
        rows.append({'review_id':cells[0],'space_id':cells[1],'estimate':cells[2],'answer':cells[5]})
assert len(rows)==7 and len({x['space_id'] for x in rows})==7
kanswers={}
for k in ['K01','K02']:
    section=md.split('### '+k,1)[1].split('### ',1)[0]
    match=re.search(r'\*\*我的确认／备注：\*\*(.*)',section)
    assert match
    kanswers[k]=match.group(1).strip()
assert kanswers['K01']=='只经S076进入'
assert '合并' in kanswers['K02'] and 'S042与S043' in kanswers['K02']
expected={'01':'休息室，外面的大厅连接在一起','02':'露天庭院','03':'大厅的一部分','04':'医护休息室','05':'库房','06':'库房','07':'清洁间'}
assert {r['review_id']:r['answer'] for r in rows}==expected
(OUT/'本轮读取的用户确认.json').write_text(json.dumps({'name_rows':rows,'connectivity_answers':kanswers},ensure_ascii=False,indent=2)+'\n')
d=json.loads((SAMPLE/'annotation.json').read_text())
state=json.loads((REVIEW/'review_state.json').read_text())
ss={s['id']:s for s in d['spaces']}
updates={
'S004':('休息室','service','semi_open_space','public_service'),
'S017':('露天庭院','courtyard','open_space','public_service'),
'S042':('大厅的一部分','hall','open_space','public_service'),
'S058':('医护休息室','staff_support','room','staff_support'),
'S073':('库房','storage','functional_block','hospital_logistics'),
'S074':('库房','storage','room','hospital_logistics'),
'S081':('清洁间','staff_support','room','public_service')}
for sid,(name,typ,level,scope) in updates.items():
    ss[sid].update(name=name,type=typ,level=level,scope=scope)
ss['S017'].pop('area_ratio',None)
union=Polygon(ss['S042']['polygon_px']).union(Polygon(ss['S043']['polygon_px']))
assert union.geom_type=='Polygon' and not union.interiors
ss['S042']['polygon_px']=[list(x) for x in list(union.exterior.coords)[:-1]]
retired=dict(ss['S043'])
d['spaces']=[s for s in d['spaces'] if s['id']!='S043']
remapped=[]
for r in d['relations']:
    for field in ['source','target']:
        if r.get(field)=='S043':
            remapped.append({'relation_id':r['id'],'field':field,'before':'S043','after':'S042'})
            r[field]='S042'
assert not any(r.get('source')==r['target'] for r in d['relations'])
# 休息室保留独立功能节点；用户确认其向外部公共通道连续，无可定位的新门洞。
assert not any(r['type']=='access' and {r['source'],r['target']}=={'S004','S007'} for r in d['relations'])
d['relations'].append({'id':'R132','source':'S004','target':'S007','type':'access'})
# 固定核对号与用户原话保存到外部记录，不进入核心JSON。
for item,row in zip(state['name_items'],rows):
    assert item['review_id']==row['review_id'] and item['space_id']==row['space_id']
    item.update(status='confirmed',answer=row['answer'],confirmed_name=ss[row['space_id']]['name'],applied=True)
for item in state['connectivity_items']:
    rid=item['review_id']
    item['answer']=kanswers[rid]
    if rid=='K01':
        item.update(status='confirmed_disconnected',reason='用户确认S072仅经S076进入；S075—S072无直接access。')
    else:
        item['history']=[{'source':item['source'],'target':item['target'],'question':item['question'],'status':item['status']}]
        item.update(target='S044',status='not_required',reason='用户要求将S043合并入S042；原S042—S043边界已退出，当前引用S042—S044保留既有对外双门R052/P036。',resolution='merged',retired_space_id='S043',surviving_space_id='S042')
state['space_merges']=state.get('space_merges',[])+[{'retired_space_id':'S043','surviving_space_id':'S042','answer':kanswers['K02'],'retired_space':retired,'relation_remaps':remapped}]
state['confirmed_continuity']=[{'source':'S004','target':'S007','relation_id':'R132','answer':expected['01'],'reason':'休息室与外部公共通道连续；仅新增概念关系，保留原S004—S006连续连接。'}]
state['checks']={'connectivity_reviewed':False,'visual_reviewed':False}
state['review_date']='2026-11-07'
# 删除外部当前引用中的已并入编号，历史/原图记录保留原样。
for item in state['layout_inferences']:
    if {item['source'],item['target']}=={'S072','S076'}:
        item['reason']='用户在K01确认S072只经S076进入，概念连接已同步；无清晰门位，不产生红点。'
state['opening_audit_file']='20261107_填写同步与连通验收/连通性测试结果.json'
(SAMPLE/'annotation.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
(REVIEW/'review_state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
mapping=json.loads((REVIEW/'固定核对映射.json').read_text())
for row in mapping:
    if row['id'] in updates:
        row['confirmed_name']=ss[row['id']]['name']
        row['answer']=expected[row['number']]
    if row['id']=='S042':
        row['original_polygon_px']=row['polygon_px'];row['polygon_px']=ss['S042']['polygon_px'];row['merged_from']=['S043']
(REVIEW/'固定核对映射.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'names_applied':len(rows),'merge':'S043 -> S042','new_conceptual_access':'R132 S004-S007','spaces':len(d['spaces']),'relations':len(d['relations'])},ensure_ascii=False))
