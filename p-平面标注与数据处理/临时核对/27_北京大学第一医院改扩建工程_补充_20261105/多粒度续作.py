from pathlib import Path
import json,copy,sys,xml.etree.ElementTree as ET,hashlib,re
import pymupdf
B=Path(__file__).resolve().parent;ROOT=B.parent.parent/'标注试样/27_北京大学第一医院改扩建工程';SCRIPTS=Path('/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts')
sys.path.insert(0,str(SCRIPTS));import annotation_tools as at;import review_workflow as rw
p=ROOT/'annotation.json';d=json.loads(p.read_text());old_md=(ROOT/'标注说明.md').read_text();mapping=json.loads((B/'固定核对映射.json').read_text());W=d['image']['width'];H=d['image']['height']
# 使用本轮续作前归档，避免从历史更早草稿重建或重排编号。
if (B/'多粒度判读记录.json').exists():raise RuntimeError('本轮已应用；请读取最新填写，不要重复覆盖。')
for line in old_md.splitlines():
 if re.match(r'\| \d{2} \| S\d{3}',line):
  cells=[x.strip() for x in line.split('|')[1:-1]]
  if cells[5] not in {'待确认','待填写','待定',''}:raise RuntimeError('发现新增填写，须先同步再继续：'+line)
for s in d['spaces']:
 if s['id'] in {'S047','S049'}:s.update(name='信息中心',type='office')
# 南侧凹入入口空间的两侧门连接大厅；外端只记一个入口，不重造两侧门的P号。
assert not any(r['id']=='E002' for r in d['relations'])
d['relations'].append(dict(id='E002',source=None,target='S025',type='entrance',name='南侧入口',entrance_type='pedestrian',position_px=[W-1-1420,1384]))
at.normalize(d);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
state={'name_items':[], 'connectivity_items':[
 {'review_id':'K01','source':'S025','target':'S022','status':'not_required','reason':'助手按完整通行布局复核：南侧外端经E002接入S025，两侧原门分别通向S022/S024。无额外假门位；不是用户已确认。','resolution_source':'assistant_layout_inference','entrance_id':'E002','related_spaces':['S022','S024','S025']},
 {'review_id':'K02','source':'S015','target':'S018','status':'pending','reason':'西侧狭长空间的唯一入口未辨明，R014保持撤下；也可能连接S013/S014或属于不同范围。'}],
 'checks':{'connectivity_reviewed':True,'visual_reviewed':False},
 'research_context':{'granularity':'mixed','user_direction':'同时接纳房间级和粗功能空间级数据；不补造内部房间','gcn_note':'../../../m-GCN模型/多粒度GCN训练思路.md'},
 'layout_inferences':[{'relations':['R013','R024','R028','R027'],'basis':'公共带、整体交通核及两个大厅的开放连续，沿用上一轮判读。'},{'entrance_id':'E002','basis':'南侧入口凹入空间两侧为大厅门组，外端作为一个建筑入口；位置为接口近似点，不是新增室内门洞。'}],
 'not_investigated':['S031','S034','S045','S050','S052']}
for m in mapping:
 item={'review_id':m['check'],'space_id':m['id'],'status':'pending','candidate':m['candidate'],'alternative':m['alternative'],'reason':m['basis'],'confidence':m['confidence']}
 if m['id'] in {'S047','S049'}:item.update(status='resolved',confirmed_name='信息中心',resolution_source='图面判读：本图图例5=信息中心，圈⑤仍为5；不作为用户确认。')
 state['name_items'].append(item)
rw.save_state(B/'review_state.json',state);state=rw.load_state(B/'review_state.json',d,p);rw.save_state(B/'review_state.json',state)
# 归档整份旧MD后，只保留简短概览和未完成填写；已辨认行保留原号与判断来源。
archive=B/'archive';archive.mkdir(exist_ok=True);(archive/'20261105_多粒度续作前_标注说明.md').write_text(old_md)
body=old_md.split('### 01｜',1)[1].split('## 关键连通疑点：',1)[0];body='### 01｜'+body
for rid,sid in [('19','S047'),('21','S049')]:
 pattern=r'(?m)^\| '+rid+r' \| '+sid+r' \|.*$'
 line='| '+rid+' | '+sid+' | 信息中心 | — | 本图图例5=信息中心，圈⑤按同一图例判读。 | 图面已辨认，非用户确认 | '+rid+' |'
 body=re.sub(pattern,lambda m:line,body)
