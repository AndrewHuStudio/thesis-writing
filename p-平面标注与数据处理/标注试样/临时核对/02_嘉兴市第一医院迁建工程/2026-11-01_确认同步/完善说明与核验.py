from pathlib import Path
from shapely.geometry import Polygon,Point
import json,hashlib,re,xml.etree.ElementTree as ET,sys,os
sys.path.insert(0,'/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts')
import annotation_tools as at
out=Path(__file__).resolve().parent;p=out.parents[2]/'02_嘉兴市第一医院迁建工程'
a=json.loads((p/'annotation.json').read_text());old=json.loads((out/'修改前备份/annotation.json').read_text());ss={s['id']:s for s in a['spaces']};gs={sid:Polygon(s['polygon_px']) for sid,s in ss.items()}
# Reposition the narrow L-shaped store-room label into its wide head.
svg=p/'标注.svg';tree=ET.parse(svg);root=tree.getroot();group=next(e for e in root.iter() if e.get('id')=='S223')
for e in list(group):
 if e.tag in ['{'+at.NS+'}text','{'+at.NS+'}rect']:group.remove(e)
x,y,w,h,font,lines=at.place_label(Polygon([[1890,1892],[1996,1892],[1996,1924],[1890,1924]]),ss['S223'])
group.append(at.element('rect',{'x':x,'y':y,'width':w,'height':h,'rx':2,'fill':'white','fill-opacity':'.94','stroke':'#7c3aed','stroke-width':'.8'}))
for i,line in enumerate(lines):group.append(at.txt(x+4,y+font+2+i*(font+2),line,font,'#7c3aed',True))
# Keep full labels inside the narrow service rooms rather than letting them spill below.
for sid in ['S100','S101','S104','S028','S029','S030','S031','S032','S033']:
 group=next(e for e in root.iter() if e.get('id')==sid);sp=ss[sid];g=gs[sid];anchor=g.representative_point();font=4 if g.bounds[3]-g.bounds[1]<30 else 5
 maxw=g.bounds[2]-g.bounds[0]-4
 lines=[sid]+at.wrap(sp['name'],font,maxw-4)+at.wrap('〔'+at.TYPE_NAMES[sp['type']]+'〕',font,maxw-4)
 w=max(at.visual_width(t,font) for t in lines)+4;h=len(lines)*(font+1)+3;x=anchor.x-w/2;y=anchor.y-h/2
 assert g.covers(Polygon([(x,y),(x+w,y),(x+w,y+h),(x,y+h)])),sid
 for e in list(group):
  if e.tag in ['{'+at.NS+'}text','{'+at.NS+'}rect']:group.remove(e)
 group.append(at.element('rect',{'x':x,'y':y,'width':w,'height':h,'rx':1,'fill':'white','fill-opacity':'.94','stroke':'#7c3aed','stroke-width':'.5'}))
 for i,line in enumerate(lines):group.append(at.txt(x+2,y+font+1+i*(font+1),line,font,'#7c3aed',True))
tree.write(svg,encoding='unicode')
# Verify each confirmed outcome, retained opening IDs and the remapped local doors.
def edge(x,y,typ='access'):return any(r['type']==typ and {r['source'],r['target']}=={x,y} for r in a['relations'])
required=[('S037','S038'),('S038','S040'),('S048','S258'),('S114','S261'),('S118','S261'),('S120','S261'),('S135','S258'),('S102','S099'),('S099','S259'),('S105','S259'),('S172','S268'),('S173','S268'),('S020','S268'),('S170','S268'),('S091','S277'),('S277','S260'),('S108','S276'),('S109','S276'),('S223','S274'),('S225','S226'),('S227','S274'),('S249','S246'),('S246','S250'),('S250','S276'),('S235','S275')]
assert all(edge(x,y) for x,y in required)
assert edge('S226','S274','service') and edge('S225','S274','shared_wall')
assert not edge('S226','S274') and not edge('S225','S274')
assert not edge('S267','S264') and not edge('S091','S257') and not edge('S091','S260')
assert ss['S023']['name']=='废物存放' and ss['S023']['type']=='waste_handling'
assert ss['S264']['name']=='医护走廊' and ss['S264']['type']=='corridor'
assert not set(ss).intersection({'S027','S273','S244'}) and len(ss)==274
oldops={o['id']:o for r in old['relations'] for o in r.get('openings',[])};ops={o['id']:o for r in a['relations'] for o in r.get('openings',[])}
assert all(ops.get(oid)==o for oid,o in oldops.items())
changed=set(json.loads((out/'本轮变更.json').read_text())['changed_spaces'])
for r in a['relations']:
 if not changed.intersection({r['source'],r['target']}):continue
 for op in r.get('openings',[]):
  assert all(gs[sid].boundary.distance(Point(op['position_px']))<=12 for sid in [r['source'],r['target']]),(r,op)
