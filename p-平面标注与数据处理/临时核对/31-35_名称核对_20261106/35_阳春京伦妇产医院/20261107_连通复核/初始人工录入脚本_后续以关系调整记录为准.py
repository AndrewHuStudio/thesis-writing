import json,hashlib,collections
from pathlib import Path
from shapely.geometry import Polygon,Point
base=Path('/Users/hushili/Documents/研究-论文写作/大论文/p-平面标注与数据处理')
p=base/'标注试样/35_阳春京伦妇产医院'
review=base/'临时核对/31-35_名称核对_20261106/35_阳春京伦妇产医院'
out=review/'20261107_连通复核'
d=json.loads((out/'修改前备份/annotation.json').read_text());state=json.loads((review/'review_state.json').read_text())
ss={s['id']:s for s in d['spaces']};rr={r['id']:r for r in d['relations']}
changes=[]
def change_source(rid,source,reason):
 old=dict(rr[rid]);rr[rid]['source']=source;changes.append({'relation_id':rid,'before':old,'after':dict(rr[rid]),'reason':reason})
change_source('R015','S014','卫生间门朝向后侧通道S014，非休息室S012。')
for rid in ['R026','R028','R030']:
 change_source(rid,'S035','对应清洁/煎药/荫凉房右侧门直接朝向S035；原S022为另一侧后勤走道。')
removed={
 'R011':'S008楼梯与S035之间为连续墙，S035侧可见门属于S009水吧台；楼梯保留独立外门。',
 'R049':'S039与S038仅角点接触，实际经S044衔接，不保留跨角直连。',
 'R051':'S039与S043之间有连续横向分隔；S043明确双门连接S044，暂不建立跨墙直连。',
 'R063':'S056北侧与S044之间为连续分隔；人员通过东侧双门进入S075再接门厅。',
 'R075':'S075与S072相邻侧未见门；暂移除原直连，保留S072至S076的概念连接，列K01核对。'
}
for rid,reason in removed.items():changes.append({'relation_id':rid,'removed':rr[rid],'reason':reason})
d['relations']=[r for r in d['relations'] if r['id'] not in removed]
# 补齐配液室实际入口前的小L形范围，原几何在门口留下25px高空缺。
s=ss['S015'];old=s['polygon_px'];s['polygon_px']=[[2444-y,x] for x,y in [(1090,690),(1185,690),(1185,750),(1145,750),(1145,808),(1090,808)]]
changes.append({'space_id':'S015','before_polygon_px':old,'after_polygon_px':s['polygon_px'],'reason':'按原图配液室L形入口补齐既有空缺，未重编号或细分空间。'})
# 坐标人工从本图转正工作图读取；转换回原图坐标。
points={
'R001':[(555,580)],'R002':[(675,625)],'R003':[(630,690)],'R004':[(815,690)],
'R007':[(715,625)],'R008':[(525,555)],'R009':[(735,575)],'R012':[(555,765)],
'R015':[(950,755)],'R016':[(1185,770)],'R017':[(1185,735)],'R021':[(1177,890),(1177,972)],
'R023':[(425,906)],'R024':[(475,906)],'R025':[(465,955)],'R026':[(555,955)],
'R027':[(465,1010)],'R028':[(555,1035)],'R030':[(555,1075)],'R031':[(555,922)],
'R032':[(425,860)],'R033':[(475,860)],'R034':[(555,1142)],'R035':[(555,1290)],
'R036':[(610,1108)],'R038':[(610,1570)],'R039':[(610,1820)],'R040':[(555,1808)],
'R041':[(555,1885)],'R042':[(555,1525)],'R043':[(555,1565)],'R044':[(490,1520)],
'R045':[(814,1012)],'R046':[(814,1140)],'R052':[(1035,1395)],'R053':[(1180,1148)],
'R055':[(630,1550)],'R056':[(760,1550)],'R058':[(835,1788)],'R059':[(950,1788)],
'R060':[(1065,1788)],'R061':[(1088,1840)],'R062':[(730,1870)],'R064':[(1250,1680)],
'R065':[(695,1952)],'R066':[(744,1935)],'R067':[(744,1970)],'R068':[(910,1950)],
'R069':[(1015,1950)],'R070':[(1110,1950)],'R071':[(1225,1950)],'R072':[(1250,1910)],
'R074':[(1405,1570)],'R076':[(1450,1765)],'R077':[(1250,2020)],'R078':[(1560,1945)],
'R079':[(1650,1945)],'R080':[(1430,1557)],'R081':[(1475,1557)],'R082':[(1520,1557)],
'R085':[(1808,1655)],'R086':[(2025,1490)]}
newrels=[
 {'id':'R129','source':'S075','target':'S073','type':'access'},
 {'id':'R130','source':'S075','target':'S082','type':'access'},
 {'id':'R131','source':'S017','target':'S037','type':'access'}]
