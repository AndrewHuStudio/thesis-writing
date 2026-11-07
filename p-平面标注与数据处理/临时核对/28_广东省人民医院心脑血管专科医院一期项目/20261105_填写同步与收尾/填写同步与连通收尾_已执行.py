from pathlib import Path
import json,html,re,sys,hashlib,shutil
P=next(Path('/Users/hushili/Documents/研究-论文写作/大论文/p-平面标注与数据处理/标注试样').glob('28_*'));BASE=P.parents[1]/'临时核对'/P.name;O=BASE/'20261105_填写同步与收尾';B=O/'同步前四文件与用户原始填写';d=json.loads((P/'annotation.json').read_text());by={s['id']:s for s in d['spaces']};md=html.unescape((B/'标注说明.md').read_text())
rows=[]
for line in md.splitlines():
 c=[x.strip() for x in line.split('|')]
 if len(c)==9 and c[1].isdigit():rows.append(c)
assert len(rows)==127
confirmed={};original_answers={}
for c in rows:
 sid=c[2];answer=c[6]
 if answer in ['待确认','待填写','待定','图面识读（可改）']:continue
 original_answers[sid]=answer
 if answer in ['已确认（用户统一确认）']:name=c[3]
 elif answer=='诊室诊室':name='诊室'
 elif answer=='中庭':name='中庭'
 else:name=answer
 confirmed[sid]=name
confirmed['S123']='准备室';original_answers['S123']='准备室（本轮聊天明确确认）'
for sid in ['S035','S040']:
 by[sid].update(name='中庭',type='courtyard',level='open_space');by[sid].pop('area_ratio',None)
for n in range(143,149):by[f'S{n:03d}'].update(name='诊室',type='consultation')
for sid in ['S194','S205']:by[sid].update(name='医护',type='staff_support')
by['S123'].update(name='准备室',type='patient_preparation')
# 原始用户填写逐字归档；诊室诊室仅去除明显重复，S编号不变。
(O/'用户填写逐项归档.json').write_text(json.dumps(dict(answers=original_answers,K01='庭院／挑空 不计入一层面积，因为有的医院就是有很多采光中庭，skill也同步了，以后不要再问了',K02='可以直接进入',S123_chat='准备室',normalizations={'S146':{'raw':'诊室诊室','applied':'诊室'}}),ensure_ascii=False,indent=2)+'\n')
# 按本图照片复核：以下旧边跨越连续墙或中间房间，撤回而非当作用户确认不相通。
removed_ids={'R038','R039','R044','R046','R072','R073','R074','R075','R076','R077','R078','R079','R080','R081','R082','R083','R084','R085','R088','R095'}
removed=[r for r in d['relations'] if r['id'] in removed_ids];assert all(not r.get('openings') for r in removed)
d['relations']=[r for r in d['relations'] if r['id'] not in removed_ids]
seq=max(int(r['id'][1:]) for r in d['relations'] if r['id'].startswith('R'));pseq=max(int(p['id'][1:]) for r in d['relations'] for p in r.get('openings',[]));added=[];locations=[];inferred=[]
def pair(a,b,reason='图面连续／明确门口',infer=False):
 global seq
 a=f'S{a:03d}';b=f'S{b:03d}'
 for r in d['relations']:
  if r['type']=='access' and {r['source'],r['target']}=={a,b}:return r
 seq+=1;r=dict(id=f'R{seq:03d}',source=a,target=b,type='access');d['relations'].append(r);added.append(dict(**r,reason=reason))
 if infer:inferred.append(dict(source=a,target=b,reason=reason))
 return r

def mark(a,b,x,y,kind='door'):
 global pseq
 r=pair(a,b);pseq+=1;p=dict(id=f'P{pseq:03d}',kind=kind,position_px=[x,y]);r.setdefault('openings',[]).append(p);locations.append(dict(**p,relation_id=r['id'],source=r['source'],target=r['target']))
