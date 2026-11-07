"""Manual evidence-based review helpers; coordinates are in the review image."""
from pathlib import Path
from collections import Counter
import copy
import importlib.util
import json
import re
import shutil
import xml.etree.ElementTree as ET

from shapely.geometry import Polygon, box
from shapely.ops import unary_union

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[2]
BASE = ROOT/'p-平面标注与数据处理'
SKILL = Path('/Users/hushili/.codex/skills/outpatient-plan-annotation')
spec = importlib.util.spec_from_file_location('annotation_tools', SKILL/'scripts/annotation_tools.py')
annotation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(annotation)
NS = '{http://www.w3.org/2000/svg}'


def sid(number):
    return number if isinstance(number,str) else f'S{number:03}'


def classify(name):
    rules = [
        ('露天采光庭院', 'courtyard'), ('管井|官井', 'building_services'),
        ('污物|污洗|污物间/洁具间|洁具', 'waste_handling'), ('污洗', 'waste_handling'),
        ('女卫|男卫|厕所|男厕|女厕|孕妇卫生间|盥洗|洗手间', 'toilet'),
        ('主任|医办|办公|医护版|财务|医保|技师办', 'office'),
        ('示教|会议', 'conference'), ('更衣|男更|女更|值班|生活区', 'staff_support'),
        ('挂号|收费', 'registration'), ('药房|中药加工|煎药|摆药', 'pharmacy'),
        ('药库|药品库|冷藏库|二级库|库房|储片', 'storage'),
        ('配药|配剂', 'medication_preparation'), ('抢救', 'resuscitation'),
        ('手术室', 'operating_room'), ('隔离', 'isolation'),
        ('观察|留观', 'observation'), ('护士站', 'nurse_station'),
        ('前室|缓冲', 'vestibule'), ('大厅|连同|服务中心', 'hall'),
        ('CT|CR|DR|MR|IR|X光|X线|影像室|造影|钼靶|乳腺机|骨密度|B超|彩超', 'imaging'),
        ('检验|尿常规|血常规|细胞室', 'laboratory'),
        ('控制室|阅片|技术工作|洗片|报告|统计分类|药品检查', 'service_work_area'),
        ('计算机房|PACS|设备间|机房|激光相机', 'equipment_room'),
        ('器材|器械', 'equipment_room'), ('准备|换衣|VIP室', 'patient_preparation'),
        ('治疗|换药|处置|输液|注射|洗胃', 'treatment'),
        ('诊室|儿科|外科|内科|妇产科|五官科|妇科', 'consultation'),
        ('检查|心电', 'examination'), ('超市|营养早餐', 'retail_service'),
        ('预诊', 'triage'), ('清洁|消毒', 'sterile_supply'),
        ('备用', 'reserved_space'), ('资料室', 'storage'), ('服务室|哺乳', 'service'),
        ('支持用房|辅助用房|医生工作单元|医护', 'staff_support'),
    ]
    for pattern,code in rules:
        if re.search(pattern,name,re.I):
            return code
    raise ValueError('Unclassified confirmed name: '+name)


