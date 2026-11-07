"""按2026-11-02用户原文同步四图；保留稳定编号、原图和完整填写归档。"""
from pathlib import Path
from collections import Counter
import copy
import hashlib
import importlib.util
import json
import os
import re
import xml.etree.ElementTree as ET

from shapely.geometry import Polygon, box
import pymupdf

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SKILL = Path('/Users/hushili/.codex/skills/outpatient-plan-annotation')


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


at = module('at', SKILL/'scripts/annotation_tools.py')
qa = module('qa', ROOT/'临时核对/05-08_概念连通对齐_20261101/核对材料与验证.py')


def dump(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')


class Plan:
    def __init__(self, number):
        self.number = number
        self.path = next((ROOT/'标注试样').glob(number+'_*'))
        self.work = HERE/self.path.name
        self.before = self.work/'同步前备份'
        self.data = json.loads((self.before/'annotation.json').read_text())
        self.old = copy.deepcopy(self.data)
        self.spaces = {s['id']: s for s in self.data['spaces']}
        self.notes = []
        self.log = []
        self.image_hash = hashlib.sha256((self.path/self.data['image']['file']).read_bytes()).hexdigest()
        self.next_relation = max(int(r['id'][1:]) for r in self.data['relations'] if r['id'].startswith('R'))+1
        self.next_opening = max(int(o['id'][1:]) for r in self.data['relations'] for o in r.get('openings', []))+1

    def sid(self, value):
        return f'S{value:03d}' if isinstance(value, int) else value

    def access(self, a, b, point=None):
        a, b = self.sid(a), self.sid(b)
        rel = next((r for r in self.data['relations'] if r['type']=='access' and
                    {r['source'], r['target']}=={a,b}), None)
        if rel is None:
            rel = dict(id=f'R{self.next_relation:03d}', source=a, target=b, type='access')
            self.next_relation += 1
            self.data['relations'].append(rel)
            self.log.append({'added_relation':copy.deepcopy(rel)})
        if point is not None:
            opening = dict(id=f'P{self.next_opening:03d}', kind='door', position_px=point)
            self.next_opening += 1
            rel.setdefault('openings', []).append(opening)
            self.log.append({'added_opening':opening, 'relation':rel['id']})
        return rel

    def absent(self, a, b):
        a,b = self.sid(a),self.sid(b)
        for r in self.data['relations'][:]:
            if r['type']=='access' and {r['source'],r['target']}=={a,b}:
                self.log.append({'removed_relation':r})
                self.data['relations'].remove(r)

    def note(self, number, text):
        self.notes.append((number,text))

    def geometry(self, sid, geom):
        sid=self.sid(sid)
        assert geom.geom_type=='Polygon' and geom.is_valid and not geom.interiors
        self.spaces[sid]['polygon_px'] = [[round(x,3),round(y,3)] for x,y in list(geom.exterior.coords)[:-1]]
        self.log.append({'geometry':sid,'polygon_px':self.spaces[sid]['polygon_px']})

    def corridor(self, sid, name, bounds, scope):
        s=dict(id=self.sid(sid),name=name,type='corridor',level='open_space',scope=scope,
               polygon_px=[list(xy) for xy in list(box(*bounds).exterior.coords)[:-1]])
        assert s['id'] not in self.spaces
        self.data['spaces'].append(s)
        self.spaces[s['id']]=s
        self.log.append({'added_space':s['id'],'name':name})

    def remove_spaces(self, ids):
        ids={self.sid(i) for i in ids}
        for r in self.data['relations'][:]:
            if r['source'] in ids or r['target'] in ids:
                self.log.append({'removed_relation':r})
                self.data['relations'].remove(r)
        self.data['spaces']=[s for s in self.data['spaces'] if s['id'] not in ids]
        for sid in ids:
            self.log.append({'excluded_space':self.spaces.pop(sid)})

    def entrance(self, target, point, name):
        n=max(int(r['id'][1:]) for r in self.data['relations'] if r['type']=='entrance')+1
        r=dict(id=f'E{n:02d}',source=None,target=self.sid(target),type='entrance',
               name=name,entrance_type='side',position_px=point)
        self.data['relations'].append(r)
        self.log.append({'added_entrance':r})

    def write(self):
        at.normalize(self.data)
        dump(self.path/'annotation.json',self.data)
        at.render(self.data,self.path/'annotation.json',self.path/'标注.svg')
        qa.optimize_labels(self.path/'标注.svg',self.data)
        if self.number=='05':
            tree=ET.parse(self.path/'标注.svg')
            entry=next(e for e in tree.iter() if e.get('id')=='E11')
            for e in entry:
                if e.tag.endswith('rect'):e.set('x','840');e.set('y','850')
                if e.tag.endswith('text'):e.set('x','847');e.set('y','868')
                if e.tag.endswith('line'):e.set('x2','939');e.set('y2','862.5')
            tree.write(self.path/'标注.svg',encoding='unicode')
        at.summary(self.data,self.work/'自动概览.md')
        text=(self.work/'自动概览.md').read_text().replace('# 平面标注概览','# '+self.path.name+'｜一层概念标注概览')
        text=text.replace('空间名称已齐；结构与关系仍以原图及人工核对为依据。',
                          '**状态：**已同步2026-11-02的人工填写，本张平面按约定的概念精度完成；本轮关键疑点已全部处理。')
        archive=Path(os.path.relpath(self.before/'标注说明.md',self.path)).as_posix()
        text+='\n\n**范围与精度：**当前单张一层平面；普通门诊、急诊、医技及住院支持按既有scope区分。'
        text+='已定位门洞保留近似红点；半墙、连续区域及已确认但无法精确定位的连接保留无openings的access。'
        text+='未记录的内部小间关系保持未知，不作为不可通行负例。原图和未退出范围的既有S/P编号保留。\n\n'
        text+='**本轮确认落实（2026-11-02）：**\n\n| 固定核对号 | 已落实内容 |\n| --- | --- |\n'
        for num,note in self.notes:text+=f'| {num} | {note} |\n'
        if self.number=='06':
            text+='\nS060及同条带S062按用户本轮范围意见退出当前样本，其编号不再分配。S120依用户“换鞋间”及原图改名，保留原S编号和P102。\n'
        if self.number=='07':
            text+='\nS411、S412补记原先遗漏的北侧横向通道，分别连接儿科医疗街S391和妇产科医疗街S396；不改变既有编号。\n'
        if self.number=='08':
            text+='\n药房的“门厅侧”按既有取药收费前区S171组织路径S153—S171—S162，保留服务窗口与人员连接的区别；这一路径映射依据原图布局，不冒充用户逐节点确认。\n'
        old_text=(self.before/'标注说明.md').read_text()
        if '## 布局推断（不是用户已确认）' in old_text:
            inference=old_text.split('## 布局推断（不是用户已确认）',1)[1].split('## 核验边界',1)[0].strip()
            text+='\n**沿用的布局推断（非用户逐项确认）：**\n\n'+inference+'\n'
        text+=f'\n[用户填写原文及全部局部图]({archive})。原文、历史名称与属性核对记录完整归档；无需重复填写。\n'
        text+=f'\n[原图]({self.data["image"]["file"]}) · [标注.svg](标注.svg) · [annotation.json](annotation.json)。\n'
        text+='\n**完成范围：**主要功能空间、通道、交通核和建筑入口的概念级标注；不穷尽辅助小间内部路线，不代表逐门施工测绘或模型效果验证。\n'
        (self.path/'标注说明.md').write_text(text)
        dump(self.work/'本轮变更.json',self.log)
        assert self.image_hash==hashlib.sha256((self.path/self.data['image']['file']).read_bytes()).hexdigest()
        old_points={o['id']:o for r in self.old['relations'] for o in r.get('openings',[])}
        new_points={o['id']:o for r in self.data['relations'] for o in r.get('openings',[])}
        assert all(new_points.get(k)==v for k,v in old_points.items()), '既有开口变动须专门核验'
        print('SYNC',self.number,len(self.data['spaces']),len(self.data['relations']),len(new_points),flush=True)


def sync05():
    p=Plan('05')
    p.absent(1,6)
    p.entrance(1,[827,975],'影像北侧外置楼梯入口')
    p.access(13,9)
    # 上侧小门前的缓冲条带属于入口区，避免红点被误指至上方试品区。
    bridge=box(1969.75,1039.78,2027,1054)
    p.geometry(41,Polygon(p.spaces['S041']['polygon_px']).union(bridge))
    p.geometry(42,Polygon(p.spaces['S042']['polygon_px']).difference(bridge))
    p.access(41,42,[2005,1054])
    p.absent(42,52)
    p.access(41,52)
    p.access(24,20)
    p.access(25,20)
    p.access(28,31,[1034,2055])
    p.absent(28,24)
    p.absent(121,72)
    p.note('01','S001为外置楼梯，补独立外部入口E11；不建立S001—S006直接连接，分别经外围进入。')
    p.note('03','护士站S013以半墙工作区概念连接DR内侧通道S009，不把柜台当门洞。')
    p.note('04','S042通过上侧小门连接S041；补P118，并微调上侧门前缓冲条带归属。')
    p.note('05','S042经S041再接S052，不建立S042—S052直达边。')
    p.note('08','S024、S025分别直接连接北侧S020；门位未精确定位，不新增假红点。')
    p.note('10','MR S028经东侧门接控制室S031，补P119；不接更衣S024。')
    p.note('14','S121与S072不直接相连；保留既有南向门及东侧独立出口。')
    p.write()


def sync06():
    p=Plan('06')
    p.remove_spaces([60,62])
    p.access(65,63,[1822,2068])
    p.access(65,64,[2118,2068])
    p.spaces['S120'].update(name='换鞋间',type='staff_support')
    p.access(111,120)
    p.access(120,109)
    p.absent(111,109)
    p.access(57,58)
    p.note('L01','卫生间S060及同一细长条带的S062退出当前标注范围；移除其附属关系，重新归一化室内面积。')
    p.note('L02','S065室内中庭B可步入，分别连接左右医疗街S063、S064，补左右门洞P277、P278；保持室内面积口径。')
    p.note('L04','按原图和填写将S120修正为换鞋间；S111经S120接S109，保留原S109—S120门洞P102，不添加跨越中间空间的直达边。')
    p.note('L09','S057与S058按用户确认直接可通行；记录概念access，不编造精确门位。')
    p.write()


def sync07():
    p=Plan('07')
    p.corridor(411,'输液中心北侧联络通道',(863,850,1200,888),'pediatric_outpatient')
    p.corridor(412,'产科门诊北侧联络通道',(2470,850,3059,888),'obstetrics_outpatient')
    p.access(411,391)
    p.access(412,396)
    p.access(105,411,[1181,891])
    p.absent(105,106)
    p.access(159,412,[2494,891])
    p.access(163,161)
    p.absent(163,162)
    for a,b in [(285,286),(294,291),(301,297),(312,304),(325,321)]:
        p.access(a,b)
    p.access(322,273,[2106,2086])
    p.note('03','S105北侧门连接上方通道S411，再接儿科医疗街S391；补P335，不接下方候诊S106。')
    p.note('05','S159北门接上方通道S412，再接妇产科医疗街S396，补P336；S163经更衣刷手S161进入，不恢复S163—S162旧直达边。')
    for num,a,b in [('06',285,286),('07',294,291),('08',301,297),('09',312,304),('12',325,321)]:
        p.note(num,f'S{a:03d}连接内部设备所在的检查室S{b:03d}；按用户确认建立access，未定位的内部小门不补造红点。')
    p.note('10','S322左侧门接影像内部通道S273，补P337；不以相邻库房／准备间的门替代其入口。')
    p.write()


def sync08():
    p=Plan('08')
    p.entrance(65,[1375,1266],'儿科北侧楼梯南向独立入口')
    p.access(74,178)
    p.absent(139,149)
    p.access(153,171)
    p.access(171,162)
    p.access(190,191)
    p.access(213,208)
    p.access(208,195)
    p.absent(213,195)
    p.access(211,322)
    p.note('01','S065从南侧室外门进入，补独立入口E08；不根据相邻关系补消防控制室或儿科候诊直达边。')
    p.note('02','S074与西侧医疗街S178直接相连；保留经S125的既有其他路径。')
    p.note('03','S139入口朝外；保留E07，不建立S139—S149室内直达边。')
    p.note('04','S153药房从门厅侧进入；结合现有功能块边界，经取药收费前区S171接门厅S162，不把服务窗口当门。')
    p.note('05','S190化验人员可经S191取样区进入，增加access；既有service同时保留。')
    p.note('06','医护门斗S213先接楼梯核S208，再接东侧工作通道S195；不添加S213—S195跨核直达边。')
    p.note('07','S211后台接西侧窄通道S322，服务关系保留；确认的是连接，未定位门位不新增红点。')
    p.write()


if __name__=='__main__':
    import sys
    globals()['sync'+sys.argv[1]]()
