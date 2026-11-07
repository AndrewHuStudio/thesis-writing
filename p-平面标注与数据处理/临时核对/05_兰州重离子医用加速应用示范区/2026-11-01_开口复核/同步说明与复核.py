from pathlib import Path
import json,re,hashlib,xml.etree.ElementTree as E
from collections import Counter
from shapely.geometry import Polygon,Point
O=Path(__file__).resolve().parent;P=O.parents[2]/'标注试样/05_兰州重离子医用加速应用示范区'
D=json.loads((P/'annotation.json').read_text());D['spaces'].sort(key=lambda s:int(s['id'][1:]));(P/'annotation.json').write_text(json.dumps(D,ensure_ascii=False,indent=2)+'\n')
A=json.loads((O/'逐关系复核.json').read_text());Q=json.loads((O/'本轮核对映射.json').read_text());old=(O/'修改前备份/标注说明.md').read_text();types=json.loads(Path('/Users/hushili/.codex/skills/outpatient-plan-annotation/references/space-types.json').read_text());c=Counter(s['type'] for s in D['spaces']);r=Counter(x['type'] for x in D['relations'])
rel=Path('../../临时核对/05_兰州重离子医用加速应用示范区/2026-11-01_开口复核')
def link(name):return (rel/name).as_posix()
lines=['# 兰州重离子医用加速应用示范区一层｜概念标注与连通性复核','',
'**状态：名称已齐，连通性仍待集中确认。** 本次已完成可确定部分；14组疑点包含16条保留的旧人员可达关系，另含MR入口尚未新增关系的问题。正式结构校验通过不表示这些疑点已经确认，不宣布本图连通性全部完成。','',
'**标注规模：**129个空间／区域，其中127个室内区域、2处露天／挑空中庭。原有127个S编号和全部已确认名称保留；新设S130、S131用于将原先跨实体分隔的连接通道分开。','',
'**类型与数量：**'+'、'.join(f'{types[k]} {v}个' for k,v in c.items())+'。','',
'**连接关系：**170条：人员可达145条、服务联系7条、共墙8条、建筑入口10条。','',
'**门洞与红点：**P001—P117，共117个可定位门洞（door），归并于106条access关系；同一空间对的多门只保存一条关系及多个openings。其余39条access没有定位点，其中23条为区域连续、开放楼梯或半墙等概念连接，16条为下表所列待确认旧关系。没有为连续区域、窗口、共墙或未辨清的检修符号编造坐标。','',
'**名称与显示：**JSON的name保留具体名称、type采用共享英文类别代码；SVG可见标签为“S编号＋具体名称＋〔标准功能类别〕”。红点及P编号与对应关系的opening、两端S编号、坐标逐项对应。建筑入口仍采用独立E编号。','',
'## 本轮集中核对（固定01—14）','',
'按西北01—03、东北04—07、西中08—11、东中12—13、东南14阅读；同片区先上后下，同排从左到右。核对号与P门洞编号相互独立。可在确认栏填写，或在聊天中回复`01=相通；02=检修口；08=更衣无北门、护士站有北门……`；“仅窗口”“不相通”“仍不清楚”也可填写。未答项继续保留，分批回答不改变映射。','',
f'![完整原图上的14组连通性核对](<{link("连通性核对总图.png")}>)','',
f'[可放大的核对总图SVG](<{link("连通性核对总图.svg")}>) · [具名原图](<05_兰州重离子医用加速应用示范区_原图.jpg>) · [正式标注SVG](<标注.svg>)','']
for group in dict.fromkeys(q['group'] for q in Q):
 items=[q for q in Q if q['group']==group];lines += [f'### {group}片区：'+(items[0]['number'] if len(items)==1 else items[0]['number']+'—'+items[-1]['number']),'',f'![{group}同号局部](<{link(group+"_核对局部.png")}>)','',
 '| 核对号 | 空间与旧关系 | 待确认问题 | 图面依据与把握 | 我的确认／备注 | 核对号（重复） |','| --- | --- | --- | --- | --- | --- |']
 for q in items:
  rr='、'.join(q['relations']) or '暂无access，确认后再新增'
  lines.append(f'| {q["number"]} | {q["spaces"]}；{rr} | {q["question"]} | {q["evidence"]} 现有图面不足以确定通行方式；把握：低。 | 待确认 | {q["number"]} |')
 lines.append('')
lines += ['## 本次已确定的修正','',
'- 西北蓝色通道S007与北侧大厅S078按门墙边界分开，电梯厅南门改接S078，另记录合用前室东门。西南侧卫生间S033、楼梯S035、强弱电S037/S038改接实际南侧通道S032；S036北门另接S015，S035与S036之间仅保留共墙。','- 东北二更S049、结算S050的南门改接S052。消防控制室与S044并不直接相邻，撤销旧R050，按北侧独立门新设E09。药房南端分出S131，分别连接出住院办理、西药房（二级）及楼梯电梯前室；已定位门均单独回查原图。','- 急诊药房S092的门实际通护士站S096；UPS门通抢救S094。同步修正S091、S094、S096的局部边界。西南楼梯北门改接S083；收费、配液、治疗、诊室和工作人员用房逐门定位。','- 门诊药房S119/S120的南门与服务联系分别保存；挂号与取药工作区的侧门补齐。东侧电梯前室出口新设E10；S121—S122门斗—S123机房按实际上下门位调整，S123与S124南侧只有共墙，不再记录人员直达。','- 南侧门斗S089移回原图标有“门斗”的3153—3236像素区域，门外3240—3332像素的雨篷／入口平台不作为室内房间。原S088保留西段，新增S130记录东段，两侧门分别连接门斗；E01保留编号并移至实际外门线。','',
'## 已确认内容与面积口径','']
# 保留旧说明中的具体确认、概念名称、合并和用户原词。
for prefix in ['空间名称已齐；','**单元修正：**','**名称与分类：**','**范围与精度：**']:
 for p in old.split('\n\n'):
  if p.startswith(prefix):lines.extend([p,''])
