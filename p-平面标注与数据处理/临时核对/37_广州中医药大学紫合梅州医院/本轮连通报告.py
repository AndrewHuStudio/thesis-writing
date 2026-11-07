from pathlib import Path
from collections import Counter,defaultdict,deque
import json,copy,os,xml.etree.ElementTree as ET
import pymupdf

R=Path(__file__).resolve().parent;P=R.parent.parent/'标注试样'/R.name
BASE=R/'20261107_连通分析前备份_134616'
D=json.loads((P/'annotation.json').read_text());old=json.loads((BASE/'annotation.json').read_text())
state=json.loads((R/'review_state.json').read_text());S={s['id']:s for s in D['spaces']}
def graph(data):
    adj={s['id']:set() for s in data['spaces']}
    for rel in data['relations']:
        if rel['type']=='access':adj[rel['source']].add(rel['target']);adj[rel['target']].add(rel['source'])
    return adj
def reach(adj,seeds):
    q=list(dict.fromkeys(seeds));seen=set(q)
    for a in q:
        for b in adj[a]-seen:seen.add(b);q.append(b)
    return seen
def path(adj,start,end):
    q=deque([start]);prev={start:None}
    while q:
        a=q.popleft()
        if a==end:break
        for b in sorted(adj[a]):
            if b not in prev:prev[b]=a;q.append(b)
    if end not in prev:return None
    out=[];a=end
    while a is not None:out.append(a);a=prev[a]
    return out[::-1]
def stats(data):
    adj=graph(data);entries=[r for r in data['relations'] if r['type']=='entrance']
    main=reach(adj,[r['target'] for r in entries if r['entrance_type']=='main'])
    any_entry=reach(adj,[r['target'] for r in entries])
    return dict(spaces=len(data['spaces']),access=sum(r['type']=='access' for r in data['relations']),
        relations=len(data['relations']),openings=sum(len(r.get('openings',[])) for r in data['relations']),
        opening_relations=sum(bool(r.get('openings')) for r in data['relations']),
        conceptual_access=sum(r['type']=='access' and not r.get('openings') for r in data['relations']),
        main_entry_reachable=len(main),any_entry_reachable=len(any_entry),
        no_recorded_entry_path=sorted(set(adj)-any_entry),main_set=main,any_set=any_entry)
before=stats(old);after=stats(D);adj=graph(D)
missing=[]
for sid in after['no_recorded_entry_path']:
    if sid in {'S036','S062','S072','S073'}:
        reason='空间/结构性质未确定，未见可靠入口；保留unknown和轮廓，不编连接。'
    elif sid in {'S097','S134','S137'}:
        reason='原通道推定撤回，实体分隔/家具界面可见但人员入口证据不足。'
    else:reason='无名辅助隔间/功能区内部小间，图面入口证据不足，本轮不穷尽其内部路线。'
    missing.append(dict(space_id=sid,name=S[sid]['name'],type=S[sid]['type'],reason=reason,
                        interpretation='未记录通行路径，不是确认不通，也不是训练负样本。'))
assert all(s['type']=='unknown' for s in missing)
entries=[r for r in D['relations'] if r['type']=='entrance']
independent=[r for r in entries if r['target'] not in after['main_set']]
targets=['S019','S028','S030','S031','S034','S046','S047','S055','S067','S039','S042','S057','S040','S080','S082','S083','S250','S038','S219']
paths={sid:path(adj,'S020',sid) for sid in targets};assert all(paths.values())
report=dict(scope='无名空间逐个粗轮廓，主要通行按图面证据和布局推断复核；不强求所有辅助隔间全连通',
    before={k:v for k,v in before.items() if not k.endswith('_set')},
    after={k:v for k,v in after.items() if not k.endswith('_set')},
    main_paths=paths,independent_entries=independent,evidence_insufficient_nodes=missing,
    pending_primary_questions=[],former_K_items=state['connectivity_items'],
    naming_unknown_is_not_omitted_annotation=True,
    warning='可达统计只用室内access；不同建筑入口不通过一个室外总节点相连。没有记录关系不是负例。')
(R/'本轮连通分析结果.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')

# Colour current outlines by recorded graph reachability. This is not a physical route map.
ns={'s':'http://www.w3.org/2000/svg'};ET.register_namespace('',ns['s']);ET.register_namespace('xlink','http://www.w3.org/1999/xlink')
tree=ET.parse(P/'标注.svg');root=tree.getroot()
for g in root.iter():
    sid=g.get('id')
    if sid not in S:continue
    poly=g.find('s:polygon',ns)
    if poly is None:continue
    if sid in after['main_set']:color='#159447';status='main_entry_reachable'
    elif sid in after['any_set']:color='#2563eb';status='independent_entry'
    else:color='#f59e0b';status='path_not_recorded'
    poly.set('fill',color);poly.set('fill-opacity','.18');poly.set('stroke',color);g.set('data-reachability',status)
