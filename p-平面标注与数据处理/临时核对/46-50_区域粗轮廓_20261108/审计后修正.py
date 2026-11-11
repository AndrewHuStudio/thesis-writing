from pathlib import Path
import json
O=Path(__file__).resolve().parent

def edit(n,fn):
 p=O/f'配置{n}.json';d=json.loads(p.read_text());fn(d);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def a(d):
 d['doors']['4']=[2100,617];d['doors']['9']=[1565,903];d['doors']['14']=[963,765]
 d['doors']['16']=[2220,722];d['doors']['21']=[2220,890];d['doors']['30']=[1080,1055]
 d['doors'].pop('37');d['doors']['39']=[1310,1166];d['doors']['40']=[1484,1125]
 d['doors']['53']=[1599,1143];d['doors']['60']=[[1965,1345],[1965,1178]];d['doors']['70']=[2020,1159]
 d['update_relations']={'23':{'source':'S018'},'24':{'source':'S018'}}
 d['new_relations']=[[4,30,'access','留观小间北侧清晰门口直接接门厅']];d['doors']['106']=[1405,903]
edit('46',a)
def b(d):
 d['new_spaces']=[s for s in d['new_spaces'] if s['id']!='S073']
 for s in d['new_spaces']:
  if s['id']=='S071':s['rect']=[1785,1675,1885,1815]
  if s['id']=='S072':s['rect']=[1785,1815,1885,1953]
 d['subtract']=[x for x in d['subtract'] if not (x[0]==34 and x[1][0]==1785)]
 d['subtract'] += [[34,[1785,1675,1885,1815]],[34,[1785,1815,1885,1953]]]
 d['new_relations']=[x for x in d['new_relations'] if x[0]!=73]
 for r in d['regions']:r[1]=[i for i in r[1] if i!=73]
 d['update_relations'].update({'3':{'target':'S041'},'26':{'source':'S035'}})
 d['remove_relations']={'24':'原公共通道与儿科关系在拆房后跨越附属办公间；保留等候大厅实际入口。','59':'细小附间门向不明，本轮不强补可达。','60':'细小附间门向不明，不按共墙连接。'}
 d['doors'].pop('7');d['doors'].pop('24')
 d['doors'].update({
 '43':[932,600],'44':[932,655],'45':[1188,635],'46':[1950,625],'47':[2009,625],'48':[2089,625],'49':[2220,690],
 '50':[2050,760],'51':[932,755],'52':[932,1080],'53':[1018,755],'54':[1018,845],'55':[1018,940],
 '56':[1018,1075],'57':[984,1430],'58':[984,1495],'61':[932,1530],'63':[1250,1575,'open_passage'],
 '64':[932,1750],'65':[932,1810],'66':[1110,1785],'67':[1200,1785],'68':[1280,1785],
 '69':[980,1855],'70':[1080,1855],'71':[1150,1855],'72':[1270,1855],'73':[1380,1855],
 '74':[1450,1853],'75':[1668,1853],'76':[1700,1855],'77':[1785,1695],'78':[1785,1830]})
edit('47',b)
def c(d):
 d['update_relations']={'30':{'source':'S059'},'34':{'target':'S066'},'66':{'target':'S090'}}
 for k,p in {'34':[2670,1275],'39':[2930,1170],'51':[455,1677],'52':[905,1504]}.items():d['doors'][k]=p
edit('48',c)
def e(d):
 d['update_relations']={'9':{'source':'S016'},'44':{'source':'S038'},'45':{'source':'S038'},'68':{'source':'S052'}}
 d['remove_relations']={'46':'肠道门诊分诊与北侧分段间隔有公共区域；保留其到S037/S038的实际连接。','67':'两个大厅分段之间隔有S052；通过既有连续通道连接，不跨节点直连。'}
 d['doors']['14']=[1028,950];d['doors']['22']=[[1080,1066],[1385,1066]];d['doors']['43']=[698,1183]
 d['doors'].pop('81');d['doors']['86']=[1150,1689];d['doors']['68']=[800,1689]
edit('49',e)
def f(d):
 d['remove_relations']={'107':'辅助卫生小间的入口证据不清，不跨越其他卫生间和内向空区接通道。'}
 d['doors'].pop('107');d['doors']['114']=[375,923]
edit('50',f)
# 47号更正本轮草稿误将一个办公间的家具分界当墙；原稿S001—S037不受影响。
p=next(O.glob('47_*/review_state.json'));s=json.loads(p.read_text())
(O/p.parent.name/'草稿新增编号修正前.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
s['name_items']=[i for i in s.get('name_items',[]) if i['space_id']!='S073']
s['regions']=[]
p.write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
