"""本轮逐图复核写回；人工点位与判读记录均保存在正式样本目录外。"""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import re
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SKILL = Path('/Users/hushili/.codex/skills/outpatient-plan-annotation')
spec = importlib.util.spec_from_file_location('annotation_tools', SKILL/'scripts/annotation_tools.py')
at = importlib.util.module_from_spec(spec)
spec.loader.exec_module(at)


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')


class Plan:
    def __init__(self, number):
        self.path = next((ROOT/'标注试样').glob(number+'_*'))
        self.work = HERE/self.path.name
        self.old = json.loads((self.work/'修改前备份/annotation.json').read_text())
        self.data = copy.deepcopy(self.old)
        self.spaces = {s['id']: s for s in self.data['spaces']}
        self.changes = []
        self.inferences = []
        self.questions = []
        self.retired = []

    def remove(self, ids, reason):
        for r in self.data['relations'][:]:
            if r['id'] in ids:
                assert not r.get('openings'), '既有定位门洞不能在筛选问题时丢失'
                self.changes.append({'removed': r, 'reason': reason})
                self.data['relations'].remove(r)

    def relation(self, a, b, kind='access', point=None):
        a = f'S{a:03d}' if isinstance(a, int) else a
        b = f'S{b:03d}' if isinstance(b, int) else b
        rel = next((r for r in self.data['relations'] if r['type']==kind and
                    {r['source'], r['target']}=={a,b}), None)
        if rel is None:
            maximum = max(int(r['id'][1:]) for r in self.data['relations'] if r['id'].startswith('R'))
            rel = {'id':f'R{maximum+1:03d}', 'source':a, 'target':b, 'type':kind}
            self.data['relations'].append(rel)
            self.changes.append({'added_relation':rel['id'], 'source':a, 'target':b, 'type':kind})
        if point:
            maximum = max([int(o['id'][1:]) for r in self.data['relations']
                           for o in r.get('openings', [])] or [0])
            opening = {'id':f'P{maximum+1:03d}', 'kind':'door', 'position_px':point}
            rel.setdefault('openings', []).append(opening)
        return rel

    def concept(self, a, b, reason):
        r = self.relation(a,b)
        self.inferences.append({'relation':r['id'], 'source':r['source'], 'target':r['target'],
                                'basis':reason, 'status':'布局推断，非用户确认'})

    def geometry(self, sid, geom, reason):
        sid = f'S{sid:03d}' if isinstance(sid,int) else sid
        assert geom.geom_type=='Polygon' and geom.is_valid and not geom.interiors, (sid,geom.geom_type)
        before = self.spaces[sid]['polygon_px']
        after = [[round(x,3),round(y,3)] for x,y in list(geom.exterior.coords)[:-1]]
        self.spaces[sid]['polygon_px'] = after
        self.changes.append({'geometry':sid, 'before':before, 'after':after, 'reason':reason})

    def new_corridor(self, sid, name, geom):
        s = copy.deepcopy(self.spaces['S201'])
        s.update(id=sid, name=name, type='corridor', level='open_space', polygon_px=list(geom.exterior.coords)[:-1])
        self.data['spaces'].append(s)
        self.spaces[sid] = s
        self.changes.append({'new_space':sid, 'name':name, 'reason':'原图可见、旧草稿遗漏的独立通行带；不细分既有功能块。'})

    def question(self, num, ids, question, judgment):
        self.questions.append({'number':num, 'spaces':ids, 'question':question,
                               'judgment':judgment, 'answer':'待填写'})

    def write(self):
        for s in self.old['spaces']:
            now = self.spaces[s['id']]
            assert all(s[k]==now[k] for k in ['name','type','level','scope']), s['id']
        old_points = {o['id']:o for r in self.old['relations'] for o in r.get('openings',[])}
        new_points = {o['id']:o for r in self.data['relations'] for o in r.get('openings',[])}
        assert all(new_points[k]==v for k,v in old_points.items())
        at.normalize(self.data)
        dump(self.path/'annotation.json', self.data)
        dump(self.work/'变更记录.json', self.changes)
        dump(self.work/'布局推断.json', self.inferences)
        dump(self.work/'明日关键确认.json', self.questions)
        dump(self.work/'退出逐项追问.json', self.retired)
        at.render(self.data, self.path/'annotation.json', self.path/'标注.svg')
        return self


