from pathlib import Path
import json
from shapely.geometry import box
from shapely.ops import transform
base=Path('/Users/hushili/Documents/研究-论文写作/大论文/p-平面标注与数据处理');root=base/'标注试样/29_内蒙古自治区国际蒙医医院扩建项目';w=base/'临时核对/29_内蒙古自治区国际蒙医医院扩建项目';run=Path((w/'当前续作目录.txt').read_text().strip());d=json.loads((root/'annotation.json').read_text());by={s['id']:s for s in d['spaces']};audit=[]
# Four visible doors are inside the imaging-room control strip, rather than on the direct S066 interface.
withdrawn=[]
for r in d['relations']:
 if {r['source'],r['target']} in [{'S061','S066'},{'S060','S066'},{'S059','S066'},{'S054','S066'}]:
  withdrawn+=r.pop('openings',[])
# Missing gray foyer adjoining the emergency toilet group.
g=transform(lambda x,y,z=None:(2444-y,x),box(1902,1262,1932,1330))
s=dict(id='S222',name='急诊卫生间前通道',type='corridor',level='open_space',scope='emergency',polygon_px=[[x,y] for x,y in list(g.exterior.coords)[:-1]]);d['spaces'].append(s);by[s['id']]=s
rnum=max(int(r['id'][1:]) for r in d['relations'] if r['id'].startswith('R'));pnum=max(int(p['id'][1:]) for r in d['relations'] for p in r.get('openings',[]));existing={(r['type'],frozenset((r['source'],r['target']))):r for r in d['relations'] if r['type']!='entrance'}
def add(a,b,uv=None,kind='access',reason='图面公共通行区连续；不是实体隔墙。'):
 global rnum,pnum
 key=(kind,frozenset((a,b)));r=existing.get(key)
 if r is None:rnum+=1;r=dict(id=f'R{rnum:03d}',source=a,target=b,type=kind);d['relations'].append(r);existing[key]=r
 if uv:pnum+=1;r.setdefault('openings',[]).append(dict(id=f'P{pnum:03d}',kind='door',position_px=[2444-uv[1],uv[0]]))
 audit.append(dict(relation_id=r['id'],source=a,target=b,type=kind,reading_position=uv,basis='图面门洞' if uv else reason))
for a,b,uv in [('S095','S094',(1451,1387)),('S095','S090',(1435,1313)),('S099','S096',(1518,1014)),('S134','S222',(1933,1303))]:add(a,b,uv)
for a,b in [('S095','S096'),('S096','S105'),('S065','S077'),('S222','S126'),('S222','S131')]:add(a,b,reason='布局推断：同一功能块中的开放前室／服务工作区连续；未定位门位。')
add('S105','S108',kind='service',reason='用户确认药房服务柜台，面向连续公共大厅。')
add('S053','S052',kind='service',reason='用户确认登记取片服务，面向检查区南侧公共大厅。')
d['relations'].append(dict(id='E10',source=None,target='S096',type='entrance',name='药库北侧入口',entrance_type='external',position_px=[2444-997,1470]))
(root/'annotation.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');(run/'连通复核追加与门点撤回.json').write_text(json.dumps({'relations':audit,'withdrawn_internal_door_points':withdrawn,'reason':'控制区域内部门不能挂到另一侧公共走廊的access上；待K06确认。'},ensure_ascii=False,indent=2)+'\n')
state=json.loads((w/'review_state.json').read_text());state['connectivity_items'] += [
{'review_id':'K02','source':'S003','target':'S014','status':'pending','related_spaces':['S003','S006','S005','S010','S013','S014'],'question':'西药S003、中药S006、挂号收费S005及病区药房S013的人员入口分别接哪里？服务窗口不算人员门。','judgment':'西药和中药北侧可见独立入口／前室；挂号收费和病区药房朝向大厅。现图不足以确定各人员入口，暂不补access。','box_reading':[235,1110,610,1685]},
{'review_id':'K03','source':'S067','target':'S050','status':'pending','related_spaces':['S049','S062','S067','S050','S221','S092'],'question':'下排体检S049、S062和合并后的VIP用房S067，是否均经体检区S050进出？若不是，请写各自直接相连区域。','judgment':'倾向经S050及侧通道组织；下排分隔线上门位模糊，暂不补这三间的人员关系。','box_reading':[1060,1560,1530,1790]},
{'review_id':'K04','source':'S150','target':'S160','status':'pending','related_spaces':['S150','S129','S160','S161'],'question':'合并后的急诊手术S150，直接接东侧纵向通道S160，还是北侧公共通道S129（或两侧均接）？','judgment':'倾向东侧S160；现图该边界未能定位可靠开口，暂不补access。','box_reading':[1950,1370,2160,1645]},
{'review_id':'K05','source':'S193','target':'S157','status':'pending','related_spaces':['S193','S194','S154','S157','S181'],'question':'X光S193的人员入口直接接通道S157，还是经操作间S194接上侧通道S154？','judgment':'西北角有门状笔画，但与相邻诊室S181边界重叠，不能可靠判断其入口归属，暂不补access。','box_reading':[2170,1070,2370,1240]},
{'review_id':'K06','source':'S061','target':'S066','status':'pending','related_spaces':['S055','S059','S060','S061','S054','S066','S056','S057'],'question':'DR S061及两间X光S060/S059，是直接接检查通道S066，还是从西侧S055进入？S055应保留为通道，还是并入这些检查室的控制区？','judgment':'可见的左侧门更像检查室内部控制门，不能把这些门点标到右侧S066。本轮撤回4个错误归属门点，原概念关系留待复核。','box_reading':[1060,990,1235,1345]}]
state['checks'].update(connectivity_reviewed=False,visual_reviewed=False);state['not_required_details']=[{'space_ids':['S022','S043','S143','S163','S192'],'reason':'辅助／服务小间的工作人员内部路线本轮不细究；未记录access不表示不相通。'},{'space_ids':['S113','S116','S121','S179'],'reason':'庭院节点保留且不计面积；无明确开口，不为使全图连通强加人员边。'}]
(w/'review_state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
print({'spaces':len(d['spaces']),'relations':len(d['relations']),'openings':sum(len(r.get('openings',[])) for r in d['relations']),'pending_connectivity':5})
