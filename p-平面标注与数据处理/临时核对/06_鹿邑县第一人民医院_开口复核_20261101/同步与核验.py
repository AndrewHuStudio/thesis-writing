from pathlib import Path
import json,copy
from shapely.geometry import Polygon,box,Point
from shapely.ops import unary_union
BASE=Path(__file__).resolve().parent
PROJECT=BASE.parent.parent/'标注试样/06_鹿邑县第一人民医院整体迁建项目'
d=json.loads((BASE/'修改前备份/annotation.json').read_text());old=copy.deepcopy(d)
ss={s['id']:s for s in d['spaces']}; rr={r['id']:r for r in d['relations']};log=[]
def geom(sid,points,basis):
 ss[sid]['polygon_px']=points;log.append({'action':'geometry','space':sid,'basis':basis})
def extend(sid,rect,basis):
 p=unary_union([Polygon(ss[sid]['polygon_px']),box(*rect)])
 assert p.geom_type=='Polygon' and not p.interiors,(sid,p.geom_type)
 geom(sid,[[x,y] for x,y in list(p.exterior.coords)[:-1]],basis)
def relation(rid,a,b,typ='access',basis=''):
 prev=copy.deepcopy(rr.get(rid)); rr[rid]={'id':rid,'source':a,'target':b,'type':typ};log.append({'action':'relation','before':prev,'after':rr[rid],'basis':basis})
def remove(rid,basis):
 log.append({'action':'remove','before':rr.pop(rid),'basis':basis})
# 在门位判读后补齐原有概念轮廓漏掉的短通道，不从几何自动生成开口。
geom('S032',[[1514,929],[1606,929],[1606,1022],[2425,1022],[2425,850],[2209,850],[2209,863],[2150,863],[2150,850],[1514,850]],'交通核北侧大厅下边界补齐；原凹口漏掉门前约28像素的大厅。')
geom('S057',[[1630,1625],[1665,1625],[1665,1701],[2029,1701],[2029,1828],[1671,1828],[1671,1874],[1630,1874]],'休闲区西侧连续侧廊延伸至住院大厅南门与西连接廊，未跨入桥体。')
geom('S058',[[2040,1701],[2270,1701],[2270,1625],[2310,1625],[2310,1830],[2270,1830],[2270,1828],[2040,1828]],'休闲区东侧连续侧廊补齐，住院大厅南门直接朝此侧廊。')
extend('S037',(3341,1202,3390,1296),'卫生间西侧通往北东通道的短前厅原未覆盖。')
geom('S045',[[2961,1120],[3101,1120],[3101,1192],[2965,1192],[2965,1229],[2911,1229],[2911,1192],[2961,1192]],'补入开水房西侧与医保后廊连续的小前厅，避开下方卫生间。')
extend('S112',(2719,2170,2769,2273),'核磁控制区实际向南延伸至打印室西侧，原矩形漏掉开放工作带。')
geom('S150',[[1356,2759],[1404,2759],[1404,2694],[1452,2694],[1452,2870],[1356,2870]],'补入治疗门东侧与注射间南、东侧的护士工作通道；避开注射间。')

