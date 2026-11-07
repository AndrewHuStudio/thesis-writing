from pathlib import Path
import json
T=Path(__file__).parent;R=T.parent.parent/'标注试样/30_佛山市禅城区中心医院';p=R/'annotation.json';d=json.loads(p.read_text())
retired={'R005','R006','R009','R010','R033','R095','R119'}
record=[r for r in d['relations'] if r['id'] in retired]
d['relations']=[r for r in d['relations'] if r['id'] not in retired]
rs={r['id']:r for r in d['relations']}
# The accessible WC opens to medical street, rather than through the elevator block.
rs['R083']['target']='S016'
add=[('R120','S010','S019'),('R121','S008','S018'),('R122','S029','S028'),('R123','S026','S027'),('R124','S063','S073'),('R125','S073','S072')]
for rid,a,b in add:
 if rid not in rs:
  r=dict(id=rid,source=a,target=b,type='access');d['relations'].append(r);rs[rid]=r
fix={'R001':(1610,420),'R015':(1527,818),'R019':(1663,1032),'R020':(1531,1032),'R021':(1402,1032),'R024':(1401,1094),'R025':(1716,1225),'R026':(1585,1225),'R027':(1456,1225),'R047':(2038,638),'R055':(1778,1238),'R058':(1778,1540),'R059':(1778,1805),'R063':(1778,2040),'R076':(958,880),'R077':(958,916),'R080':(958,1192),'R083':(1085,1301),'R096':(1203,1780),'R091':(1254,1655),'R116':(1279,1655)}
for rid,pos in fix.items():
 if rs[rid].get('openings'):rs[rid]['openings'][0]['position_px']=list(pos)
# Existing P IDs retain their numbers; retired ones are not recycled.
nextp=max(int(o['id'][1:]) for r in d['relations'] for o in r.get('openings',[]))+1
more={'R022':(1664,1094),'R023':(1532,1094),'R029':(1485,773),'R032':(1253,818),'R042':(2058,725),'R043':(1925,725),'R044':(1840,725),'R051':(1818,818),'R052':(1795,879),'R054':(1778,1105),'R060':(1790,1692),'R061':(1790,1709),'R065':(913,585),'R067':(803,695),'R068':(913,615),'R069':(929,818),'R078':(958,1033),'R079':(958,1070),'R084':(1006,1325),'R117':(1259,1745),'R118':(1328,1745),'R120':(1601,548),'R121':(1467,548),'R122':(1601,680),'R123':(1467,680),'R124':(1695,1282)}
# Exclude positions whose door leaf is still obscured in the raster.
for key in ['R051','R052','R060','R061','R065','R067','R068','R069']:more.pop(key,None)
for rid,pos in more.items():
 if rs[rid].get('openings'):continue
 rs[rid]['openings']=[dict(id=f'P{nextp:03d}',kind='door',position_px=list(pos))];nextp+=1
p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
(T/'直接关系校正记录.json').write_text(json.dumps({'retired':record,'added':add,'corrected':'R083 target changed from S059 to S016','basis':'影像检查室通过独立更衣间进入候诊通道；输液支持房间分别向大厅与交通核开门，实墙不构成直接相通；庭院路径按连续布局推断。'},ensure_ascii=False,indent=2)+'\n')
print('relations',len(d['relations']),'openings',sum(len(r.get('openings',[])) for r in d['relations']))
