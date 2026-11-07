"""34号原图逐区目读的增量记录；不是自动识别或共墙造门。"""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parents[2]
SAMPLE = BASE / '标注试样/34_青岛市中心医院综合病房楼'
path = SAMPLE / 'annotation.json'
data = json.loads((ROOT / '修改前备份/annotation.json').read_text())
spaces = {s['id']: s for s in data['spaces']}
spaces['S075'].update(type='courtyard', level='open_space')

# 南墙连续；通过东侧医生通道进入西核。石膏室改接北侧通道。
retired = {'R034': '西核南墙无门，旧直连公共等候区跨墙。',
           'R049': '西药房南门落在现有东侧通道S046的范围，改经S046。',
           'R131': '石膏室南墙连续；清晰门洞位于北墙。'}
data['relations'] = [r for r in data['relations'] if r['id'] not in retired]
rels = {r['id']: r for r in data['relations']}
rels['R123']['type'] = 'service'

def access(a, b):
    number = max(int(r['id'][1:]) for r in data['relations'] if r['id'].startswith('R')) + 1
    rid = f'R{number:03}'
    r = {'id': rid, 'source': f'S{a:03}', 'target': f'S{b:03}', 'type': 'access'}
    data['relations'].append(r)
    rels[rid] = r
    return rid

new = {}
for a, b, why in [
    (23, 24, '准备室南侧左门直接进入S024；右门进入产科等候区。'),
    (44, 49, '布局推断：收费东侧狭窄通路上下连续，未画横向隔墙。'),
    (46, 49, '布局推断：办公室南侧通道延入西药房，图面连续，无独立隔墙。'),
    (75, 80, '内庭院南端有明确双扇门，庭院仍不计面积。'),
    (83, 82, '布局推断：导诊为朝东北敞口的C形服务台，保留概念进入联系。'),
    (92, 96, '配液室南墙右侧单门通向雾化室。'),
    (113, 103, '急诊药房北墙西端单门，人员从急诊输液通道进入。'),
    (116, 103, '石膏室北墙东端单门直接连向急诊输液通道。'),
    (120, 136, '布局推断：取药为柜台前开放服务区，南及西侧与大厅连续。'),
]:
    rid = access(a, b)
    new[(a, b)] = rid
    rels[rid].pop('openings', None)

for a in range(64, 74):
    corridor = 59 if a % 2 == 0 else 60
    rid = access(a, corridor)
    new[(a, corridor)] = rid