# 用户K02仅确认关系，不虚构通行门位。
pair(1,10,'用户K02：可以直接进入')
# 供应区人员动线在东侧交通前区衔接；电梯及卫生间朝此前区，按布局记概念连接。
pair(10,7,'布局推断：供应区东侧工作人员通道与交通核前通道在卫生间南侧衔接',True)
pair(6,7,'布局推断：供应电梯组朝东侧交通核前通道开门',True)
pair(11,7,'布局推断：供应卫生间通过其东侧交通前区组织进出',True)
pair(4,10,'布局推断：上排值班小间朝南侧内部通道',True)
pair(5,10,'布局推断：上排值班小间朝西侧内部通道',True)
# 影像控制室朝北侧患者通道有清楚门口；检查室经控制区组织进出不强制定位内部小门。
pair(49,50,'布局推断：CT检查室与中央控制室组成检查单元',True)
pair(51,50,'布局推断：CT检查室与中央控制室组成检查单元',True)
pair(98,97,'布局推断：胃肠机与紧邻的控制室形成检查单元',True)
pair(98,99,'布局推断：胃肠机房通过紧邻灌肠准备间组织患者进入',True)
mark(50,44,832,1276);mark(51,57,898,1367)
mark(57,45,1096,1382);mark(87,88,610,1614);mark(103,104,1096,1734)
mark(93,103,674,1712);mark(97,103,867,1712);mark(99,88,987,1635);mark(100,88,1027,1635)
# 急诊准备、配药小间的可见下侧门，均按原图坐标定位。
mark(123,128,606,2360);mark(124,129,647,2360);mark(111,113,533,2120)
pair(139,131,'布局推断：急诊护士站北侧工作区向内部通道开放',True)
(P/'annotation.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
(O/'连通语义复核.json').write_text(json.dumps(dict(removed=removed,removed_basis={'R038':'S104东侧外墙连续；从S089经既有门通医院街','R039':'S045与S089之间有更衣和卫生间，不是直接相邻开放区','CT':'检查室北墙连续，患者侧门落在控制室和注射室；保留南侧清楚门','DR':'中排检查与控制单元南墙连续，撤回直接向S088的批量边，保留工作人员侧清楚门','south_imaging':'备用检查单元北墙连续；胃肠机房无独立南侧门，经控制／准备单元概念组织'},added=added,new_openings=locations,inferred=inferred,reviewed_major_groups=['住院服务及医院街主网络','供应人员通道与工作区入口','影像控制与检查单元、患者通道接口','急诊主环廊、内通道、药房及DSA','东侧门诊纵向通道、南通道、诊室与电梯厅'],not_required_details=['设备带S012用于灭菌物品流程，不据物流箭头建人员边','S033/S034、S158/S160及S162服务柜台保留service；柜台背部精确小门本轮不穷尽','S105—S108商铺朝南侧外廊；原图未绘独立门，保留无内向access，未记不作不通负例','S121窄小交通设施及其他小设备间内部路线不细究；不凭颜色造门','庭院节点保留独立轮廓，不以不计面积推断不相通']),ensure_ascii=False,indent=2)+'\n')
# 将原127项固定核对号与明确用户原话导入外部状态，不往核心数据增加过程字段。
mapfile=BASE/'20261105_33项诊室确认同步/固定核对映射.json';mapping=json.loads(mapfile.read_text());name_items=[]
for q in mapping:
 sid=q['id'];sp=by[sid];item=dict(review_id=q['number'],space_id=sid,status='resolved',confirmed_name=sp['name'])
 if sid in original_answers:item.update(status='confirmed',answer=original_answers[sid],applied=True)
 name_items.append(item)
state=dict(name_items=name_items,connectivity_items=[dict(review_id='K01',source='S035',target='S040',status='not_required',answer='庭院／挑空 不计入一层面积，因为有的医院就是有很多采光中庭，skill也同步了，以后不要再问了',reason='空间用途／面积问题已同步为中庭courtyard/open_space；不是两庭院之间的人员关系问题'),dict(review_id='K02',source='S001',target='S010',status='confirmed_connected',answer='可以直接进入'),dict(review_id='K03',source='S046',target='S047',status='not_required',reason='MR入口已由照片与控制区布局自主复核，两侧MR通过控制室组织进出；非用户确认')],checks=dict(connectivity_reviewed=True,visual_reviewed=False),scope='主要功能空间、走廊大厅、主要交通核及入口的概念可达；辅助小间内部细节不穷尽',user_area_rule='已确认的中庭／庭院／挑空不计一层室内面积，沿用该口径，不重复追问顶盖或可步入')
sys.path.insert(0,'/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts');from review_workflow import load_state,save_state
state_path=BASE/'review_state.json';save_state(state_path,state);state=load_state(state_path,d,P/'annotation.json');save_state(state_path,state)
# 已同步问答全部归档，MD只留简短状态；目检完成后再生成正式完成概览。
(P/'标注说明.md').write_text('# 标注说明\n\n名称及用户确认已同步；正在进行最终图面核验。\n')
shutil.copy2('/tmp/finalize28.py',O/'填写同步与连通收尾_已执行.py')
print('spaces',len(d['spaces']),'relations',len(d['relations']),'openings',sum(len(r.get('openings',[])) for r in d['relations']),'unknown',sum(s['type']=='unknown' for s in d['spaces']),'removed',len(removed),'added',len(added),'new_openings',len(locations))