for r in newrels:d['relations'].append(r);rr[r['id']]=r
points['R129']=[(1498,1648)];points['R131']=[(1035,840)]
openpass={'R031','R072','R074'}
audit=[];i=0
for rid,qs in points.items():
 for qx,qy in qs:
  i+=1;pt=[2444-qy,qx];r=rr[rid];r.setdefault('openings',[]).append({'id':f'P{i:03d}','kind':'open_passage' if rid in openpass else 'door','position_px':pt})
  distances={s:round(Polygon(ss[s]['polygon_px']).boundary.distance(Point(pt)),3) for s in [r['source'],r['target']]}
  audit.append({'opening_id':f'P{i:03d}','relation_id':rid,'source':r['source'],'target':r['target'],'position_px':pt,'endpoint_distance_px':distances})
# 入口仍使用E号。主入口分为图上左右两个实际门口。
rr['E01']['position_px']=[2444-2057,1270]
rr['E01']['name']='门厅主入口（左侧门）'
entrances=[('E12','S075','门厅主入口（右侧门）','main',1435,2057),('E13','S008','西北楼梯下侧外门','secondary',400,780),('E14','S051','西南楼梯前厅外门','secondary',400,1810)]
for eid,target,name,typ,x,y in entrances:
 d['relations'].append({'id':eid,'source':None,'target':target,'type':'entrance','name':name,'entrance_type':typ,'position_px':[2444-y,x]})
# 可见的左侧楼梯外门沿用原E08/E09，不因相邻室内关系被移除而删入口。
rr['E08']['position_px']=[2444-695,400]
rr['E09']['position_px']=[2444-1730,400]
state['connectivity_items']=[
 {'review_id':'K01','source':'S075','target':'S072','status':'pending','question':'门厅东侧电梯交通核S072是否只经S076进入门厅，还是也能直接连通S075？','judgement':'倾向S072经南侧白色前厅接S076；S075侧未见明确门洞，原R075暂移除。','related_space_ids':['S076','S073','S074']},
 {'review_id':'K02','source':'S042','target':'S043','status':'pending','question':'03号灰色区域S042与东侧白色区域S043之间是否可以通行？','judgement':'S043至S044的双门明确，S042与S043的分界性质不清；目前不补S042的连接。','related_space_ids':['S039','S044'],'linked_name_review_id':'03'}]
state['checks']={'connectivity_reviewed':True,'visual_reviewed':False}
state['review_date']='2026-11-07'
state['relation_changes']=changes
state['layout_inferences']=[
 {'source':'S035','target':'S033','reason':'西药房后场朝西侧工作人员通道组织，与中药房及药房柜台区域相邻；保留既有概念关系，门扇不清，不生成红点。'},
 {'source':'S072','target':'S076','reason':'电梯组底侧白色前厅与S076侧衔接；保留无门位概念关系，K01核对是否另向S075。'},
 {'source':'S075','target':'S082','reason':'南侧独立电梯嵌在大厅边缘，面向S075，按交通核整体记录，不推断内部小间路线。'}]
state['not_required_details']=[{'space_ids':['S079','S081'],'reason':'资料室、小清洁/卫生辅助间具体入口未辨明，本轮不细究；未补人员关系，不表示不相通。'},{'space_ids':['S073'],'reason':'合并功能块中的小隔间不细分，仅记录可见朝S075的门。'}]
state['opening_audit_file']='20261107_连通复核/门洞端点审计.json'
(p/'annotation.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
(review/'review_state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
(out/'门洞端点审计.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
(out/'关系调整记录.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n')
print('counts',len(d['spaces']),len(d['relations']),i,collections.Counter(r['type'] for r in d['relations']))
print('endpoint exceptions',[a for a in audit if max(a['endpoint_distance_px'].values())>.1])
