from pathlib import Path
import json, copy, hashlib
from shapely.geometry import Polygon, box
from shapely.ops import unary_union
O=Path(__file__).resolve().parent
P=O.parents[2]/'标注试样'/'05_兰州重离子医用加速应用示范区'
D=json.loads((O/'修改前备份/annotation.json').read_text())
old=copy.deepcopy(D); S={s['id']:s for s in D['spaces']}; R={r['id']:r for r in D['relations']}
changes=[]
def rect(s,x1,y1,x2,y2): S[s]['polygon_px']=[[x1,y1],[x2,y1],[x2,y2],[x1,y2]]
def change(r,**kw):
 changes.append({'id':r,'before':copy.deepcopy(R[r]),'change':kw});R[r].update(kw)
def add(a,b,typ='access',**kw):
 n=max(int(r[1:]) for r in R if r.startswith('R'))+1;rid=f'R{n:03d}'
 r=dict(id=rid,source=a,target=b,type=typ,**kw);R[rid]=r;D['relations'].append(r);changes.append({'new':copy.deepcopy(r)});return rid
# 校正可从原图明确判断的边界，不更改已有空间编号或名称。
S['S007']['polygon_px']=[[356.3,1214.57],[1064.43,1214.57],[1064.43,1295.24],[611.77,1295.24],[611.77,1288.52],[356.3,1288.52]]
p=unary_union([Polygon(S['S078']['polygon_px']),box(1068,1149.58,1330,1290.76)])
S['S078']['polygon_px']=[list(q) for q in list(p.exterior.coords)[:-1]]
change('R005',target='S078')
# 电梯前室南界随可见门位修正，南侧连接通道为其留出凹口。
rect('S036',1142.86,2191.6,1243.7,2374)
p=unary_union([Polygon(S['S032']['polygon_px']),box(616.25,2191.6,672.27,2348)]).difference(box(1139.5,2343,1244,2377))
S['S032']['polygon_px']=[list(q) for q in list(p.exterior.coords)[:-1]]
# 东侧南端：蓝色通道的西界在2440附近；西侧粉色大厅延至1943。
p=unary_union([Polygon(S['S072']['polygon_px']),box(2440.34,2179,2492,2348)]).difference(box(1864,2184,1947.34,2402))
parts=sorted(p.geoms,key=lambda g:g.area,reverse=True)
assert len(parts)==2 and parts[0].bounds[1]==2179.0
S['S072']['polygon_px']=[list(q) for q in list(parts[0].exterior.coords)[:-1]]
ns=copy.deepcopy(S['S072']);ns.update(id='S131',name='出住院办理南侧连接通道',polygon_px=[list(q) for q in list(parts[1].exterior.coords)[:-1]])
ns['polygon_px']=[[1868.91,2119.89],[2005.61,2119.89],[2005.61,2180],[1868.91,2180]]
D['spaces'].append(ns);S['S131']=ns
p=unary_union([Polygon(S['S082']['polygon_px']),box(1860,2187.12,1943,2400.01)])
S['S082']['polygon_px']=[list(q) for q in list(p.exterior.coords)[:-1]]
for rid in ['R034','R035','R037','R038']:change(rid,target='S032')
change('R040',type='shared_wall')
change('R044',target='S052');change('R045',target='S052')
# 消控室实际北向独立门：删除隔着卫生间的旧直达边，原关系保存在外部变更记录。
changes.append({'removed':copy.deepcopy(R['R050']),'reason':'消控室与S044不直接相邻；北侧独立门清晰。'})
D['relations'].remove(R.pop('R050'))
# 急诊护士站、UPS下方与抢救区入口对应的轮廓。
rect('S096',721.57,2525.5,813.45,2588.24)
S['S094']['polygon_px']=[[885.16,2406.73],[1039.78,2406.73],[1039.78,2630.82],[817.93,2630.82],[817.93,2525.5],[885.16,2525.5]]
S['S091']['polygon_px']=[[622.97,2406.73],[717.09,2406.73],[717.09,2592.72],[813.45,2592.72],[813.45,2635.3],[885.16,2635.3],[885.16,2715.97],[622.97,2715.97]]
change('R097',target='S096');change('R098',target='S094');change('R124',target='S083')
# 东门斗：上为电梯前室，下门直接通机房；机房南侧为墙。
rect('S121',2496.37,2406.73,2601.69,2586)
rect('S122',2496.37,2590,2601.69,2675)
rect('S123',2496.37,2679,2601.69,2839.22)
change('R131',target='S123');change('R132',type='shared_wall')
change('R135',source='S125')
# 南门斗实在3153—3236：原3240—3332为门外雨篷/入口平台，不作室内节点。
rect('S089',1447.62,3152.95,1667.23,3235.86)
rect('S088',1138.38,3152.95,1443.14,3235.86)
ns=copy.deepcopy(S['S088']);ns.update(id='S130',name='南侧入口东侧连接通道',polygon_px=[[1671.71,3152.95],[1967.51,3152.95],[1967.51,3235.86],[1671.71,3235.86]])
D['spaces'].append(ns);S['S130']=ns
for rid in ['R126','R136','R137']:change(rid,target='S130')
R['E01']['position_px']=[1557.43,3240]
# 手工逐门定位，坐标均来自本图可见门洞。无门区域连续不自动生成坐标。
pts={
'R001':[(570,1214)],'R002':[(694,1214)],'R004':[(902,1214)],'R005':[(1117,1146),(1165,1146)],
'R006':[(570,1294)],'R007':[(699,1294)],'R008':[(842,1294)],'R009':[(989,1294)],'R011':[(1065,1240)],
'R015':[(644,1506),(1144,1506)],'R016':[(619,1715)],'R017':[(696,1591)],'R018':[(844,1591)],'R019':[(1054,1591)],
'R020':[(617,1864)],'R021':[(617,1900)],'R023':[(617,2098)],'R024':[(673,1976)],'R025':[(673,1889)],
'R026':[(673,1817)],'R028':[(1247,1560),(1247,2146)],'R029':[(1009,1866)],'R032':[(1097,2119)],'R033':[(1153,2119)],
'R034':[(692,2344),(760,2344),(805,2344)],'R035':[(969,2344),(1028,2344)],'R039':[(1097,2020)],
'R041':[(1141,2371)],'R042':[(645,2190)],
'R044':[(2115,1289)],'R045':[(2160,1289)],'R047':[(2650,1290)],'R048':[(2201,1212)],
'R051':[(2401,1197)],'R052':[(2401,1054),(2401,1108)],'R054':[(2003,1037)],
'R056':[(2236,1374)],'R057':[(2436,1374)],'R058':[(2187,1420)],
'R061':[(1917,1670)],'R062':[(1964,1670)],'R063':[(2042,1670)],'R064':[(2097,1670),(2438,1645)],
'R065':[(1986,1734)],'R066':[(2438,1752)],'R067':[(2489,1715)],'R068':[(2492,1832)],'R069':[(2492,1890)],
'R071':[(2492,2130)],'R072':[(2438,2130)],'R073':[(1865,1700)],'R074':[(2465,2184)],
'R075':[(1974,2345),(2149,2345)],'R079':[(2302,2345),(2416,2345)],'R080':[(1945,2371)],
'R081':[(2107,2403),(2345,2403),(2400,2403)], # 后面拆归直接相连房间，不保留这组误归的点
'R082':[(1445,979),(1669,979)],
'R094':[(1445,3194)],
'R096':[(617,2430)],'R097':[(790,2523)],'R098':[(850,2523)],'R099':[(816,2607)],'R100':[(620,2557)],
'R102':[(886,2665)],'R103':[(953,2633)],'R104':[(850,2718)],'R105':[(645,2403)],'R106':[(1042,3119)],
'R107':[(620,2759)],'R108':[(620,2875)],'R109':[(620,2990)],'R110':[(620,3108)],
'R111':[(690,2780)],'R112':[(946,2809)],'R113':[(986,2809)],'R114':[(690,2830)],'R115':[(690,2970)],'R116':[(850,3095)],
'R117':[(676,3150)],'R118':[(739,3150)],'R119':[(861,3150)],'R121':[(948,3150)],'R122':[(986,3150)],
'R123':[(1136,3180)],'R124':[(1068,3150)],'R125':[(1172,3238)],'R126':[(1940,3238)],
'R127':[(2107,2403)],'R128':[(2345,2403)],'R129':[(2400,2403)],'R131':[(2515,2677)],
'R133':[(2562,2956)],'R135':[(2042,3150)],'R136':[(1970,3180)],
}
pts.pop('R081') # 大厅与南侧挂号厅区域连续，房间北门属于R127—R129。
# 明确的新增连接。多门仍归一条无向关系。
new_entries=[('S006','S078',[(1066,1174)]),('S036','S015',[(1160,2185)]),('S039','S078',[(1865,983)]),('S052','S080',[(1865,1343)]),('S065','S131',[(1965,2118)]),('S118','S085',[(2080,2820)]),('S119','S124',[(2365,2841)]),('S120','S124',[(2420,2841)]),('S124','S085',[(2080,2865)]),('S121','S122',[(2538,2588)]),('S130','S089',[(1669,3194)]),('S066','S131',[(2008,2140)]),('S131','S073',[(1970,2180)])]
for a,b,ps in new_entries:pts[add(a,b)]=ps
# 已确认无实体分隔的连接，仅保留概念可达。
new_concept=[add('S032','S082'),add('S084','S130')]
# 独立北向消控室入口和电梯前室东向出口，继续E编号。
for eid,target,name,pos in [('E09','S046','消防控制室北侧独立入口',[2534,1027]),('E10','S121','东侧电梯前室出口',[2602,2460])]:
 r=dict(id=eid,source=None,target=target,type='entrance',name=name,entrance_type='side',position_px=pos);D['relations'].append(r);changes.append({'new':r})
