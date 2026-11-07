from pathlib import Path
import json
T=Path(__file__).parent;R=T.parent.parent/'标注试样/30_佛山市禅城区中心医院';p=R/'annotation.json';d=json.loads(p.read_text())
# Each point below was read from this plan, not computed from polygon boundaries.
# Historical erroneous internal chains are removed; their IDs stay retired.
removed=[r for r in d['relations'] if r['id'] in ['R089','R090']]
d['relations']=[r for r in d['relations'] if r['id'] not in ['R089','R090']]
new=[('R116','S084','S075'),('R117','S083','S088'),('R118','S084','S088'),('R119','S085','S089')]
for rid,a,b in new:
 if not any(r['id']==rid for r in d['relations']):d['relations'].append(dict(id=rid,source=a,target=b,type='access'))
# Approximate opening centers in original pixels. Leave uncertain positions unlocated.
points={
'R001':(1690,420),'R002':(1451,420),'R003':(1531,420),'R004':(1267,420),
'R005':(1610,548),'R006':(1450,548),'R007':(1546,585),'R008':(1514,585),
'R009':(1610,680),'R010':(1450,680),'R011':(1546,642),'R012':(1514,642),
'R013':(1610,818),'R014':(1450,818),'R015':(1545,818),
'R016':(1708,892),'R017':(1580,892),'R018':(1455,892),
'R019':(1698,1032),'R020':(1575,1032),'R021':(1447,1032),
'R022':(1418,1094),'R023':(1546,1094),'R024':(1443,1094),
'R025':(1700,1225),'R026':(1550,1225),'R027':(1445,1225),
'R030':(1337,614),'R031':(1337,1065),'R033':(1203,1060),
'R036':(1728,386),'R037':(1728,1250),
'R038':(2057,456),'R039':(1927,456),'R040':(1845,456),
'R041':(1926,510),'R042':(1925,725),'R043':(1924,725),'R044':(1840,737),
'R045':(1926,665),'R046':(1780,587),'R047':(2055,665),
'R051':(1791,823),'R052':(1800,924),'R054':(1781,1105),'R055':(1807,1217),
'R056':(1754,1280),'R057':(1754,1495),'R058':(1795,1495),
'R059':(1797,1800),'R060':(1786,1680),'R061':(1786,1742),'R063':(1783,2028),
'R064':(1728,1614),
'R065':(913,585),'R067':(803,695),'R068':(913,615),'R069':(929,818),'R070':(1085,774),
'R071':(803,898),'R072':(741,580),'R073':(741,740),'R074':(741,895),
'R076':(967,880),'R077':(967,916),'R078':(967,1032),'R079':(967,1070),'R080':(967,1192),
'R083':(1068,1325),'R085':(803,1370),'R086':(1085,1380),
'R087':(1203,1627),'R091':(1254,1655),'R094':(1728,1923),
'R095':(1278,1745),'R096':(1203,1760),'R100':(1203,1388),
'R116':(1279,1655),'R117':(1254,1745),'R118':(1279,1745),'R119':(1355,1745)
}
# Restrict this pass to unambiguous doors, skipping ambiguous internal equipment routes.
skip={'R005','R006','R009','R010','R022','R023','R042','R043','R044','R051','R052','R060','R061','R065','R067','R068','R069','R078','R079','R117','R118','R119'}
# Correct clear original-image coordinates after comparison with enlarged source crops.
points.update({'R005':(1610,548),'R006':(1450,548),'R009':(1610,680),'R010':(1450,680)})
used=[]
for rid,pos in points.items():
 if rid in skip:continue
 r=next(r for r in d['relations'] if r['id']==rid)
 if r.get('openings'):continue
 pid=f'P{len(used)+1:03d}'
 r['openings']=[dict(id=pid,kind='door',position_px=list(pos))];used.append((rid,pid,list(pos)))
p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
(T/'本轮关系变更记录.json').write_text(json.dumps({'removed':removed,'added':new,'located':used,'note':'门位为本图目视近似值；未定位概念连接并不表示不连通。'},ensure_ascii=False,indent=2)+'\n')
print('removed',len(removed),'added',len(new),'located',len(used),'relations',len(d['relations']))