def plan05():
    p = Plan('05')
    pending = ['R003','R010','R014','R022','R030','R031','R037','R038',
               'R046','R053','R055','R060','R070','R077','R078','R130']
    p.remove(pending, '原复核明确列为无可靠门洞证据的旧边；移至外部记录，待核前不当作确定人员可达。')
    entries = [
        ('01',['S001','S006'],'两座北侧交通核是否直接相通，还是分别经外围通道进入？','现有门洞可保留，但两核之间的旧直接连接缺少证据。'),
        ('03',['S013','S009'],'护士站人员是否可从下方DR内侧通道进入？','柜台服务联系已保留，人员入口仍需判断；不要求精确门位。'),
        ('04',['S041','S042'],'静脉输液入口区与准备区是否按相邻两区概念相通？','边界上有密集的小门与缓冲符号，但跨区归属尚不清楚。'),
        ('05',['S042','S052'],'准备区能否直接通向南侧静脉配液区通道？','入口／缓冲小间归属仍影响主要连接；未补造门位。'),
        ('08',['S024','S025','S020'],'更衣、护士站是否分别直接通向北侧影像内通道？','更衣南向门已保留；北向人员联系不由服务窗口推定。'),
        ('10',['S028','S024','S031'],'MR人员入口主要接更衣还是控制室？','MR东侧狭长符号可能为门或观察窗，需要确认直接相连节点。'),
        ('14',['S121','S072'],'东侧电梯及前室是否在北端直接连向南侧连接通道？','东向出口及南侧门已保留，北向联系尚无可靠开口证据。'),
    ]
    for entry in entries:p.question(*entry)
    p.retired = [{'number':n,'result':'管井／检修小间或已有替代出入口的辅助内部细节，本轮不细究；未定边不回写access，非用户确认。'}
                 for n in ['02','06','07','09','11','12','13']]
    return p.write()


def plan06():
    p = Plan('06')
    p.concept(124,299,'登记柜台后侧与东侧短通行带之间未见完整实体隔墙；S299两端已连接等候厅。仅记录后台概念可达，不画假门。')
    p.relation(276,262,point=[2690,3955])
    entries = [
        ('L01',['S060'],'这处卫生间是否属于当前首层？若属于，从哪侧通道进入？','与此前删除的非首层小图块同排，范围归属仍需确认；暂不删除既有节点。'),
        ('L02',['S065'],'室内中庭B是否可步入；若可步入，主要从哪条通道进入？','名称与面积口径保留，名称本身不证明人员可进入。'),
        ('L04',['S111','S109'],'更衣内通道是否与影像员工通道相连？','男女更衣开向东侧条带，但条带外端接入主要通道的方式仍不明确。'),
        ('L09',['S057','S058'],'两处休闲区是否可直接穿行？','中间竖向分隔连续；两区各自的已知出入口保留，跨区边留空。'),
    ]
    for entry in entries:p.question(*entry)
    p.retired = [
        {'number':'L05','result':'已自主记录S124—S299后台概念可达，未编造门位；不是用户已确认。'},
        {'number':'L10','result':'原图东侧门扇弧可辨，补S276—S262门洞P276，近似坐标2690,3955。'},
    ] + [{'number':n,'result':'辅助小间／卫生间内部／值班更衣内部细节，本轮不穷尽连接；证据不足继续留空。'}
         for n in ['L03','L06','L07','L08']]
    return p.write()