# 人工逐项记录：概念连续与仍待确认的旧边分别统计，后者不补造门位。
pending={
'R003':'管井南侧为小三角符号，是否人员门待确认。','R010':'两座楼梯之间隔着未分配的北侧间隙；旧连接未找到直接门洞。',
'R014':'护士站南侧为连续曲线边界，未辨清工作人员入口。','R022':'管井东侧小三角符号，是否人员门待确认。',
'R030':'更衣北侧未见清晰门洞；目前仅南侧通控制室的门可定位。','R031':'护士站北侧未见清晰门洞；面向大厅的服务联系不等于人员通行。',
'R037':'强电南侧小三角符号，是否可步入检修门待确认。','R038':'弱电南侧小三角符号，是否可步入检修门待确认。',
'R046':'餐包北侧类似盆具/服务开口，未辨明是否人员入口。','R053':'入口区与准备区的竖向边界符号密集，未辨明门位。',
'R055':'准备区南侧多个小间及缓冲门的归属不清，保留旧概念边待确认。','R060':'二更与库房之间未见可靠人员门位。',
'R070':'管井西侧小三角符号，是否人员门待确认。','R077':'强电南侧小三角符号，是否可步入检修门待确认。',
'R078':'弱电南侧小三角符号，是否可步入检修门待确认。','R130':'电梯前室北端为小管井/设备空间，未辨明向S072的通行口。',
}
concept={rid:'原图连续开放区域，无独立门洞，不编造定位点。' for rid in ['R012','R013','R027','R043','R049','R081','R083','R084','R085','R086','R087','R088','R089','R090','R091','R092','R093','R095','R101','R134','R137']+new_concept}
# R027为走廊向大厅的连续端部，R101为半墙护士站概念连接。
concept['R027']='影像中心内侧通道东端接候诊区，图面区域连续，无独立门洞。'
concept['R101']='半墙护士站与急诊大厅的概念联系，不从服务台边界编造门位。'
# P编号首次建立，按片区依次排列，后续续作保持稳定。
order=[]
for rid,ps in pts.items():
 for xy in ps:order.append((rid,xy))
