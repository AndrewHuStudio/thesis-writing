from pathlib import Path
import json, sys, hashlib
from shapely.geometry import Polygon, Point
ROOT=Path(__file__).resolve().parents[2]/'标注试样'/'39_梅州市蕉岭县人民医院'
OUT=Path(__file__).resolve().parent
D=json.loads((OUT/'20261107_续作前备份/annotation.json').read_text())
spaces={s['id']:s for s in D['spaces']}
# 原图坐标不变；下列判读坐标统一使用逆时针转正后的显示坐标。
def orig(x,y): return [round(2424-y,3),round(x,3)]
def display_poly(sid): return Polygon([(y,2424-x) for x,y in spaces[sid]['polygon_px']])
geom=[]
# 补足原草稿漏掉的急诊横向通道末端，未进入相邻房间。
s=spaces['S060'];s['polygon_px']=[orig(x,y) for x,y in [(289,1352),(486,1352),(486,1372),(289,1372)]]
geom.append({'space_id':'S060','reason':'原横向通道在x450处截断，补到x486，覆盖通往留观区的现有连续咽喉。'})
# 影像走廊西端真实门厅位于楼梯南侧，不经楼梯内部。
s=spaces['S072'];s['polygon_px']=[orig(x,y) for x,y in [(835,900),(878,900),(878,975),(1400,975),(1400,900),(1424,900),(1424,1014),(777,1014),(777,988),(835,988)]]
geom.append({'space_id':'S072','reason':'补入楼梯南侧x777—835、y988—1014的漏标门厅，使主通道的清晰门洞接到实际影像通道。'})
remove={'R003':'会议中心南界连续玻璃/墙体，清晰门洞在S011庭院侧，不能跨庭院直连S010。',
        'R001':'S001东侧门开向S002，不能跨过S002直接连接S005。',
        'R013':'洗衣中心北门开向S024；与S028相邻边界未见门洞。',
        'R022':'留观室与外侧楼梯之间为连续墙，楼梯通过南端候药/通行区衔接。',
        'R028':'交通核东墙连续，北侧通道应经S072与主通道衔接，不能穿过楼梯共墙。',
        'R040':'儿科西侧楼梯与儿科功能块间共墙无门，保留独立外门。'}
removed=[dict(r,reason=remove[r['id']]) for r in D['relations'] if r['id'] in remove]
D['relations']=[r for r in D['relations'] if r['id'] not in remove]
rel_by_pair={frozenset((r['source'],r['target'])):r for r in D['relations'] if r['type']=='access'}
next_r=52;next_p=1; audit=[]
def acc(a,b,points=(),kind='door',reason='原图可见门洞'):
 global next_r,next_p
 a=f'S{a:03d}';b=f'S{b:03d}';pair=frozenset((a,b));r=rel_by_pair.get(pair)
 if r is None:
  r=dict(id=f'R{next_r:03d}',source=a,target=b,type='access');next_r+=1;D['relations'].append(r);rel_by_pair[pair]=r
 for x,y in points:
  r.setdefault('openings',[]).append(dict(id=f'P{next_p:03d}',kind=kind,position_px=orig(x,y)));next_p+=1
 audit.append(dict(relation_id=r['id'],source=a,target=b,basis=reason,display_positions=list(points),kind=kind if points else None))
# A 会议中心：按真实门洞连接，柜台服务另保留。
acc(1,2,[(277.5,475)])
acc(2,5,[(308,507.5)],'open_passage','入口空间与会议中心通道连续开敞')
acc(3,5,[(410,507.5),(525,507.5)])
acc(4,5,[(543,507.5)])
acc(4,6,[(630,507.5)])
acc(5,7,[(205,565.5),(583,565.5)])
acc(7,8,[(589.5,583)])
acc(7,9,[(589.5,697),(589.5,777)])
acc(7,11,[(574,795.5)],reason='会议中心舞台南侧门洞通向庭院侧；不据此连接庭院另一侧通道。')
acc(10,12,[(205,862.5),(269,862.5)])
acc(10,13,[(292,862.5)])
acc(13,18,[(292,922.5)])
acc(12,18,(),reason='布局推断：卫生/附属空间的下部出入前厅与收费外侧通道连续，具体小门不定位。')
acc(14,18,[(330,922.5)],reason='南侧独立门洞可见，区别于挂号窗口service')
for n,x in [(15,365),(16,403),(17,441)]:
 acc(n,10,[(x,862.5)])
 acc(n,18,[(x,922.5)])