class Review:
    def __init__(self,name):
        self.name=name
        self.number=name[:2]
        self.project=BASE/'标注试样'/name
        self.out=WORK/name
        self.backup=self.out/'修改前备份'
        self.data=json.loads((self.backup/'annotation.json').read_text())
        self.original=copy.deepcopy(self.data)
        self.spaces={s['id']:s for s in self.data['spaces']}
        self.rows=json.loads((self.out/'用户填写解析.json').read_text())
        self.work_polys=json.loads((self.out/'工作坐标多边形.json').read_text())
        self.notes=[]
        self.removed=[]
        self.inferred=[]
        self.manual=[]
        self.questions=[]
        self.next_relation=max(int(r['id'][1:]) for r in self.data['relations'] if r['id'].startswith('R'))+1
        self.next_opening=1
        for row in self.rows:
            s=self.spaces[row['sid']]
            answer=row['answer'].strip().strip('*')
            assert answer and '待确认' not in answer and '待填写' not in answer
            if self.number=='09' and row['sid']=='S014':
                continue
            if self.number=='09' and row['sid']=='S159':
                answer='儿科大厅'
            if '露天采光庭院' in answer:
                answer=answer.split(' ')[0]
            s['name']=answer
            s['type']=classify(answer)
            if s['type']=='courtyard':s['level']='open_space'
            elif s['type']=='hall' and s['level'] in ['room','functional_block']:s['level']='open_space'
            elif s['type']=='vestibule':s['level']='room'
        # Scope and stable identifiers remain case-specific.
        if self.number=='09':
            overrides={50:'service',91:'staff_support',100:'staff_support',132:'staff_support',156:'hall'}
        else:
            overrides={122:'resuscitation',123:'operating_room',125:'operating_room',133:'vestibule',
                       165:'storage',168:'pharmacy',181:'consultation',182:'consultation',183:'consultation',184:'consultation'}
        for n,t in overrides.items():self.spaces[sid(n)]['type']=t

    def to_source(self,point):
        x,y=point
        if self.number=='09':
            scale=2444/1367
            return [round(y*scale,2),round(2444-x*scale,2)]
        return [round(x*2444/1367,2),round(y*3260/1824,2)]

    def set_polygon(self,n,points):
        self.work_polys[sid(n)]=points
        self.spaces[sid(n)]['polygon_px']=[self.to_source(p) for p in points]

    def extend(self,n,bounds):
        poly=unary_union([Polygon(self.work_polys[sid(n)]),box(*bounds)])
        assert poly.geom_type=='Polygon'
        self.set_polygon(n,list(poly.exterior.coords)[:-1])

    def merge_rectangle(self,keep,others,name):
        ids=[sid(keep)]+[sid(n) for n in others]
        bounds=unary_union([Polygon(self.work_polys[i]) for i in ids]).bounds
        self.set_polygon(keep,list(box(*bounds).exterior.coords)[:-1])
        self.spaces[sid(keep)]['name']=name
        self.spaces[sid(keep)]['type']='imaging'
        for n in others:
            self.spaces.pop(sid(n))
            self.work_polys.pop(sid(n))
        for r in self.data['relations']:
            for field in ['source','target']:
                if r[field] in ids:r[field]=sid(keep)
        self.data['spaces']=[s for s in self.data['spaces'] if s['id'] in self.spaces]
        self.notes.append('按用户房名核对09的说明，将S008、S009、S014合并为S008“CT”；保留S008，不重排其余编号。')

    def find(self,a,b,kind='access'):
        pair={sid(a),sid(b)}
        return next((r for r in self.data['relations'] if r['type']==kind and {r['source'],r['target']}==pair),None)

    def edge(self,a,b,kind='access'):
        a,b=sid(a),sid(b)
        assert a in self.spaces and b in self.spaces and a!=b
        r=self.find(a,b,kind)
        if r is None:
            r={'id':f'R{self.next_relation:03}','source':a,'target':b,'type':kind}
            self.next_relation+=1
            self.data['relations'].append(r)
        return r

    def remove(self,a,b,reason):
        r=self.find(a,b)
        if r:
            self.removed.append(dict(relation=copy.deepcopy(r),reason=reason))
            self.data['relations'].remove(r)

    def door(self,a,b,x,y,kind='door'):
        r=self.edge(a,b)
        point=self.to_source((x,y))
        for old in r.get('openings',[]):
            if sum((p-q)**2 for p,q in zip(old['position_px'],point))<4:return
        op={'id':f'P{self.next_opening:03}','kind':kind,'position_px':point}
        self.next_opening+=1
        r.setdefault('openings',[]).append(op)
        self.manual.append({'id':op['id'],'pair':[sid(a),sid(b)],'work_xy':[x,y],'kind':kind})

    def row_doors(self,rooms,channel,y,xs):
        assert len(rooms)==len(xs)
        for n,x in zip(rooms,xs):
            if x is not None:self.door(n,channel,x,y)

    def concept(self,a,b,reason):
        r=self.edge(a,b)
        self.inferred.append({'pair':[sid(a),sid(b)],'relation':r['id'],'reason':reason})

    def service(self,a,b):
        return self.edge(a,b,'service')

    def entrance(self,target,x,y,name):
        existing=[int(r['id'][1:]) for r in self.data['relations'] if r['type']=='entrance']
        rid=f'E{max(existing)+1:03}'
        self.data['relations'].append({'id':rid,'source':None,'target':sid(target),'type':'entrance',
                                      'name':name,'entrance_type':'main','position_px':self.to_source((x,y))})

    def save_stage(self):
        for s in self.data['spaces']:
            assert s['type']!='unknown',s
        annotation.normalize(self.data)
        stage=self.out/'待核验成果'
        stage.mkdir(exist_ok=True)
        shutil.copy2(self.backup/self.data['image']['file'],stage/self.data['image']['file'])
        p=stage/'annotation.json'
        p.write_text(json.dumps(self.data,ensure_ascii=False,indent=2)+'\n')
        annotation.render(self.data,p,stage/'标注.svg')
        fit_labels(stage/'标注.svg',self.data)
        annotation.summary(self.data,stage/'标注说明.md')
        review={'notes':self.notes,'removed_relations':self.removed,'layout_inferences':self.inferred,
                'manual_openings':self.manual,'questions':self.questions}
        (self.out/'复核记录.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n')
        print(self.number,len(self.data['spaces']),Counter(r['type'] for r in self.data['relations']),
              'openings',len(self.manual),'questions',len(self.questions),flush=True)
        return stage


def fit_labels(path,data):
    tree=ET.parse(path)
    for space in data['spaces']:
        group=tree.find(f'.//{NS}g[@id="{space["id"]}"]')
        rect=group.find(NS+'rect')
        texts=group.findall(NS+'text')
        if rect is None:continue
        x,y,w,h=[float(rect.get(k)) for k in ['x','y','width','height']]
        poly=Polygon(space['polygon_px'])
        q=poly.representative_point()
        scale=1
        while scale>.05 and not poly.covers(box(q.x-w*scale/2,q.y-h*scale/2,q.x+w*scale/2,q.y+h*scale/2)):
            scale*=.94
        if scale<1:
            holder=ET.Element(NS+'g',{'transform':f'translate({q.x} {q.y}) scale({scale}) translate({-x-w/2} {-y-h/2})'})
            for element in [rect]+texts:
                group.remove(element)
                holder.append(element)
            group.append(holder)
    tree.write(path,encoding='unicode')