texts=root.findall('s:text',ns)
texts[0].text='37号｜已记录的人员可达分布'
texts[1].text=f'绿色：主入口可达{len(after["main_set"])}；蓝色：独立入口{len(after["any_set"]-after["main_set"])}；橙色：{len(missing)}个节点路径证据不足，不能解释为不通。'
tree.write(R/'连通分析_可达分布.svg',encoding='unicode')
with pymupdf.open(R/'连通分析_可达分布.svg') as doc:
    doc[0].get_pixmap(matrix=pymupdf.Matrix(.7,.7),alpha=False).save(R/'连通分析_可达分布.png')

rel=os.path.relpath(R,P);archive=os.path.relpath(BASE/'标注说明.md',P)
types=Counter(r['type'] for r in D['relations']);unknown=sum(s['type']=='unknown' for s in S.values())
md=['# 37号｜逐空间粗轮廓与连通分析','',
 '**状态：**已完成本轮主要通行复核与补充。房名缺失按未知保留；无可靠入口的辅助范围不强行补边。此状态不表示全部具体功能已识别。','',
 f'**规模：**{len(S)}个单元；{types["access"]}条access、{types["service"]}条service、{types["shared_wall"]}条shared_wall、{types["entrance"]}处入口；{after["openings"]}个门洞定位对应{after["opening_relations"]}条access，另{after["conceptual_access"]}条为无定位概念连接。','',
 '[原图](37_广州中医药大学紫合梅州医院_原图.jpg) · [当前标注图](标注.svg)','',
 f'**可达性：**主入口经现有access可达{after["main_entry_reachable"]}个节点，计入各独立外门后共{after["any_entry_reachable"]}个；另{len(missing)}个节点缺少可证实的入口路径。后者不表示不相通，也不作负样本。','',
 '绿色表示主入口可达，蓝色表示独立外门，橙色表示路径证据不足；颜色不代表门禁权限。','',
 f'![已记录的可达分布]({rel}/连通分析_可达分布.png)','',
 '## 主要通行组织','',
 '- 西侧：中央门厅S020 ↔ 西翼通道S054 ↔ 药房后场S053；后场分别进入中药房S046、西药房S047，并经门进入专家门诊内通道S067。',
 '- 妇儿：门厅S021 → 妇科通道S030 → 南侧通道S089 → 输液前区S138 → 儿科输液S031 → 成人输液前区S143 → 成人输液S034；儿科通道S028经S088连接急诊。',
 '- 医技：门厅S021 → 东翼通道S086 → 医技通道S085；放射科内通道S055同时接南侧通道S085与东部通道S084。',
 '- 急诊：S088 → 急诊通道S039/S232 → 急救S042、留观S057、住院门厅S040；留观南通道S091接东侧公共带S250。',
 '- 东南：东部通道S084分别连接VIP大厅S080、肠道门诊通道S082及发热门诊通道S083；内部前区按实际组织分段连接。','',
 '## 本轮校正','',
 '- 补齐S138—S089、S138—S031、S143—S034，以及放射科内外通道等拆分后遗漏的关系。',
 '- 卫生间及交通核分别按可辨门口、共用前区和布局组织补连；共墙、柜台服务不当作人员门。',
 '- P006移至实际南向门并改接S089；撤回西侧墙上的误点P140，该组实际入口保留P028。新P号从P155续编，不复用P140。',
 '- S097、S134、S137无贯通证据，恢复unknown，不再用“通道”名称暗示可穿行；S207按图面纠正为交通核局部。','',
 f'![妇儿连接与南向门点]({rel}/本轮连通_SVG_妇儿.png)','',
 f'![医技内部及外侧通道]({rel}/本轮连通_SVG_医技.png)','',
 f'![急诊、留观及东侧公共带]({rel}/本轮连通_SVG_急诊东侧.png)','',
 '## 独立入口与信息缺失','',
 'S066保留独立外门E06；S043保留120值班入口E08；S013、S015分别保留商铺外门E10、E11。未通过室外总节点把这些空间强行连进主楼网络。','',
 '原K01：S066内部是否另接专家门诊仍未知，但独立入口明确，本轮无需必答。原K02：S072/S073厚边界单元性质及入口信息缺失，保留unknown和轮廓，不编造门或连接。原题号及处理依据保存在外部记录。','',
 f'**未记录入口路径的{len(missing)}个单元：**'+'、'.join(x['space_id'] for x in missing)+'。','',
 f'**功能缺失：**{unknown}个单元保持unknown；房名不可读不等于漏标，不要求逐项猜名。S026、S036、S062等范围的庭院/室内性质若有新证据再更新；确定庭院/挑空后统一不计面积。','',
 f'[原名称填写与连通问题存档]({archive}) · [逐房间核对总图]({rel}/37_逐房间完整核对总图.png)','']
(P/'标注说明.md').write_text('\n'.join(md))
print(json.dumps({k:v for k,v in after.items() if not k.endswith('_set')},ensure_ascii=False))
