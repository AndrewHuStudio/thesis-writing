from pathlib import Path
import json,re,html,shutil,hashlib,sys
T=Path(__file__).parent;R=T.parent.parent/'标注试样/30_佛山市禅城区中心医院';p=R/'annotation.json';d=json.loads(p.read_text());sp={s['id']:s for s in d['spaces']};md=html.unescape((R/'标注说明.md').read_text())
# Parse user answers by column name, preserving all original spellings and fixed IDs.
rows=[];columns=None
for line in md.splitlines():
 if not line.startswith('|'):continue
 cells=[c.strip() for c in line.strip().strip('|').split('|')]
 if '我的确认／备注' in cells:columns={c:i for i,c in enumerate(cells)};continue
 if not columns or not re.fullmatch(r'\d{2}',cells[0]):continue
 answer=cells[columns['我的确认／备注']];sid=cells[columns['S编号']];rid=cells[columns['核对号']]
 assert rid==cells[columns['核对号（重复）']]
 assert answer and answer not in {'待确认','待填写','待定'}
 rows.append((rid,sid,answer))
assert len(rows)==31 and len({r[0] for r in rows})==31
q=md.split('### C01')[1];answer=html.unescape(re.search(r'\*\*我的确认／备注：\*\*\s*(.+)',q).group(1)).strip();assert answer=='配药室'
TYPE={'S003':'office','S004':'office','S005':'building_services','S007':'service_work_area','S008':'imaging','S009':'equipment_room','S010':'imaging','S012':'retail_service','S020':'hospital_logistics','S025':'retail_service','S031':'equipment_room','S032':'storage','S033':'office','S034':'storage','S037':'retail_service','S039':'staff_support','S044':'staff_support','S047':'imaging','S050':'office','S052':'office','S055':'office','S056':'imaging','S057':'imaging','S058':'imaging','S060':'storage','S062':'service_work_area','S064':'service_work_area','S070':'courtyard','S071':'landscape','S073':'courtyard','S083':'treatment'}
for rid,sid,name in rows:
 sp[sid].update(name=name,type=TYPE[sid])
 if sid in {'S070','S071','S073'}:sp[sid]['level']='open_space';sp[sid].pop('area_ratio',None)
sp['S084'].update(name=answer,type='medication_preparation');sp['S021']['type']='conference'
state={'name_items':[dict(review_id=rid,space_id=sid,status='confirmed',answer=name,confirmed_name=name,applied=True) for rid,sid,name in sorted(rows)],'additional_name_confirmations':[dict(review_id='C01',space_id='S084',status='confirmed',answer=answer,confirmed_name=answer,applied=True)],'connectivity_items':[],'checks':{'connectivity_reviewed':False,'visual_reviewed':False},'source':'用户填写的标注说明.md，修改前全文及四文件已备份。'}
# Current edges are direct accessible interfaces; room-level preparation nodes are not bypassed.
rs={r['id']:r for r in d['relations']};changes=[]
def retarget(rid,target,pos=None):
 r=rs[rid];before=json.loads(json.dumps(r));r['target']=target
 if pos:r['openings'][0]['position_px']=list(pos)
 changes.append({'action':'retarget','before':before,'after':r})
retarget('R013','S035',(1601,800));retarget('R014','S035',(1467,800))
retarget('R042','S022');retarget('R065','S006');retarget('R066','S013');retarget('R082','S016')
for rid in ['R032','R112']:
 changes.append({'action':'retire','before':rs[rid]});d['relations'].remove(rs[rid]);del rs[rid]
new=[('R126','S024','S002'),('R127','S041','S002'),('R128','S054','S002'),('R129','S040','S016'),('R130','S059','S068'),('R131','S085','S075')]
for rid,a,b in new:
 r=dict(id=rid,source=a,target=b,type='access');rs[rid]=r;d['relations'].append(r);changes.append({'action':'add','after':r})
# Source-read centers only; existing IDs remain stable, newly read doors start after P076.
loc=[('R028','door',(1337,1267)),('R051','door',(1778,857)),('R052','door',(1778,886)),('R053','door',(1778,962)),('R060','door',(1778,1685)),('R061','door',(1778,1711)),('R062','door',(1778,1881)),('R065','door',(913,585)),('R066','door',(803,772)),('R067','door',(803,700)),('R068','door',(913,700)),('R069','door',(929,818)),('R082','open_passage',(1085,1514)),('R101','door',(1479,1495)),('R126','door',(1728,614)),('R127','door',(1728,850)),('R128','door',(1728,1063)),('R129','door',(1203,875)),('R130','door',(803,1573))]
nextp=77
for rid,kind,pos in loc:
 assert not rs[rid].get('openings'),rid
 rs[rid]['openings']=[dict(id=f'P{nextp:03d}',kind=kind,position_px=list(pos))];nextp+=1
# Clearly drawn exterior interfaces are independent entrance relations, never an outdoor hub.
entrances=[('E006','候药大厅外门','S096',(1728,2153)),('E007','医护走廊东端外门','S076',(1755,2060)),('E008','医护办公区北端交通核外门','S023',(2158,637)),('E009','医护办公区西楼梯外门','S051',(1861,1104))]
for eid,name,target,pos in entrances:d['relations'].append(dict(id=eid,source=None,target=target,type='entrance',name=name,entrance_type='secondary',position_px=list(pos)))
state['layout_inferences']=[{'source':'S073','target':'S072','basis':'景观庭院内步道、台阶接入庭院通廊；只记概念连接，不编内部门位。'},{'source':'S085','target':'S075','basis':'护士站U形柜台内侧向输液大厅敞开，人员从开放侧进入；与面向大厅的service并存，不以柜台窗口推断穿行。'},{'source':'S071','basis':'用户确认景观平台，图面位于水景庭院内，归景观开放空间，不计室内面积。'}]
state['not_required_details']=['交通核内部电梯、楼梯与小前室不再拆分；外部门与走道连接按整体节点记录。','导医问询台内工作人员的小门未清晰显示，保留服务关系，不为使图全连通补access。','大厅分段为同一开放大厅的标注分区，连续边保留概念access，不以分区线制造门洞。','水景庭院与水景节点不强求可达；未记连接不作为确认不连接。']
p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');(T/'review_state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n');(T/'关系变更记录.json').write_text(json.dumps({'changes':changes,'new_doors':loc,'entrances':entrances},ensure_ascii=False,indent=2)+'\n')
shutil.copy2(R/'标注说明.md',T/'已填写名称确认原文.md')
print('names applied',len(rows)+1,'spaces',len(sp),'relations',len(d['relations']),'openings',sum(len(r.get('openings',[])) for r in d['relations']))