# 登记柜台东侧通行带须独立，避免带孔多边形或跨柜台连接。
new={'id':'S299','name':'影像登记东侧通道','type':'corridor','level':'open_space','scope':ss['S116']['scope'],'polygon_px':[[2524,2346],[2550,2346],[2550,2497],[2524,2497]]}
d['spaces'].append(new);ss['S299']=new
log.append({'action':'add_space','space':'S299','basis':'原图登记柜台与片库门之间可辨通行带，原S116在此挖除的范围大于柜台。'})
remove('R063','值班室北墙未见朝更衣通道的门；实际通过东侧准备间及南侧大厅进入，不跨墙直连。')
remove('R174','影像交通核西侧下部门实际朝北侧通道S185，不能跳过S185直连S197。')
remove('R094','值班S153北墙未见通急诊横通道的门；实际人员门在西侧通S152。')
relation('R184','S218','S227',basis='女卫生间北侧人员门位于交通核S218南沿，不跳接东侧药房内部通道。')
relation('R102','S063','S139',basis='电梯厅东侧双扇门直接朝西侧医疗街；不把此门归到输液区。')
relation('R203','S252','S247','shared_wall','注射间南侧为连续隔墙；清晰人员门位于西侧，通配药S246。')
relation('R216','S262','S283','service','护士站东侧为柜台服务界面；人员门在西侧配剂室一侧。')
remove('R213','护士站S281东侧为服务界面；南侧与儿科横向通道连续，不跳过S285直连S262。')
relation('R317','S299','S130',basis='片库西侧单门直接朝登记柜台东侧通行带，非穿过柜台。')
relation('R376','S133','S090',basis='值班S090南侧双扇门直接朝急诊大厅。')
relation('R377','S063','S146',basis='静脉输液大厅东侧双扇门直接朝医疗街；西侧另有通向留观区的门。')
relation('R378','S246','S247',basis='注射间西侧清晰单扇门开向配药间。')
relation('R379','S272','S262',basis='儿科办公室东侧双扇门朝公共通道，与西侧内通道门分记。')
relation('R380','S116','S299',basis='登记东侧短通行带北、南端均与影像等候厅连续，柜台无可穿行假设。')
relation('R381','S285','S281',basis='护士站南侧无实体分隔，直接接儿科横向通道；不编造门位。')
relation('R383','S222','S224',basis='西药药房南侧东部双扇门直接接中药，不跨过中药跳接内部通道。')
relation('R382','S262','S281','service','护士站东侧柜台服务界面。')
# 本轮发现但无法确证的既有边，从事实关系移至外部/MD核对，不混作确定连接。
for rid,basis in [('R043','男更北侧人员入口未见清晰开口，保留L08待确认。'),('R247','两休闲区之间竖向分隔连续，可否穿行保留L09待确认。'),('R212','值班诊室北/东入口门位和直接目标不清，保留L10待确认。')]:remove(rid,basis)
records=[]
skip={('S033','S035'),('S185','S186')}
fix={
 ('S002','S016',505,1265):(520,1260),('S002','S024',940,1300):(940,1310),
 ('S033','S057',1665,1640):(1635,1624),('S033','S058',2260,1640):(2290,1624),
 ('S079','S082',1570,2248):(1590,2239),('S090','S092',830,2543):(803,2480),
 ('S085','S133',745,2595):(870,2570),('S090','S084',830,2459):(803,2430),
 ('S135','S139',1655,2650):(1655,2650),
 ('S133','S151',915,2890):(851,2910),('S136','S137',1032,2596):(973,2618),
 ('S144','S150',1345,2752):(1352,2762),('S145','S150',1380,2775):(1380,2758),
 ('S188','S199',2470,2970):(2373,2970),('S188','S205',2470,3055):(2373,3055),
 ('S187','S190',2500,2690):(2555,2690),('S219','S224',1040,3970):(1056,3965),
 ('S262','S279',2985,3978):(3082,3990),('S285','S262',2860,4091):(2720,4091),
 ('S285','S286',2284,4190):(2350,4150),('S289','S293',2990,4218):(2934,4250),
 ('S263','S262',2986,3908):(2970,3775)
}
for line in (BASE/'目视开口记录.tsv').read_text().splitlines():
 a,b,k,x,y=line.split();x=int(x);y=int(y)
 if (a,b) in skip or (a,b) in [('S068','S090'),('S151','S153'),('S262','S276'),('S262','S283'),('S151','S134')]:continue
 x,y=fix.get((a,b,x,y),(x,y))
 if (a,b)==('S219','S227'):a,b='S218','S227'
 if (a,b)==('S297','S257'):x,y=2382,3484
 if (a,b)==('S134','S143'):x,y=1144,2960
 if (a,b)==('S219','S222') and x==1105:a,b='S222','S224'
 if (a,b)==('S135','S139'):a,b='S063','S139'
 if (a,b)==('S143','S146') and x==1655:a,b='S063','S146'
 if (a,b)==('S116','S130'):a,b='S299','S130'
 records.append((a,b,k,x,y))
extra='''S133 S090 door 745 2543
S185 S186 door 3130 2630
S185 S186 door 3130 2805
S208 S200 door 2595 3135
S208 S201 door 2732 3135
S246 S247 door 2480 3255
S272 S262 door 3085 3910
S262 S282 door 2755 4060
S213 S214 door 1460 3580
S295 S216 door 1635 3590
S064 S093 door 2285 1970
S064 S116 door 2285 2250
S064 S116 door 2285 2430
S099 S104 open_passage 2480 2110
S070 S071 open_passage 1458 2020
S076 S074 door 874 2320
S068 S075 open_passage 753 2365
S211 S212 door 1810 4350
S211 S212 door 1935 4350
S211 S212 door 2050 4350
S030 S029 door 1885 815
S030 S029 door 2085 815'''
for line in extra.splitlines():
 a,b,k,x,y=line.split();records.append((a,b,k,int(x),int(y)))
pairmap={frozenset((r['source'],r['target'])):r for r in rr.values() if r['type']=='access'}
for idx,(a,b,k,x,y) in enumerate(records,1):
 r=pairmap[frozenset((a,b))];r.setdefault('openings',[]).append({'id':f'P{idx:03}','kind':k,'position_px':[x,y]})
d['relations']=list(rr.values())
(BASE/'关系与轮廓修订依据.json').write_text(json.dumps(log,ensure_ascii=False,indent=2)+'\n')
stage=BASE/'待核验成果';stage.mkdir(exist_ok=True)
(stage/'annotation.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
# 原图以不改动的链接供skill脚本读取，正式交付仍保留实际原文件。
image=stage/d['image']['file']
if not image.exists():image.symlink_to(PROJECT/d['image']['file'])
print('spaces',len(d['spaces']),'relations',len(d['relations']),'openings',len(records))
for r in d['relations']:
 for op in r.get('openings',[]):
  q=Point(op['position_px']);ds=[round(Polygon(ss[z]['polygon_px']).distance(q),1) for z in (r['source'],r['target'])]
  if max(ds)>35:print('DIST',r['id'],r['source'],r['target'],op,ds)