lines += ['**中庭与面积：**S034、S074为用户已确认的露天／挑空中庭；其编号、名称、原轮廓、courtyard／open_space属性均保持原样，不保存area_ratio，不新增人员穿行关系。127个室内区域参与归一化，area_ratio合计为1。边界和门斗口径的修正后重新计算相对占比；不保存平方米面积或像素面积。','',
'**入口：**'+ '、'.join(x['id']+' '+x['name'] for x in D['relations'] if x['type']=='entrance')+'。','',
'**核验与完成边界：**正式`validate --check-dir`通过；已渲染并查看全图、西北／东北／西中／东中／西南／东南密集区及南侧入口局部。117个红点均与JSON编号、坐标和两端空间对应，点位距两端标注边界均不超过15像素。既有名称与中庭事实逐项比对保留。核对图14号连续、每项唯一、引线无交叉。语义疑点仍待用户确认；保留的旧疑点边不可当作已审核的训练真值，未记录关系也不当作负例。','',
'**文件与备份：**样本目录仍仅保留具名原图、标注.svg、annotation.json、标注说明.md四文件。原图SHA-256与修改前一致；备份、逐关系判读表、变更记录及本轮核对材料均在上述外部核对目录。','',
f'[逐关系复核表](<{link("逐关系复核.md")}>) · [修改前说明（含原人工记录）](<{link("修改前备份/标注说明.md")}>)','']
(P/'标注说明.md').write_text('\n'.join(lines))
# 人工审计表只保存在外部，不污染核心JSON。
a=['# 05号逐关系连通复核','', '| 关系 | 两端空间 | 状态 | 开口 | 判读依据 |','| --- | --- | --- | --- | --- |']
for x in A:
 ops='、'.join(o['id']+':'+str(o['position_px']) for o in x['openings']) or '无定位'
 a.append(f'| {x["id"]} | {x["source"]} ↔ {x["target"]} | {x["status"]} | {ops} | {x["evidence"]} |')
(O/'逐关系复核.md').write_text('\n'.join(a)+'\n')
# 交叉核查当前实体文件，避免只校验生成脚本。
oldD=json.loads((O/'修改前备份/annotation.json').read_text());S={s['id']:s for s in D['spaces']};B={s['id']:s for s in oldD['spaces']}
assert all((s['name'],s['type'],s['level'],s['scope'])==(S[k]['name'],S[k]['type'],S[k]['level'],S[k]['scope']) for k,s in B.items())
assert all(B[k]==S[k] for k in ['S034','S074'])
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();img=D['image']['file'];assert h(P/img)==h(O/'修改前备份'/img)
T=E.parse(P/'标注.svg');groups={g.get('id'):g for g in T.iter() if g.get('data-space-name') is not None}
for sid,s in S.items():
 g=groups[sid];visible=''.join(e.text or '' for e in g if e.tag.endswith('text'));strip=lambda x:re.sub(r'\s+','',x)
 assert strip(s['id']) in strip(visible) and strip(s['name']) in strip(visible) and strip('〔'+types[s['type']]+'〕') in strip(visible),(sid,visible)
polys={k:Polygon(s['polygon_px']) for k,s in S.items()};bad=[];maxdist=0
for rr in D['relations']:
 for op in rr.get('openings',[]):
  dd=[polys[k].boundary.distance(Point(op['position_px'])) for k in [rr['source'],rr['target']]];maxdist=max(maxdist,*dd)
  if max(dd)>15.001:bad.append((rr['id'],op['id'],dd))
assert not bad,bad
assert len(Q)==14 and [q['number'] for q in Q]==[f'{i:02}' for i in range(1,15)]
assert len([z for q in Q for z in q['relations']])==16
assert {z for q in Q for z in q['relations']}=={a['id'] for a in A if a['status']=='待确认旧关系'}
# MD链接均必须存在，包括外部同号图与备份。
for target in re.findall(r'\]\(<([^>]+)>\)',(P/'标注说明.md').read_text()):assert (P/target).exists(),target
report={'original_sha256':h(P/img),'original_unchanged':True,'existing_ids_names_types_scope_preserved':len(B),'courtyards_unchanged':['S034','S074'],'spaces':len(S),'indoor_spaces':sum(s['type'] not in ['landscape','courtyard'] for s in S.values()),'relations':dict(r),'openings':sum(len(r.get('openings',[])) for r in D['relations']),'located_access':sum(bool(r.get('openings')) for r in D['relations']),'unlocated_concept':23,'retained_unconfirmed_access':16,'max_opening_distance_to_endpoint_boundary_px':round(maxdist,3),'visible_space_labels':len(groups),'review_groups':len(Q),'review_leader_crossings':json.loads((O/'核对图检查.json').read_text())['leader_crossings'],'all_md_links_exist':True,'sample_files':sorted(p.name for p in P.iterdir())}
(O/'补充核验结果.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))
