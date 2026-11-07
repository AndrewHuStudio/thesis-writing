from pathlib import Path
import json,html,re,shutil,sys,subprocess,copy,xml.etree.ElementTree as ET
BASE=Path('/Users/hushili/Documents/研究-论文写作/大论文/p-平面标注与数据处理')
P=BASE/'标注试样/32_青岛大学附属医院东区病房综合楼'
R=BASE/'临时核对/31-35_名称核对_20261106/32_青岛大学附属医院东区病房综合楼'
W=R/'20261107_最终确认同步';W.mkdir(exist_ok=False)
b=W/'同步前备份';b.mkdir()
for f in P.iterdir():shutil.copy2(f,b/f.name)
for n in ['review_state.json','固定核对映射.json']:shutil.copy2(R/n,b/n)
shutil.copy2(Path(__file__),W/Path(__file__).name)
raw=(P/'标注说明.md').read_text();md=html.unescape(raw)
row=next(x for x in md.splitlines() if re.match(r'^\|\s*33\s*\|',x));cols=[x.strip() for x in row.strip('|').split('|')];assert cols[1]=='S053' and cols[5]=='更衣'
assert '**我的确认／备注：是的就这么写**' in md
assert re.search(r'我的确认／备注：\*\*直接连到s105',md,re.I)
d=json.loads((P/'annotation.json').read_text());state=json.loads((R/'review_state.json').read_text());items={i['review_id']:i for i in state['name_items']};spaces={s['id']:s for s in d['spaces']}
for rid,sid,name,typ,scope in [('20','S038','卫生间','toilet','public_service'),('21','S039','MIR','imaging','ordinary_outpatient'),('22','S040','MIR','imaging','ordinary_outpatient'),('33','S053','更衣','staff_support','ordinary_outpatient')]:
 s=spaces[sid];assert s['type']=='unknown';s.update(name=name,type=typ,level='room',scope=scope)
 i=items[rid];i.setdefault('history',[]).append({k:i[k] for k in ['status','held_answer','reason'] if k in i})
 for k in ['held_answer','reason']:i.pop(k,None)
 i.update(status='confirmed',confirmed_name=name,applied=True,answer='更衣' if rid=='33' else '是的就这么写',source='标注说明.md 最新填写 2026-11-07')
 if rid!='33':i['original_answer']=name
k=next(i for i in state['connectivity_items'] if i['review_id']=='K01');k.setdefault('history',[]).append({'status':k['status'],'reason':k['reason']});k.update(status='confirmed_connected',answer='直接连到s105',source='S084',target='S105',reason='用户确认电梯直接连到S105；门位未定位，保留无openings的概念连接。')
assert not any(r['type']=='access' and {r['source'],r['target']}=={'S084','S105'} for r in d['relations'])
new_id=f'R{max(int(r["id"][1:]) for r in d["relations"] if r["id"].startswith("R"))+1:03}'
d['relations'].append({'id':new_id,'source':'S084','target':'S105','type':'access'})
state['checks']['visual_reviewed']=False
state['scope_notes']=['主要功能空间与主通行组织已逐区复核；K01已按用户确认同步','中庭保留独立节点；未记关系不表示不相通或负样本','小间内部细节未穷尽，见外部人工记录']
(P/'annotation.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');(R/'review_state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
m=json.loads((R/'固定核对映射.json').read_text())
for i in m:
 if i['number'] in {'20','21','22','33'}:i.update(current_name=spaces[i['id']]['name'],confirmation_source='标注说明.md 最新填写 2026-11-07')
(R/'固定核对映射.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
(W/'最终确认读取.json').write_text(json.dumps({'33':'更衣','20-22':'是的就这么写','correspondence':{'20/S038':'卫生间','21/S039':'MIR','22/S040':'MIR'},'K01':'直接连到s105','new_access':new_id,'source_markdown':raw},ensure_ascii=False,indent=2)+'\n')
t='/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts/annotation_tools.py'
for args in [['normalize',str(P/'annotation.json')],['render',str(P/'annotation.json'),'--output',str(P/'标注.svg')],['summary',str(P/'annotation.json'),'--output',str(P/'标注说明.md'),'--review-state',str(R/'review_state.json'),'--compact']]:
 z=subprocess.run([sys.executable,t]+args,capture_output=True,text=True);print(z.returncode,z.stdout.strip());assert z.returncode==0
# 保持P号可读，同时保留SVG与xlink命名空间，避免栅格预览丢失底图。
ET.register_namespace('','http://www.w3.org/2000/svg');ET.register_namespace('xlink','http://www.w3.org/1999/xlink')
tree=ET.parse(P/'标注.svg');ns='{http://www.w3.org/2000/svg}'
for g in tree.iter(ns+'g'):
 if g.get('data-opening-id'):
  for node in list(g):
   if node.tag==ns+'text' and node.get('stroke')=='white':
    fg=copy.deepcopy(node)
    for attr in ['stroke','stroke-width','paint-order']:fg.attrib.pop(attr,None)
    g.append(fg)
tree.write(P/'标注.svg',encoding='unicode')
print('四个房名与K01已同步；新增',new_id,'；MIR原文保留。')