for n,(rid,xy) in enumerate(order,1):R[rid].setdefault('openings',[]).append(dict(id=f'P{n:03d}',kind='door',position_px=list(xy)))
audit=[]
for r in D['relations']:
 if r['type']!='access':continue
 rid=r['id'];status='已定位门洞' if rid in pts else '待确认旧关系' if rid in pending else '无定位的概念连通' if rid in concept else '漏审'
 audit.append(dict(id=rid,source=r['source'],target=r['target'],status=status,evidence=pending.get(rid,concept.get(rid,'原图门扇及开口位置清晰，逐门人工定位。')),openings=r.get('openings',[])))
assert not any(x['status']=='漏审' for x in audit),[x for x in audit if x['status']=='漏审']
# 保护既有确认事实。
for s in old['spaces']:
 assert (s['name'],s['type'],s['level'])==(S[s['id']]['name'],S[s['id']]['type'],S[s['id']]['level'])
for sid in ['S034','S074']:
 assert S[sid]==next(s for s in old['spaces'] if s['id']==sid)
(P/'annotation.json').write_text(json.dumps(D,ensure_ascii=False,indent=2)+'\n')
(O/'逐关系复核.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
(O/'变更记录.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n')
print('project',P,'spaces',len(D['spaces']),'relations',len(D['relations']),'openings',len(order),'located_relations',len(pts),'pending',len(pending),'concept',len(concept))