acc(18,40,[(674.5,930)],'open_passage','收费外侧通道东端与主通道连续')
acc(19,40,[(724,723.5)],'open_passage','次入口门厅与主通道连续')
acc(19,28,[(777.5,584)])
# B 后勤及太平间。
acc(28,21,[(913,564.5)],'open_passage','电梯厅南口连续')
acc(21,23,[(886.5,470),(886.5,505),(886.5,547)])
acc(21,20,[(939.5,470),(939.5,505)])
acc(28,20,[(970,564.5)])
acc(22,28,[(812,564.5)])
acc(28,32,[(812,608.5)])
acc(28,24,(),reason='布局推断：楼梯东侧后勤走道绕过核心北端连续，功能块内部转折不细分。')
acc(24,29,[(1140,494)])
acc(24,30,[(1327.5,589)])
acc(30,33,[(1245,609.5)])
acc(30,34,[(1312,609.5)])
acc(31,24,[(1365,565.5)])
acc(25,24,[(1467,565.5)])
acc(24,26,(),reason='布局推断：东端交通核的南侧厅部与后勤通道连续，保留概念连接而不虚构楼梯内部小门。')
acc(24,27,[(1707,565.5)],'open_passage','东端走道南端连续')
acc(26,27,[(1698.5,541)],'open_passage','交通核东侧厅部开敞')
acc(24,35,[(1440,609.5)],'open_passage','后勤北侧通道向南折转连续')
acc(33,35,[(1294.5,704)])
acc(34,35,[(1400.5,652)],'open_passage','东侧无完整封闭隔墙，开敞衔接南侧通道')
acc(39,71,[(1406,859.5)],reason='小间南侧原图有门洞；内部用途仍未知')
# C 急诊。
acc(40,46,[(674.5,1025)])
acc(41,46,[(277.5,1023)],'open_passage','交通核厅部向东敞开')
acc(41,47,(),reason='布局推断：急救大厅北侧入口厅与交通核整体节点的下部厅区连续，不细分核内路线。')
acc(42,46,[(340,1008.5)])
acc(44,46,[(508,1008.5)])
acc(45,46,[(579,1008.5)],'open_passage','房间组西侧出入前厅向南开敞')
acc(45,40,[(674.5,974)])
acc(47,48,[(278.5,1090)],'open_passage','两抢救大厅间开口清楚')
acc(47,53,(),reason='布局推断：半墙护士站面向急救大厅，未见独立小门，不定位。')
acc(47,54,[(260,1125.5)],'open_passage','急救大厅南侧连续进入诊疗通道')
acc(54,48,[(350,1125.5)])
acc(54,50,[(385,1125.5)])
acc(49,46,[(389,1044.5)])
acc(49,50,[(430,1108.5)])
acc(51,46,[(574,1044.5)])
acc(51,50,[(579,1108.5)],'open_passage','配套房间南侧缺口可见')
acc(50,52,[(587.5,1116)],'open_passage','电梯前厅与配套走道衔接')
acc(56,54,[(352,1151.5)])
acc(56,60,[(330,1351.5)])
acc(57,40,(),reason='布局推断：庭院东南侧附属房间组入口前厅朝主通道，内部小门不细究。')
acc(59,60,[(288.5,1360)],'open_passage','大厅与横向通道连续')
acc(60,61,[(486.5,1360)],'open_passage','横向通道东端进入留观区域连续')
acc(59,64,[(355,1531.5)])
acc(59,61,[(512,1531.5)])
acc(62,91,(),reason='布局推断：外侧楼梯通过南端落地/通行区衔接候药区域；与留观室间连续墙不作直连，未定位踏步/栏杆边界。')
acc(64,66,[(456,1480.5)],reason='护士站南侧有独立门扇，不从左右服务界面推出通行。')
acc(65,66,(),reason='布局推断：护士站北侧配套小间有出入缺口，具体小门位置不细究。')
acc(59,67,[(242,1565.5)],'open_passage','急诊厅南侧核前厅连续')
acc(59,68,[(350,1565.5)])
acc(59,69,[(535,1565.5),(620,1565.5)])
acc(59,91,[(674.5,1548)])
acc(40,58,[(799,1304.5),(833,1304.5),(870,1304.5)])
acc(40,89,[(777,1430)])
acc(40,91,[(750,1460.5)],'open_passage','公共主通道南端与候药区连续')
# D 影像、放射：科室内的小检查室仍用原功能块。
acc(40,70,[(810,860)])
acc(40,72,[(777,1000)],reason='楼梯南侧清晰门洞接入影像通道西端，补足漏标门厅后定位。')
acc(71,72,[(862,899.5),(1412,899.5)],'open_passage','两端绕行通道在房间组外连续')
acc(72,75,[(850,1014.5)],'open_passage','影像通道西端与放射候诊区连续')
acc(71,74,[(925,899.5),(1005,899.5),(1087,899.5),(1167,899.5),(1247,899.5)])
acc(72,74,[(1247,974.5)])
acc(75,77,[(912.5,1108)])
acc(72,77,[(1006,1014.5),(1083,1014.5),(1247,1014.5)])
acc(77,78,[(1008,1127.5),(1136,1127.5),(1337,1127.5)])
acc(75,78,[(912.5,1138)],'open_passage','放射科西南角绕行通道连续')
acc(78,81,[(1330,1149.5)],'open_passage','放射南侧通道东端继续衔接')
acc(78,80,[(920,1149.5),(1000,1149.5),(1082,1149.5),(1164,1149.5),(1245,1149.5)])
acc(78,82,[(1405,1149.5)],'open_passage','东端小间组北侧入口前厅可辨')
acc(40,83,[(800,1239.5),(835,1239.5),(870,1239.5)])
acc(81,85,[(1330,1239.5)],'open_passage','东端通道连续南下')
# E 超声及药房。
acc(85,86,(),reason='布局推断：电梯整体节点面向东侧走道，原图未清晰显示具体轿厢门中心。')
acc(85,87,[(1339.5,1306)],'open_passage','电梯旁整体前厅向西开敞')
acc(85,88,[(1339.5,1430)],'open_passage','成组小间出入前厅向西开敞')
acc(85,89,[(1320.5,1440)],'open_passage','超声中心东端通道与后勤走道连续')
acc(85,92,[(1339.5,1495),(1339.5,1568),(1339.5,1630)])
acc(89,90,(),reason='布局推断：超声护士站为半墙服务区，位于同一科室连续空间，不编造柜台小门。')
acc(91,93,[(923.5,1583)],reason='中药房西端独立双扇开口，不等同于取药窗口。')
acc(91,94,[(923.5,1640)],reason='西药房西端独立门洞，不等同于取药窗口。')
acc(85,93,[(1320.5,1580)])
acc(93,94,[(1265,1599.5)])
acc(91,96,[(777,1656)])
# F 入口与儿科。
acc(91,98,[(750,1685.5)],'open_passage','候药区南端与门诊大厅连续')
acc(98,100,(),reason='布局推断：岛式咨询台两侧为同一连续大厅，仅为无孔多边形而拆为两个节点。')
acc(100,104,[(523,1921)],'open_passage','主入口门斗内侧开口')
acc(100,105,[(777,1965)])
acc(105,106,[(1209.5,1991)],'open_passage','儿科东侧核前厅西南开敞')
acc(98,102,[(777,1842),(777,1870)])
# 清楚独立外门继续使用E编号，不通过室外总节点连通。
for eid,target,name,typ,xy in [
 ('E005','S097','门诊西侧独立用房外门','service',(337,1725)),
 ('E006','S107','儿科西侧楼梯外门','secondary',(800,2095)),
 ('E007','S035','后勤南侧通道外门','service',(1440,718)),
]:
 D['relations'].append(dict(id=eid,source=None,target=target,type='entrance',name=name,entrance_type=typ,position_px=orig(*xy)))
