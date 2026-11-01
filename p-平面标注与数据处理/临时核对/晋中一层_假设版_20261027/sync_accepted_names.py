from pathlib import Path
import json, copy, sys, shutil, hashlib
from decimal import Decimal
import xml.etree.ElementTree as ET
from PIL import Image
import pymupdf

ROOT=Path('/Users/hushili/Documents/毕业 - 大论文写作/大论文')
D=ROOT/'p-写作过程/标注试样/3晋中市第一人民医院_一层'
O=Path(__file__).parent
Q=O/'同步后核验';Q.mkdir(exist_ok=True)
B=Q/'修改前备份';B.mkdir(exist_ok=True)
for p in D.iterdir():
    if p.is_file() and not (B/p.name).exists():shutil.copy2(p,B/p.name)
sys.path.insert(0,'/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts')
import annotation_tools as at

path=D/'annotation.json';before=json.loads(path.read_text());data=copy.deepcopy(before)
hypotheses=json.loads((O/'假设清单及编号映射.json').read_text())['hypotheses']
by={s['id']:s for s in data['spaces']}
types={4:'building_services',9:'storage',10:'sterile_supply',11:'sterile_supply',12:'building_services',13:'toilet',14:'staff_support',15:'toilet',16:'staff_support',17:'storage',21:'service',23:'toilet',32:'staff_support',33:'staff_support',34:'building_services',44:'toilet',46:'toilet',48:'toilet',49:'vestibule',50:'vestibule',51:'staff_support'}
assert set(types)=={h['number'] for h in hypotheses}
pending={s['id'] for s in data['spaces'] if s['type']=='unknown'}
assert pending=={h['sid'] for h in hypotheses}
for h in hypotheses:
    s=by[h['sid']]
    assert [[y,1440-x] for x,y in s['polygon_px']]==h['polygon']
    s['name']=h['name'];s['type']=types[h['number']]
# Normalize only the existing indoor geometries; no boundary or link edits.
at.normalize(data)
indoor=[s for s in data['spaces'] if at.indoor(s)]
residual=Decimal(1)-sum(Decimal(str(s['area_ratio'])) for s in indoor)
largest=max(indoor,key=lambda s:s['area_ratio'])
largest['area_ratio']=float(Decimal(str(largest['area_ratio']))+residual)
assert sum(Decimal(str(s['area_ratio'])) for s in indoor)==Decimal(1)
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')

# Display upright while keeping all core JSON coordinates on the original image.
display=copy.deepcopy(data);w=data['image']['width'];h=data['image']['height']
Image.open(D/'source.jpg').transpose(Image.Transpose.ROTATE_90).save(Q/'upright.png')
display['image']={'file':'upright.png','width':h,'height':w}
for s in display['spaces']:s['polygon_px']=[[y,w-x] for x,y in s['polygon_px']]
for r in display['relations']:
    if r['type']=='entrance':
        x,y=r['position_px'];r['position_px']=[y,w-x]
at.render(display,Q/'display.json',D/'标注.svg')
svg=ET.parse(D/'标注.svg');root=svg.getroot();ns={'s':at.NS}
texts=root.findall('s:text',ns)
texts[0].text='晋中市第一人民医院 · 一层概念标注'
texts[1].text='342 个具名空间／区域；21 处采用本轮接受的概念功能名称'
texts[-1].text='编号与名称直接显示；概念级标注不记录施工门位。'
svg.write(D/'标注.svg',encoding='unicode')

at.summary(data,D/'标注说明.md')
md=(D/'标注说明.md').read_text()
md=md.replace('# 平面标注概览','# 晋中市第一人民医院一层｜概念标注')
md=md.replace('空间名称已齐；结构与关系仍以原图及人工核对为依据。','空间名称已齐：本轮21项功能假设已按用户“同步更新”的要求采用为概念标签。部分名称属于接受的功能命名，并非从原图清晰辨认出的原始房名。')
scope='**范围：**普通门诊（西侧外科门诊、骨科及药房）、门诊公共大厅、急诊急救、MRI／CT／普放、中心供应及两处病房楼首层支持空间分开记录；住院支持空间不混作普通门诊诊室。三处内院保留轮廓，不计入室内占比。屋面、内院上空和院外空白不作为室内空间。\n\n**底图与坐标：**原图为1440×1725像素，SVG转正显示；JSON的空间边界及入口近似位置仍对应未旋转原图。\n\n'
md=md.replace('**标注规模：**',scope+'**标注规模：**')
md=md.replace('具体物理尺寸由生成环节按任务确定。','不保存平方米或像素面积字段。')
md+='\n**本轮采用的概念名称：**'+'、'.join(f'{q["sid"]} {q["name"]}' for q in hypotheses)+'。\n'
md+='\n**概念精度：**交通核与EICU保留整体节点。43号收费处、56号过道及其左侧洁具间、上方取药服务范围的既有修正均保留。人员可达、服务窗口与共墙关系分别记录；未记录的连接保持未知，不表示不可达。不记录施工级门位、门宽、门禁权限或内部精确路线。\n'
(D/'标注说明.md').write_text(md)

result,code=at.check(data,path,check_dir=True)
assert code==0,result
oldby={s['id']:s for s in before['spaces']};accepted={q['sid'] for q in hypotheses}
assert data['image']==before['image'] and data['relations']==before['relations']
for s in data['spaces']:
    old=oldby[s['id']]
    assert all(s[k]==old[k] for k in ['id','level','scope','polygon_px'])
    if s['id'] not in accepted:assert (s['name'],s['type'])==(old['name'],old['type'])
assert hashlib.sha256((D/'source.jpg').read_bytes()).digest()==hashlib.sha256((B/'source.jpg').read_bytes()).digest()
for s in display['spaces']:
    g=root.find(f'.//s:g[@id="{s["id"]}"]',ns)
    assert g is not None
    shown=''.join(e.text or '' for e in g.findall('s:text',ns))
    assert s['id'] in shown and s['name'] in shown,(s['id'],shown)
doc=pymupdf.open(D/'标注.svg');page=doc[0]
page.get_pixmap(matrix=pymupdf.Matrix(1.3,1.3),alpha=False).save(Q/'完整图.png')
head=86.25
for name,box in [('中心供应',(625,140,1040,405)),('南侧住院支持',(1080,580,1600,880)),('急诊服务',(800,925,1220,1305))]:
    x1,y1,x2,y2=box
    page.get_pixmap(matrix=pymupdf.Matrix(3,3),clip=pymupdf.Rect(x1,y1+head,x2,y2+head),alpha=False).save(Q/(name+'.png'))
(Q/'核验结果.json').write_text(json.dumps({**result,'adopted_concept_labels':21,'all_svg_names_visible':True,'decimal_area_sum':'1','geometry_and_relations_preserved':True,'original_source_preserved':True},ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False));print('Adopted 21 concept names; source, geometry, IDs, scopes, levels and relations preserved.')