# 每行是从对应放大原图直接目读的门位；一对多门仍在同一access内。
doors = {
    'R001': [(547,785)], 'R002': [(607,785)],
    'R003': [(679,785)], 'R004': [(700,785)],
    'R005': [(878,785)], 'R006': [(1070,799)],
    'R007': [(493,904)], 'R008': [(493,1067)],
    'R009': [(461,1145)],
    'R010': [(658,880)], 'R011': [(677,880)],
    'R012': [(756,880)], 'R013': [(777,880)],
    'R014': [(853,880)], 'R015': [(903,880)],
    'R016': [(616,904)], 'R017': [(1070,963)],
    'R019': [(506,1017)], 'R020': [(604,1017)],
    'R021': [(679,1059)], 'R022': [(753,1059)],
    'R023': [(828,1059)], 'R024': [(850,1059)],
    'R025': [(605,1107)], 'R026': [(627,1107)],
    'R027': [(705,1107)], 'R028': [(728,1107)],
    'R029': [(803,1107)], 'R030': [(829,1107)],
    'R031': [(904,1107)], 'R033': [(1070,1110)],
    'R035': [(427,1271)],
    'R036': [(529,1254)], 'R037': [(548,1254)],
    'R038': [(680,1254)], 'R039': [(700,1254)],
    'R042': [(925,1258)], 'R043': [(1060,1258)],
    'R045': [(1503,790)], 'R046': [(1503,938)],
    'R047': [(1503,1030)], 'R048': [(1343,1019)],
    'R050': [(1515,1338)], 'R054': [(1531,800)],
    'R055': [(1646,785)], 'R056': [(1850,799)],
    'R057': [(1916,785)], 'R058': [(1937,785)],
    'R059': [(2070,785)], 'R060': [(2092,785)],
    'R061': [(1865,814)], 'R062': [(1865,1183)],
    'R063': [(2145,814)], 'R064': [(2145,1183)],
    'R065': [(1878,849)], 'R066': [(2132,865)],
    'R067': [(1878,887)],
    'R068': [(1985,917),(2025,917)],
    'R069': [(1944,958)], 'R070': [(2066,958)],
    'R071': [(1944,984)], 'R072': [(2066,984)],
    'R073': [(1944,1067)], 'R074': [(2066,1067)],
    'R075': [(1944,1090)], 'R076': [(2066,1090)],
    'R077': [(1944,1145)], 'R078': [(2066,1145)],
    'R079': [(1967,1183),(2048,1183)],
    'R082': [(1566,1343)], 'R083': [(1762,1343)],
    'R086': [(1183,1487),(1183,1555)],
    'R087': [(1183,1740),(1183,1885)],
    'R092': [(640,1896)],
    'R095': [(1558,1463),(1587,1463)],
    'R096': [(2030,1463),(2074,1463)],
    'R098': [(1727,1627)], 'R099': [(1783,1627)],
    'R100': [(1806,1627)],
    'R101': [(1728,1545)], 'R102': [(1783,1545)],
    'R103': [(1405,1455)], 'R104': [(1430,1640)],
    'R106': [(1481,1796)], 'R107': [(1728,1796)],
    'R108': [(1594,1837)], 'R111': [(1836,1885)],
    'R112': [(1836,1815)], 'R113': [(1536,1667),(1608,1667)],
    'R114': [(2008,1667)], 'R115': [(2088,1667)],
    'R116': [(1875,1837)], 'R117': [(1915,1850)],
    'R118': [(1915,1898)], 'R119': [(2113,1937)],
    'R124': [(1241,1983)], 'R125': [(1378,1964)],
    'R126': [(1194,2062)], 'R127': [(1295,2062)],
    'R128': [(1318,2062)], 'R129': [(1567,1990)],
    'R130': [(1668,1990)], 'R132': [(1836,2143)],
    'R133': [(1836,2018)],
    'R134': [(1224,2128)], 'R135': [(1247,2128)],
    'R136': [(1326,2128)], 'R137': [(1350,2128)],
    'R138': [(1430,2128)], 'R139': [(1454,2128)],
    'R140': [(1534,2128)],
    'R141': [(2032,2022)], 'R142': [(2032,2044)],
    'R143': [(2002,2104)], 'R144': [(2070,2117)],
    new[(23,24)]: [(506,1107)],
    new[(75,80)]: [(1642,1343)],
    new[(92,96)]: [(1808,1545)],
    new[(113,103)]: [(1443,1930)],
    new[(116,103)]: [(1773,1930)],
}
ys = [958,984,1067,1090,1145]
for a in range(64,74):
    c = 59 if a % 2 == 0 else 60
    doors[new[(a,c)]] = [(1878 if c==59 else 2132, ys[(a-64)//2])]

open_passages = {'R044': [(1070,1274)], 'R081': [(2010,1343)],
                 'R085': [(1067,1578)]}
pid = 0
for rid in sorted(rels, key=lambda r:int(r[1:])):
    r = rels[rid]
    r.pop('openings', None)
    for kind, points in [('door',doors.get(rid,[])),
                         ('open_passage',open_passages.get(rid,[]))]:
        for point in points:
            pid += 1
            r.setdefault('openings',[]).append(
                {'id': f'P{pid:03}', 'kind': kind, 'position_px': list(point)})

for eid, target, name, typ, point in [
    ('E004','S033','西侧交通核出入口','secondary',[310,1140]),
    ('E005','S046','北侧药房工作出入口','staff_service',[1515,705]),
]:
    data['relations'].append({'id':eid,'source':None,'target':target,'type':'entrance',
                             'name':name,'entrance_type':typ,'position_px':point})

# 二次按门扇方向及双方多边形审计，保留已经分配的P号。
rels['R017']['source'] = 'S022'
rels['R129']['target'] = 'S121'
rels['R130']['target'] = 'S121'
rels[new[(113,103)]]['target'] = 'S136'
rels[new[(113,103)]]['openings'][0]['position_px'] = [1430,1940]
stone = rels.pop(new[(116,103)])
data['relations'].remove(stone)
stone.update(id='R131',source='S116',target='S136')
stone['openings'][0]['position_px'] = [1785,1940]
data['relations'].append(stone)
rels['R131'] = stone
retired.pop('R131')
prep = access(63,74)
rels[prep]['openings'] = [rels['R068']['openings'].pop(0)]
shop = access(81,85)
rels[shop]['openings'] = [rels['R086']['openings'].pop(1)]
rels['R048']['source'] = 'S049'
rels['R048']['openings'][0]['position_px'] = [1353,1030]
rels['R081']['openings'][0]['position_px'] = [1930,1343]
for opening, x in zip(rels['R096']['openings'], [1976,2023]):
    opening['position_px'] = [x,1463]
rels['R113']['target'] = 'S097'
side = access(98,99)
rels[side]['openings'] = [rels['R113']['openings'].pop(1)]
rels['R113']['openings'][0]['position_px'] = [1534,1682]
rels[side]['openings'][0]['position_px'] = [1602,1682]
for sid, old, x in [('S097',1524,1534),('S098',1524,1534),
                    ('S098',1616,1602),('S099',1616,1602)]:
    for point in spaces[sid]['polygon_px']:
        if point[0] == old:
            point[0] = x
rels['R122']['type'] = 'shared_wall'
rels['R123']['type'] = 'shared_wall'

path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
state = json.loads((ROOT/'review_state.json').read_text())
state['checks'].update(connectivity_reviewed=True,visual_reviewed=False)
state['review_scope'] = '主要功能空间、公共交通、入口；名称仍有三项待确认。'
state['retired_relations'] = retired
state['relation_adjustments'] = [
    {'id':'R123','reason':'服务台为柜台联系，不据此认定人员穿行。'},
    {'space_id':'S075','reason':'原图写内庭院，统一courtyard/open_space，不计面积；名称保留。'},
    {'id':'R017','reason':'门位属于S022与公共区，改端点；妇科候诊经现有S016—S022概念联系接入。'},
    {'id':prep,'reason':'原R068的西门实际属于准备S063，东门才属于门诊手术S062。'},
    {'id':shop,'reason':'电梯厅北侧西门开入开放商店S081，不跨商店直连大厅S082。'},
    {'id':'R129','reason':'财务南门进入挂号收费S121，不能越过收费区连大厅。'},
    {'id':'R130','reason':'办公南门进入挂号收费S121，不能越过收费区连大厅。'},
    {'id':'R131','reason':'二次精读纠正初判：门在石膏室东墙，不是北墙；保留原空间对并定位。'},
    {'id':new[(113,103)],'reason':'二次精读：药房门在西墙，连接S136，不跨过采血化验连S103。'},
    {'id':'R048','reason':'收费门实际位于东侧墙，接西药房侧窄通路S049。'},
    {'id':'R113','reason':'急诊配液北墙连续，两门分别开在东西侧，改接急诊儿童/成人输液。'},
    {'id':side,'reason':'急诊配液东门接急诊成人输液；配液左右墙依原图修正，S号不变。'},
    {'ids':['R122','R123'],'reason':'咖啡/服务台与急救大厅之间是连续实墙，只记共墙，不记通行或服务窗口。'}]
state['layout_inferences'] = [
    {'relation_id':new[(44,49)],'basis':'收费东侧窄通路上下连续。'},
    {'relation_id':new[(46,49)],'basis':'东侧通道南段与西药房图面连续。'},
    {'relation_id':new[(83,82)],'basis':'C形导诊台东北侧有敞口，无独立小门位置。'},
    {'relation_id':new[(120,136)],'basis':'取药柜台前公共区域与大厅连续。'},
]
state['not_required_details'] = [
    {'spaces':['S035','S036','S037','S038','S040','S121'],
     'reason':'柜台内部办公/值班入口未充分表达；保留服务关系，不为全图连通补造门或追问内部小门。'},
    {'spaces':['S106','S107'],
     'reason':'男女卫共用内部前部空间，保留到通道的概念联系；不把共同前区门重复绑定成两个房门。'},
    {'spaces':['S039','S085','S104'],
     'reason':'整体交通核保留外部接口，电梯门和楼梯内部路径不继续细分。'},
]
state['opening_audit'] = {'method':'逐区放大本图目读近似门洞中心；未从质心/共墙中点生成。',
                         'panels':['A_妇产.png','B_药房外科.png','C_输液.png','D_急诊.png'],
                         'located_openings':pid}
(ROOT/'review_state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'spaces':len(data['spaces']),'relations':len(data['relations']),
                  'openings':pid,'retired':retired},ensure_ascii=False,indent=2))
