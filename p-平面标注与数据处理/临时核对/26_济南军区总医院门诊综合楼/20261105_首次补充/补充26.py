from pathlib import Path
import json, importlib.util
import xml.etree.ElementTree as ET

ROOT = Path('/Users/hushili/Documents/研究-论文写作/大论文/p-平面标注与数据处理')
P = ROOT/'标注试样/26_济南军区总医院门诊综合楼'
W = ROOT/'临时核对/26_济南军区总医院门诊综合楼/20261105_首次补充'
SKILL = Path('/Users/hushili/.codex/skills/outpatient-plan-annotation')
spec = importlib.util.spec_from_file_location('annotation_tools', SKILL/'scripts/annotation_tools.py')
at = importlib.util.module_from_spec(spec)
spec.loader.exec_module(at)
d = json.loads((W/'补充前备份/annotation.json').read_text())
original = json.loads(json.dumps(d))
ss = {s['id']:s for s in d['spaces']}

# Only clear image readings are synchronized; the rest remain unknown.
names = {
 'S015':('值班室','staff_support'),
 'S054':('医生值班室','staff_support'),
 'S059':('抢救室','resuscitation'),
 'S070':('B超','imaging'),
 'S097':('配电房','building_services'),
 'S101':('诊室','consultation'),
 'S102':('诊室','consultation'),
 'S104':('诊室','consultation'),
 'S105':('诊室','consultation'),
}
for sid,(name,typ) in names.items():
    ss[sid]['name'],ss[sid]['type'] = name,typ
d['spaces'].append(dict(id='S113',name='值班室东侧通道',type='corridor',level='open_space',scope=ss['S083']['scope'],polygon_px=[[1760,1657],[1800,1657],[1800,1856],[1760,1856]]))

# Replace demonstrably wrong endpoints, preserving relation IDs and recording the diff externally.
fix = {
 'R030':('S036','S044'),
 'R052':('S039','S037'),
 'R053':('S042','S037'),
 'R057':('S050','S051'),
 'R059':('S053','S113'),
 'R060':('S054','S113'),
 'R066':('S083','S078'),
 'R078':('S063','S062'),
 'R085':('S079','S080'),
 'R088':('S083','S085'),
 'R103':('S071','S103'),
 'R109':('S071','S083'),
 'R112':('S110','S111'),
}
# These old edges cross intervening units or a wall; no replacement is invented.
drop = {'R008','R054','R058','R063','R068','R086','R087','R100','R108','R111'}
d['relations'] = [r for r in d['relations'] if r['id'] not in drop]
for r in d['relations']:
    if r['id'] in fix:r['source'],r['target']=fix[r['id']]

new = [
 ('R138','S003','S007'),('R139','S011','S007'),
 ('R140','S023','S021'),('R141','S047','S113'),
 ('R142','S113','S083'),('R143','S083','S106'),
 ('R144','S079','S082'),('R145','S081','S082'),
 ('R146','S098','S097'),('R147','S083','S108'),
 ('R148','S107','S109'),('R149','S059','S064'),
 ('R150','S059','S065'),('R151','S071','S059'),
 ('R152','S076','S079'),('R153','S077','S080'),
 ('R154','S057','S071'),('R155','S037','S051'),
 ('R156','S013','S035'),('R157','S011','S035'),
]
for rid,a,b in new:d['relations'].append(dict(id=rid,source=a,target=b,type='access'))
d['relations'].append(dict(id='E007',source=None,target='S112',type='entrance',name='底部服务门厅入口',entrance_type='support_entrance',position_px=[1942,2705]))