def plan07():
    p = Plan('07')
    p.concept(139,130,'药房电梯整体节点的开门面朝北侧后场通道；按整体交通核与后场连续前区的组织记录概念联系，不定位井道内部门。')
    mapping = json.loads((ROOT/'临时核对/07_内蒙古_20261101_开口复核/连通核对映射_工作.json').read_text())
    keep = {'03','05','06','07','08','09','10','12'}
    for q in mapping:
        number = str(q.get('number',q.get('num',''))).zfill(2)
        if number in keep:
            p.question(number, q['spaces'], q['question'],
                       '该问题仍影响主要交通核或检查／治疗空间的直接连接；只需确认所连通道或相邻空间，无需确定施工门位。')
    assert len(p.questions)==8, mapping[:1]
    p.retired = [{'number':'04','result':'S139—S130按整体电梯核与后场通道组织作布局推断，未编造具体门位。'}]
    p.retired += [{'number':n,'result':'保安、平车、辅助更衣、男浴及小机房内部细节，本轮不逐项追问，未定联系继续未知。'}
                  for n in ['01','02','11','13']]
    return p.write()


def plan08():
    p = Plan('08')
    # 校正原图明确可辨的通行带、诊室斜边与南侧交通核位置，保留既有S编号与房名。
    def poly(i):return Polygon(p.spaces[f'S{i:03d}']['polygon_px'])
    p.geometry(2,box(350,436,400,466),'库房东界按原图调整，门开向南侧通行带。')
    p.geometry(3,box(400,436,446,510),'合并机房的西界按原图调整，为入口带留出范围。')
    p.geometry(5,box(484,436,546,518),'卫生间外部入口下界按原图延至518附近。')
    area = unary_union([poly(6),box(390,466,546,522)])
    for i in [2,3,4,5,8,12,13]:area=area.difference(poly(i))
    p.geometry(6,area,'备用功能块包含可见内部连续通行带，不另细分内部小房间。')
    p.geometry(66,box(346,1164,422,1262),'交通核右侧的窄通行带属于医技西侧通道。')
    p.geometry(73,unary_union([poly(73),box(422,1164,444,1262)]),'补医技西侧通道北端漏段。')
    p.geometry(93,unary_union([poly(93),box(388,1644,422,1666)]),'整体楼梯核保留东侧出入口前区。')
    for i,pts in {
        99:[[444,1618],[490,1618],[540,1645],[540,1690],[444,1690]],
        100:[[540,1645],[590,1618],[636,1618],[636,1690],[540,1690]],
        101:[[636,1618],[684,1618],[734,1645],[734,1690],[636,1690]],
        102:[[734,1645],[782,1618],[830,1618],[830,1690],[734,1690]],
    }.items():
        old=poly(i);new=Polygon(pts)
        p.geometry(i,new,'胃肠检查室北侧斜入口按原图修正。')
        p.geometry(96,unary_union([poly(96),old.difference(new)]),'工作通道延入对应斜入口前区。')
    for i,pts in {
        108:[[444,1742],[540,1742],[540,1793],[490,1822],[444,1822]],
        109:[[540,1742],[636,1742],[636,1822],[590,1822],[540,1793]],
        110:[[636,1742],[734,1742],[734,1793],[684,1822],[636,1822]],
        111:[[734,1742],[830,1742],[830,1822],[784,1822],[734,1793]],
    }.items():
        old=poly(i);new=Polygon(pts)
        p.geometry(i,new,'DR检查室南侧斜入口按原图修正。')
        p.geometry(114,unary_union([poly(114),old.difference(new)]),'工作通道延入对应斜入口前区。')
    p.new_corridor('S322','急诊西侧后场通道',box(1514,2014,1532,2184))
    for i in [211,218]:p.geometry(i,poly(i).difference(poly(322)),'为原图可见后场窄通道留出范围。')
    p.new_corridor('S323','西南片区东侧内通道',box(894,2514,926,2590))
    p.spaces['S323']['scope']=p.spaces['S269']['scope']
    p.geometry(253,unary_union([poly(253),box(388,2624,414,2680)]),'西南通道沿楼梯东侧下行至南端办公室门口。')
    p.geometry(249,unary_union([poly(249),box(880,2378,926,2414)]),'苏醒功能区包含服务台东侧连续前区，连接东侧准备间。')
    p.geometry(295,box(2034,2280,2068,2380),'库房南端延至原图楼梯前区横界。')
    for i,geom in [(317,box(1214,2634,1578,2696)),(318,box(1578,2634,1600,2696)),
                   (319,box(1600,2634,1695,2696)),(320,box(1695,2634,1786,2696))]:
        p.geometry(i,geom,'南入口带按实际门斗、辅助小间及楼梯位置纠正；维持既有编号及名称。')
    for r in p.data['relations']:
        if r['id']=='E05':r['position_px']=[1733,2696]
    # 旧设备室直达候诊大厅的边改接可见南门所通北侧工作通道。
    p.remove(['R065'],'设备S070的可见南门通S068；旧直达S074无独立门位依据。')
    for line in (p.work/'门位人工判读.tsv').read_text().splitlines():
        if not line or line.startswith('#'):continue
        a,b,coords=line.split()
        for pair in coords.split(';'):
            p.relation(int(a),int(b),point=list(map(float,pair.split(','))))
    concepts = [
        (46,50,'强弱电整体节点南侧有出入口，原图小门分片未继续细分。'),
        (47,50,'入口区南端与服务通道连续。'),
        (4,6,'独立电梯整体节点的前区朝向备用功能区，按电梯与前区布局记录概念联系。'),
        (10,1,'东侧独立电梯开门面向病房楼电梯厅，按整体节点组织记录。'),
        (42,40,'儿科观察区内的整体电梯核经自身前区接观察区，不细分井道内部。'),
        (32,19,'服务台侧端向出入院通道开放，保留服务工作区概念联系。'),
        (66,73,'整体交通核东侧前区接医技西侧窄通道，不记录核内部小门。'),
        (80,79,'观察室在注射功能区内部，分隔线未延至南端，按连续前区记录概念联系。'),
        (83,74,'登记半墙工作区向候诊大厅提供服务，人员可达按南侧开放端布局推断，未编造门位。'),
        (97,74,'交通核与候诊大厅的既有连接保留，定位门已补充。'),
        (105,74,'登记半墙区与候诊大厅端部相接，人员开口未明确定位。'),
        (122,74,'南侧登记服务工作区以东侧开放端连接候诊大厅，按布局推断。'),
        (131,162,'儿科联络通道南端与儿科门厅连续。'),
        (133,162,'儿科东侧走道南端接门厅。'),
        (147,130,'半墙护士站从侧端衔接儿科候诊前区，按概念布局推断，不从服务柜台生成门位。'),
        (161,162,'预诊挂号侧端开放联系门厅，保留半墙服务区概念连接。'),
        (171,162,'儿科取药收费人员工作区经东侧服务前区接入门厅，布局推断，不定位门。'),
        (173,179,'整体交通核西侧前区衔接东侧医疗街，不细分内部核路线。'),
        (175,179,'儿科门厅西侧联络区西端与东侧医疗街衔接。'),
        (176,162,'儿科门厅的自动扶梯整体节点通过自身前区接门厅。'),
        (180,181,'中央电梯组朝向公共连廊的整体节点连接。'),
        (182,181,'中央扶梯直接接公共连廊，内部路线不单独建模。'),
        (186,188,'南侧自动扶梯整体核直接接门诊大厅。'),
        (202,204,'护士站半墙工作区从侧端接ICU南侧通道，布局推断，无定位点。'),
        (207,204,'留观功能块的北侧入口前区接ICU南侧通道，保留整体节点。'),
        (322,200,'后场窄通道北端接急诊候诊区，曲线边界入口按布局推断。'),
        (322,284,'后场窄通道南端接急诊诊疗大厅连续前区。'),
        (228,184,'西南候诊区东侧与门诊大厅北部连续，无清晰独立门扇。'),
        (228,185,'西南候诊区东侧开放边接门诊大厅西侧，概念分区线不当作隔墙。'),
        (228,188,'西南候诊区南端经开放前区接门诊大厅。'),
        (323,269,'西南东侧内通道南端无实体分隔接南侧通道。'),
        (278,279,'登记半墙区从侧端衔接西南门厅，布局推断。'),
        (290,284,'A区诊室按现有半墙功能块保存，从开放端接急诊诊疗大厅。'),
        (291,284,'B区诊室按现有半墙功能块保存，从开放端接急诊诊疗大厅。'),
        (306,284,'护士挂号半墙区从西侧开放端接急诊诊疗大厅，布局推断。'),
        (245,249,'服务台通过苏醒区内的开放前区接入，半墙柜台不记录假门。'),
        (307,310,'门斗间南端接急诊大厅，未定位独立门位。'),
    ]
    for a,b,reason in concepts:p.concept(a,b,reason)
    for a,b in [(83,74),(105,74),(122,74),(147,130),(153,130),(161,162),(171,162),
                (202,204),(245,249),(247,188),(278,279),(290,284),(291,284),(306,284),
                (32,34),(191,190),(191,200),(211,200)]:
        p.relation(a,b,kind='service')
    for a,b in [(76,77),(77,78),(87,88),(88,89),(89,90),(99,100),(101,102),
                (108,109),(110,111),(230,231),(232,233),(241,242),(243,244)]:
        p.relation(a,b,kind='shared_wall')
    entries = [
        ('01',['S065','S053','S130'],'楼梯交通核S065主要从消防控制室一侧还是儿科候诊一侧进入？','南侧可见外部门口，但内部入口归属未清楚；不把相邻墙线当人员连接。'),
        ('02',['S139','S149'],'儿科楼梯S139是否也直接连向南侧儿科门诊候诊通道？','庭院侧门可辨并单独记为外部入口，面向室内候诊通道的开口仍需确认。'),
        ('03',['S153','S147','S162'],'儿科药房工作人员主要从护士站一侧、门厅侧，还是其他后台空间进入？','服务窗口已单列service；不以窗口推断人员可以穿过。'),
        ('04',['S190','S191','S175','S200'],'化验室S190的人员入口接北侧联络区，还是经取样区或候诊区进入？','取样的服务联系可记录，但不能据此确定工作人员入口。'),
        ('05',['S213','S208','S195'],'医护入口门斗S213进入室内后，直接连接楼梯核还是急诊东侧工作通道？','入口区域与楼梯相邻，门扇及开口归属尚不清楚，暂不新增室内access。'),
        ('06',['S074','S178','S125'],'医技候诊大厅与西侧医疗街是否直接相通，还是主要经南侧联络通道进入门诊大厅？','两区之间有连续边线，现有图面不足以确定其是否为可穿行界面；南侧已知通道关系保留。'),
        ('07',['S211','S322','S201'],'影像报告领取处的后台人员是否从西侧窄通道S322进入？','领取服务边已保存；后台门未辨清，暂不把服务联系写成人员通行。'),
    ]
    for entry in entries:p.question(*entry)
    p.retired=[{'number':'内部细节','result':'独立小设备、管井、卫生间内部分隔、辅助值班等未见可靠门口的细节不逐项追问；保持未知，不作为不可通行负例。'}]
    p.data['relations'].append({'id':'E07','source':None,'target':'S139','type':'entrance',
        'name':'儿科庭院侧楼梯出口','entrance_type':'side','position_px':[1755,1364]})
    return p


if __name__=='__main__':
    import sys
    number=sys.argv[1]
    p=globals()['plan'+number]()
    if number=='08':p.write()
    print(p.path.name, len(p.data['spaces']),len(p.data['relations']),
          sum(len(r.get('openings',[])) for r in p.data['relations']),len(p.questions))