ns={'s':at.NS}
for sid,s in ss.items():
 group=next(e for e in root.iter() if e.get('id')==sid)
 label=''.join(e.text or '' for e in group.findall('s:text',ns));assert sid in label and s['name'] in label,(sid,label)
sha=hashlib.sha256((p/a['image']['file']).read_bytes()).hexdigest();assert sha==(out/'原图SHA256.txt').read_text().strip()
# Final overview keeps the case scope, review decisions and a working link to the verbatim answers.
summary=(out/'新概览.md').read_text().replace('# 平面标注概览','# 嘉兴市第一医院迁建工程｜一层标注说明',1)
archive='../临时核对/'+p.name+'/'+out.name+'/用户填写原文.md'
rows=[
('01','S037 经 S038 门厅与 S040 相连；S048 由 S258 门诊大厅进入。'),
('02','S261 修正为右侧医护走廊，连通 S114、S118、S120；保留男女更衣原编号及经洗手台前区进入的整体表达。原指向 S124 的两处局部门洞改接 S261。'),
('03','S135 从 S258 门诊大厅进入。'),
('04','S102 与 S099 挂号收费相连；S099、S105 与 S259 医疗主街相连。按门洞纠正此处库房及相邻设备间分界。'),
('05','S172、S173、S020 分别连接 S268。'),
('06','S170 东侧连接 S268；S264 更名为“医护走廊”、类型为 corridor；S267 与 S264 不记录直接 access。'),
('07','S091 经新增 S277 楼梯门厅到 S260 医疗主街。门厅另接 S092 等候厅及 S257；原 P068、P069、P246 改挂实际门厅，原 P247 仍属 S257—S260。'),
('08','S108、S109 均由 S276 医疗主街进入；S107 与 S276 的既有连接保留。'),
('09、10','S023 按用户确认保留“废物存放”，归入 waste_handling；S273 并入 S023，原 S273 编号停用。'),
('11','S027 并入 S223，统一为“库房”；补入西侧门前窄段，连接 S274，并校正 S028 边界。'),
('12','S226—S274 记录为服务窗口 service，S225—S274 记录共墙 shared_wall；S225—S226 的两处室内门及 S225—S276 既有门保留。'),
('13','S227 补入北侧横向窄段并连接 S274；同时修正 S031 及 S274 相邻边界。'),
('14','S249 从 S246 报告厅进入；外围环廊与连接通道合并为 S250“报告厅连接通道及外围环廊”，报告厅经南、北两门进入环廊，再到 S276。'),
('15','按用户要求删除 S244，不重排其余编号。原图上的楼梯图形原样保留，不纳入本次数据范围。'),
('16','S235 由 S275 行政区通道进入。')]
summary+='\n**范围与精度：**一层总平面中的门诊、急诊、医技、住院大厅、行政与报告厅，按 scope 区分。床位区、交通核、学术交流室及部分药房按概念功能块表达；不补猜诊室小字。原图和 307 个既有门洞点位均保留，既有 S／P 编号不重排。两处空白内院不推定为室内或绿化；报告厅西侧入口前场未并入室内环廊。\n'
summary+='\n**本轮确认（2026-11-01）：**已读取并同步 16 项人工填写。以下为落实结果；你的原始回答、问题和截图完整保存在[用户填写原文]('+archive+')。\n\n| 核对号 | 已落实内容 |\n| --- | --- |\n'+'\n'.join('| '+n+' | '+v+' |' for n,v in rows)+'\n'
summary+='\n**连通定位口径：**可辨认门洞记录原图近似中心并绘制红点；人工确认了可通行、但门洞仍无法独立定位的连接保留为概念 access，不编造点位。S037—S038、S048—S258、S099—S259、S105—S259、S172—S268、S020—S268、S170—S268、S091—S277、S108—S276 属于本轮这类连接。服务窗口及共墙不生成通行红点；未记关系不作不可达或负样本。\n'
summary+='\n**文件：**[原图]('+a['image']['file']+') · [具名标注 SVG](标注.svg) · [annotation.json](annotation.json)。\n'
(p/'标注说明.md').write_text(summary)
for f in [p/'标注说明.md',out/'用户填写原文.md']:
 for path in re.findall(r'\]\(([^)]+)\)',f.read_text()):
  if not path.startswith('#'):assert (f.parent/path).exists(),(f,path)
report={'confirmed_questions':16,'spaces':len(ss),'relations':len(a['relations']),'old_openings_preserved':len(oldops),'total_openings':len(ops),'original_sha256':sha,'all_visible_labels_match':True,'all_local_openings_within_12px_of_both_boundaries':True,'valid_links':True,'data_scope':'本张一层平面'}
(out/'补全核验记录.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))