# Hand-read door centers. Never derive openings from centroids or shared walls.
doors = {
 'R001':[(536,523)],'R002':[(593,519)],'R003':[(819,524)],
 'R004':[(864,523),(957,523)],'R005':[(1017,523),(1250,523),(1346,523)],
 'R006':[(530,577)],'R007':[(646,577),(910,577)],
 'R009':[(536,734)],'R010':[(580,687),(798,687)],'R011':[(1120,687)],
 'R012':[(1178,809)],'R013':[(1270,809)],'R014':[(1375,548)],
 'R015':[(1420,523)],'R016':[(1518,523)],'R017':[(1618,523)],
 'R018':[(1815,523)],'R019':[(1902,523)],'R020':[(1400,577),(1498,577)],
 'R022':[(1818,577)],'R023':[(1904,577)],'R024':[(1910,704)],
 'R025':[(1885,809)],'R026':[(1885,1177)],
 'R032':[(1455,1385)],'R036':[(1840,1419),(1870,1419)],'R037':[(1970,1419)],
 'R039':[(2046,1418)],'R040':[(2098,1378)],
 'R041':[(1517,1652),(1562,1652)],'R042':[(1325,1652)],
 'R043':[(1840,1652)],'R044':[(1960,1652)],
 'R050':[(780,1355)],'R051':[(780,1715)],
 'R055':[(1354,1680)],'R056':[(1354,1740)],
 'R059':[(1757,1720)],'R060':[(1757,1825)],
 'R065':[(1485,2215)],'R066':[(1757,2238)],'R067':[(1568,2215)],
 'R069':[(475,2065)],'R070':[(685,2180)],'R071':[(685,2440)],
 'R072':[(719,2391)],'R073':[(819,2391)],'R074':[(963,2391)],
 'R075':[(1060,2180)],'R076':[(1060,2240)],'R077':[(1205,2196)],
 'R078':[(1252,2250)],'R079':[(1090,2391)],'R080':[(1188,2391)],
 'R081':[(1280,2391)],'R082':[(1404,2391)],
 'R083':[(1506,2399)],'R084':[(1757,2350)],'R085':[(1548,2300)],
 'R088':[(1804,2040)],'R089':[(1916,2115)],'R090':[(1916,2184)],
 'R091':[(1916,2245)],'R092':[(1916,2320)],'R093':[(1916,2393)],
 'R094':[(1916,2457)],'R095':[(1960,1946)],
 'R097':[(596,2553)],'R098':[(520,2617)],'R099':[(685,2530)],
 'R101':[(876,2554)],'R102':[(932,2554)],'R103':[(1346,2493)],
 'R104':[(1096,2522)],'R105':[(1096,2675)],
 'R106':[(1377,2520)],'R107':[(1377,2676)],'R110':[(1578,2640)],
 'R112':[(1835,2590)],'R113':[(1900,2667)],
 'R138':[(746,523)],'R139':[(1340,577)],'R140':[(1550,577)],
 'R143':[(1518,2493)],'R144':[(1548,2374)],'R145':[(1639,2374)],
 'R146':[(811,2554)],'R147':[(1720,2493)],'R148':[(1783,2554)],
 'R149':[(719,2278)],'R150':[(819,2278)],'R151':[(985,2180)],
 'R152':[(1504,2277)],'R153':[(1570,2277)],'R154':[(1020,2065)],
 'R156':[(1125,1000)],'R157':[(1180,1000)],
}
# Only distinct, visible architectural openings are positioned.
passages = {'R038':[(1995,1518)],'R141':[(1780,1652)],'R142':[(1780,1864)],'R109':[(1465,2444)]}
pi=0
for r in d['relations']:
    pts=doors.get(r['id'],passages.get(r['id'],[]))
    if pts:
        r['openings']=[]
        for xy in pts:
            pi+=1
            r['openings'].append(dict(id=f'P{pi:03}',kind='open_passage' if r['id'] in passages else 'door',position_px=list(xy)))

at.normalize(d)
(P/'annotation.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
at.render(d,P/'annotation.json',P/'标注.svg')
# Keep small P labels readable in raster previews with white outlines.
tree=ET.parse(P/'标注.svg')
for node in tree.iter():
    if node.tag.endswith('text') and node.text and __import__('re').fullmatch(r'P\d{3,}',node.text):
        node.set('stroke-width','0.65')
tree.write(P/'标注.svg',encoding='utf-8',xml_declaration=True)
at.summary(d,W/'更新后概览.md')
changed=[]
oldrels={r['id']:r for r in original['relations']}
for r in d['relations']:
    if r['id'] in oldrels and any(r[k]!=oldrels[r['id']].get(k) for k in ('source','target')):
        changed.append(dict(id=r['id'],before=oldrels[r['id']],after=r))
record=dict(image_read_names=names,added_spaces=['S113'],endpoint_corrections=changed,removed_relations=[r for r in original['relations'] if r['id'] in drop],added_relations=[r['id'] for r in d['relations'] if r['id'] not in oldrels],openings=pi)
(W/'本轮变更记录.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
print('spaces',len(d['spaces']),'unknown',len(at.unresolved(d)),'relations',len(d['relations']),'openings',pi)