k02=old_md.split('### K02｜',1)[1].split('## 当前完成状态',1)[0];k02='### K02｜'+k02
md='''# 27 北京大学第一医院改扩建工程｜混合粒度标注草稿

仅标注转正后上方完整的门诊楼一层；下方裁切平面不纳入。保留原图坐标与稳定S/P编号，按图面同时记录房间、明确功能空间和整体交通核。

<!-- annotation:summary:start -->
<!-- annotation:summary:end -->

当前还有22项名称和K02待确认。19、21已按本图图例辨认为信息中心；K01按布局判读完成，南侧E002接入S025，不重复计算两侧门。判读依据和历史材料已归档到正式目录外。

## 名称核对

沿用01—24原核对号；可改“预估名称（可改）”，再在“我的确认／备注”填“已确认”，或直接填写实际名称。19、21保留本轮已辨认记录，其余未填写项不视为确认。

![原固定编号总图；19、21本轮已辨认](../../临时核对/27_北京大学第一医院改扩建工程_补充_20261105/27_完整核对总图.png)

'''+body.strip()+'\n\n## 关键连通疑点\n\n'+k02.strip()+'\n'
(ROOT/'标注说明.md').write_text(md)
at.summary(d,ROOT/'标注说明.md',p,B/'review_state.json')
# SVG转正展示；圈点的原始像素坐标及编号保留，显示变换显式写入。
u=copy.deepcopy(d);u['image'].update(width=H,height=W)
for s in u['spaces']:s['polygon_px']=[[y,W-1-x] for x,y in s['polygon_px']]
for r in u['relations']:
 if 'position_px' in r:r['position_px']=[r['position_px'][1],W-1-r['position_px'][0]]
 for o in r.get('openings',[]):o['position_px']=[o['position_px'][1],W-1-o['position_px'][0]]
at.render(u,p,ROOT/'标注.svg');ns='{http://www.w3.org/2000/svg}';tree=ET.parse(ROOT/'标注.svg');rt=tree.getroot();im=rt.find('.//'+ns+'image');im.set('width',str(W));im.set('height',str(H));im.set('transform',f'matrix(0 -1 1 0 0 {W-1})')
for r in d['relations']:
 for o in r.get('openings',[]):
  og=rt.find('.//'+ns+'g[@data-opening-id="'+o['id']+'"]');c=og.find(ns+'circle');c.set('cx',str(o['position_px'][0]));c.set('cy',str(o['position_px'][1]));c.set('transform',f'matrix(0 -1 1 0 0 {W-1})');label=og.find(ns+'text')
  for key in ['stroke','stroke-width','paint-order']:label.attrib.pop(key,None)
  label.set('font-size','8');x=float(label.get('x'));y=float(label.get('y'));og.insert(list(og).index(label),at.element('rect',{'x':x-1,'y':y-8,'width':24,'height':10,'fill':'white','fill-opacity':'.9','rx':1}))
rt.findall(ns+'text')[0].text='27 北京大学第一医院改扩建工程｜混合粒度标注草稿'
for eid,bx,by in [('E004',2495,450),('E006',2235,465)]:
 eg=rt.find('.//'+ns+'g[@id="'+eid+'"]');rect=eg.find(ns+'rect');label=eg.find(ns+'text');line=eg.find(ns+'line');rect.set('x',str(bx));rect.set('y',str(by));label.set('x',str(bx+7));label.set('y',str(by+18));line.set('x2',str(bx+float(rect.get('width'))/2));line.set('y2',str(by+float(rect.get('height'))/2))
rt.find(ns+'g').append(at.txt(120,1780,'下方裁切平面不纳入本次标注。',24,'#64748b',True));tree.write(ROOT/'标注.svg',encoding='unicode')
doc=pymupdf.open(ROOT/'标注.svg');page=doc[0]
for name,clip,scale in [('全图',None,.8),('西翼',pymupdf.Rect(100,630,1120,1540),1.5),('东翼',pymupdf.Rect(2020,620,2700,1550),1.5),('南侧入口',pymupdf.Rect(1160,1300,1600,1630),2)]:
 page.get_pixmap(matrix=pymupdf.Matrix(scale,scale),clip=clip,alpha=False).save(B/f'多粒度续作_{name}_检查.png')
record={'date':'2026-11-05','resolved_names':['19 S047 信息中心','21 S049 信息中心'],'resolved_connectivity':['K01：助手布局判读，恢复E002'],'pending_names':22,'pending_connectivity':['K02'],'core_fields_unchanged':True,'no_new_interior_door_points':True,'source':'图例与入口布局自主复核，非用户逐项确认'}
(B/'多粒度判读记录.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n');print(json.dumps(record,ensure_ascii=False,indent=2))
