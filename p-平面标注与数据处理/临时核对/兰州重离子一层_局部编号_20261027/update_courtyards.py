from pathlib import Path
import json,copy,sys,shutil,hashlib
from decimal import Decimal
import xml.etree.ElementTree as ET
import pymupdf

ROOT=Path('/Users/hushili/Documents/毕业 - 大论文写作/大论文')
D=ROOT/'p-写作过程/标注试样/5兰州重离子医用加速应用示范区_一层'
O=Path(__file__).parent/'中庭确认_20261027';O.mkdir(exist_ok=True)
B=O/'修改前备份';B.mkdir(exist_ok=True)
for p in D.iterdir():
    if p.is_file() and not (B/p.name).exists():shutil.copy2(p,B/p.name)
sys.path.insert(0,'/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts')
import annotation_tools as at
path=D/'annotation.json';data=json.loads(path.read_text());before=copy.deepcopy(data)
by={s['id']:s for s in data['spaces']};courts={'S034','S074'}
assert by['S039']['name']=='试品' and by['S054']['name']=='餐包'
for sid in courts:
    by[sid].update(name='中庭',type='courtyard',level='open_space',scope='public_service')
    by[sid].pop('area_ratio',None)
removed=[r for r in data['relations'] if r['type']=='access' and (r['source'] in courts or r['target'] in courts)]
data['relations']=[r for r in data['relations'] if r not in removed]
at.normalize(data)
indoor=[s for s in data['spaces'] if at.indoor(s)]
largest=max(indoor,key=lambda s:s['area_ratio'])
residual=Decimal(1)-sum(Decimal(str(s['area_ratio'])) for s in indoor)
largest['area_ratio']=float(Decimal(str(largest['area_ratio']))+residual)
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
at.render(data,path,D/'标注.svg')
tree=ET.parse(D/'标注.svg');root=tree.getroot();ns={'s':at.NS}
texts=root.findall('s:text',ns)
texts[0].text='兰州重离子医用加速应用示范区 · 一层标注草稿'
texts[1].text='127 个区域（含2处露天／挑空中庭）；仅10号（S042）名称未确认'
texts[-1].text='黄色为名称未确认；露天／挑空中庭仅保留轮廓，不计入室内面积。'
for sid in courts:
    g=root.find(f'.//s:g[@id="{sid}"]',ns);p=g.find('s:polygon',ns)
    p.set('fill','#dce8ee');p.set('fill-opacity','.15');p.set('stroke','#64748b');p.set('stroke-dasharray','10 5')
tree.write(D/'标注.svg',encoding='unicode')
at.summary(data,D/'标注说明.md')
md=(D/'标注说明.md').read_text().replace('# 平面标注概览','# 兰州重离子医用加速应用示范区一层｜标注草稿')
md=md.replace('未完成：1 个空间名称尚未确认。','未完成：仅10号（S042）空间名称未确认。08“试品”、15“餐包”已按用户确认的原名保留。')
md=md.replace('绿化不参与。具体物理尺寸由生成环节按任务确定。','绿化及露天／挑空中庭不参与。不保存平方米或像素面积字段。')
md+='\n**中庭与面积：**05号（S034）、24号（S074）为不计室内面积的露天／挑空中庭，保留编号、名称及原轮廓，类型为 courtyard，不保存 area_ratio。127个区域包含125个室内区域及2处中庭；室内面积已重新归一化。两处中庭原先按室内房间记录的人员可达连接已移除，不再作为室内穿行节点。\n'
md+='\n**范围与精度：**一层普通门诊、影像、配液及输液支持、急诊、药房支持和公共服务分别记录。图像为3079×4088像素照片，坐标与原图一致；未经透视校正，相对面积不代表实测建筑面积。未记录的关系保持未知，不推断门禁权限。\n'
md+='\n**单元修正：**18—19合为“二更”（S057），28—29合为“办公”（S111）。S058与S112已并入对应空间，其余S编号不改。合并引起的自连接和重复连接已清理。周围“一更、洗手间”等提示未在缺乏明确范围时拆出新节点。\n'
md+='\n**名称与分类：**08“试品”、15“餐包”按已确认的原名记录；06、07及25、26按回复列举顺序分别记为强电、弱电。“中药房（二房）”“西药房（二级）”保留原名。09、17分别采用“静脉输液入口区”“输液空间”的概念功能名称。\n'
md+='\n**剩余核对：**[10号局部图](<'+str(Path(__file__).parent/'名称更新_20261027/10号名称待确认.png')+'>)。原01—32核对号保留在临时核对材料中；最终样本目录仍仅原图、SVG、JSON、MD四文件。\n'
(D/'标注说明.md').write_text(md)
assert all('area_ratio' not in by[sid] for sid in courts)
assert sum(Decimal(str(s['area_ratio'])) for s in indoor)==Decimal(1)
assert len(indoor)==125 and len(data['spaces'])==127 and len(data['relations'])==154
for old,s in zip(before['spaces'],data['spaces']):
    assert s['id']==old['id'] and s['polygon_px']==old['polygon_px']
    if s['id'] not in courts:assert (s['name'],s['type'])==(old['name'],old['type'])
assert hashlib.sha256((D/'source.jpg').read_bytes()).digest()==hashlib.sha256((B/'source.jpg').read_bytes()).digest()
assert len(list(D.iterdir()))==4
result,code=at.check(data,path,check_dir=True)
assert result['valid'] and result['pending_name_ids']==['S042'] and code==2,result
for s in data['spaces']:
    g=root.find(f'.//s:g[@id="{s["id"]}"]',ns)
    shown=''.join(e.text or '' for e in g.findall('s:text',ns))
    assert s['id'] in shown and s['name'] in shown,(s['id'],shown)
doc=pymupdf.open(D/'标注.svg');page=doc[0]
page.get_pixmap(matrix=pymupdf.Matrix(.6,.6),alpha=False).save(O/'完整图.png')
page.get_pixmap(matrix=pymupdf.Matrix(1.8,1.8),clip=pymupdf.Rect(750,2250,2340,2510),alpha=False).save(O/'中庭复核.png')
report={**result,'indoor_spaces':len(indoor),'courtyards':sorted(courts),'indoor_ratio_sum':'1','removed_access_relation_ids':[r['id'] for r in removed],'source_unchanged':True}
(O/'核验结果.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False))