# 保留原39个固定核对号，不把候选当成已确认。
mapping=json.loads((OUT/'review_mapping.json').read_text())
state={'name_items':[dict(review_id=m['review'],space_id=m['id'],status='pending',candidates=m['candidates'],reason=m['why'],confidence=m['confidence'],group=m['group']) for m in mapping],
 'connectivity_items':[dict(review_id='K01',source='S036',target='S035',status='pending',question='S036是否经西侧细线边界与S035相通？若不是，请注明实际入口。',reason='该块北侧为连续墙，西侧细线可能是分隔/玻璃边界；现图未见可靠门洞，唯一主要入口尚不明确。')],
 'checks':{'connectivity_reviewed':True,'visual_reviewed':False},
 'removed_relations':removed,'geometry_changes':geom,'relation_evidence':audit,
 'scope':'沿用107个概念空间/功能块，不穷尽块内每间小房间；名称候选不写入核心JSON。',
 'non_target_details':['S006、S043、S079、S095及配镜中心S101缺乏可定位内部小门，本轮不细究；未记录不代表不相通。','庭院、绿化及地下车库上空按原属性独立保留，不由面积排除推断人员可达。'],
 'mapping_recovery':{'source':'2026-10-31原始build_draft.py及review.py历史记录，恢复原01—39映射；当前JSON空间编号及名称为主。','rollout_id':'01a1904e-a8af-7b11-8479-042b53d4fa0d'}}
state['connectivity_items'].append(dict(review_id='K02',source='S006',target='S019',status='pending',question='会议区是否经S006东侧与次入口门厅S019相通？若不是，请指出会议区实际连接门厅的空间。',reason='会议翼与门厅相邻边界未见清晰门洞；会议中心南门朝庭院，不能作为通向S010的直接门洞。该问题决定会议翼与主通行网络的连接。'))
(OUT/'review_state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
(ROOT/'annotation.json').write_text(json.dumps(D,ensure_ascii=False,indent=2)+'\n')
# 定位点只检查人工选点的几何端点，不自动制造门位。
exceptions=[]
for r in D['relations']:
 for o in r.get('openings',[]):
  x,y=o['position_px'];p=Point(y,2424-x)
  ds=[display_poly(s).distance(p) for s in [r['source'],r['target']]]
  if max(ds)>1.1:exceptions.append(dict(relation=r['id'],opening=o['id'],point=[p.x,p.y],distances=ds))
(OUT/'opening_endpoint_audit.json').write_text(json.dumps(exceptions,ensure_ascii=False,indent=2)+'\n')
print('spaces',len(D['spaces']),'relations',len(D['relations']),'access',sum(r['type']=='access' for r in D['relations']),'openings',next_p-1,'exceptions',exceptions)
