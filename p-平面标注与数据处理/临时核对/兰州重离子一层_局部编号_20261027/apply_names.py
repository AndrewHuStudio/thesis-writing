from pathlib import Path
import json,copy,shutil,sys,hashlib
from decimal import Decimal
import xml.etree.ElementTree as ET
from shapely.geometry import Polygon,box
from PIL import Image,ImageDraw,ImageFont
import pymupdf

ROOT=Path('/Users/hushili/Documents/毕业 - 大论文写作/大论文')
D=ROOT/'p-写作过程/标注试样/5兰州重离子医用加速应用示范区_一层'
O=Path(__file__).parent/'名称更新_20261027';O.mkdir(exist_ok=True)
B=O/'修改前备份';B.mkdir(exist_ok=True)
for p in D.iterdir():
    if p.is_file() and not (B/p.name).exists():shutil.copy2(p,B/p.name)
sys.path.insert(0,'/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts')
import annotation_tools as at
before=json.loads((B/'annotation.json').read_text());data=copy.deepcopy(before)
mapping=json.loads((Path(__file__).parent/'编号对应.json').read_text());nums={q['number']:q['sid'] for q in mapping}
by={s['id']:s for s in data['spaces']}
answers={
 1:('药房','pharmacy'),2:('配电室','building_services'),3:('设备','equipment_room'),4:('控制','service_work_area'),
 5:('中庭','unknown'),6:('强电','building_services'),7:('弱电','building_services'),
 8:('试品','storage'),9:('静脉输液入口区','vestibule'),
 11:('消防控制室','building_control'),12:('二更','staff_support'),13:('结算','registration'),14:('库房','storage'),
 15:('餐包','service_work_area'),16:('净化机房','building_services'),17:('输液空间','treatment'),
 18:('二更','staff_support'),20:('中药房（二房）','pharmacy'),21:('出住院办理','registration'),22:('西药房（二级）','pharmacy'),
 23:('新风机房（大厅）','building_services'),24:('中庭','unknown'),25:('强电','building_services'),26:('弱电','building_services'),
 27:('处置','treatment'),28:('办公','office'),30:('更衣','staff_support'),31:('更衣','staff_support'),32:('洁具','staff_support'),
}
for n,(name,typ) in answers.items():by[nums[n]].update(name=name,type=typ)
for n in [5,24]:by[nums[n]].update(level='open_space',scope='public_service')
by[nums[9]]['level']='open_space'
by[nums[9]]['scope']='infusion_support';by[nums[17]]['scope']='infusion_support'
by[nums[21]]['scope']='inpatient_support';by[nums[23]]['scope']='public_service'

# Merge only the two pairs explicitly identified as one room. Include the
# narrow annotation seam; it is not a confirmed wall inside the actual room.
by[nums[18]]['polygon_px']=[[2189.36,1407.29],[2234.18,1407.29],[2234.18,1499.16],[2189.36,1499.16]]
by[nums[28]]['polygon_px']=[[759.67,3152.95],[887.4,3152.95],[887.4,3300.85],[826.89,3289.64],[822.41,3287.4],[759.67,3273.96]]
aliases={nums[19]:nums[18],nums[29]:nums[28]}
data['spaces']=[s for s in data['spaces'] if s['id'] not in aliases]
relations=[];seen=set();removed=[]
for old in data['relations']:
    r=copy.deepcopy(old)
    r['source']=aliases.get(r['source'],r['source']);r['target']=aliases.get(r['target'],r['target'])
    if r['source']==r['target']:removed.append(old['id']);continue
    key=('entrance',r['id']) if r['type']=='entrance' else (tuple(sorted((r['source'],r['target']))),r['type'])
    if key in seen:removed.append(old['id']);continue
    seen.add(key);relations.append(r)
data['relations']=relations
at.normalize(data)
largest=max(data['spaces'],key=lambda s:s.get('area_ratio',0))
delta=Decimal(1)-sum(Decimal(str(s.get('area_ratio',0))) for s in data['spaces'])
largest['area_ratio']=float(Decimal(str(largest['area_ratio']))+delta)
assert sum(Decimal(str(s.get('area_ratio',0))) for s in data['spaces'])==Decimal(1)
path=D/'annotation.json';path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
at.render(data,path,D/'标注.svg')
tree=ET.parse(D/'标注.svg');root=tree.getroot();ns={'s':at.NS}
root.findall('s:text',ns)[0].text='兰州重离子医用加速应用示范区 · 一层标注草稿'
root.findall('s:text',ns)[1].text='127 个空间／区域；10号名称未确认，05与24号中庭面积属性待核'
for n in [5,24]:
    g=root.find(f'.//s:g[@id="{nums[n]}"]',ns)
    for e in g.findall('s:text',ns):
        if e.text=='名称未确认':e.text='中庭'
tree.write(D/'标注.svg',encoding='unicode')
at.summary(data,D/'标注说明.md')
md=(D/'标注说明.md').read_text()
md=md.replace('# 平面标注概览','# 兰州重离子医用加速应用示范区一层｜标注草稿')
md=md.replace('未完成：3 个空间名称尚未确认。','未完成：10号（S042）名称未确认；05号（S034）、24号（S074）已明确名为“中庭”，室内／露天或挑空属性待核。')
start=md.index('**名称待确认：**')
md=md[:start]+'**待核内容：**10号（S042）名称未确认；05号（S034）、24号（S074）中庭面积及通行属性待核。\n'
md=md.replace('具体物理尺寸由生成环节按任务确定。','不保存平方米或像素面积字段。两处中庭面积属性待核，当前暂沿用原室内分母，不能作为最终面积版本。')
md+='\n**范围与精度：**一层普通门诊、影像、配液及输液支持、急诊、药房支持和公共服务分别记录。图像为3079×4088像素照片，坐标与原图一致；未经透视校正，相对面积不代表实测建筑面积。未记录的关系保持未知，不推断门禁权限。\n'
md+='\n**单元修正：**18—19合为“二更”（S057），28—29合为“办公”（S111）。S058与S112已并入对应空间，其余S编号不改。合并引起的自连接和重复连接已清理。周围“一更、洗手间”等提示未在缺乏明确范围时拆出新节点。\n'
md+='\n**名称与分类：**08“试品”、15“餐包”暂保留用户原字，未自行更正；06、07及25、26按回复列举顺序分别记为强电、弱电。“中药房（二房）”“西药房（二级）”保留原名。09、17分别采用“静脉输液入口区”“输液空间”的概念功能名称。\n'
md+='\n**核对材料：**原01—32核对号保留在[局部核对材料](<'+str(Path(__file__).parent/'按局部顺序查看.md')+'>)。最终样本目录仍仅原图、SVG、JSON、MD四文件。\n'
(D/'标注说明.md').write_text(md)
updated=[]
for q in mapping:
    r=copy.deepcopy(q);sid=aliases.get(q['sid'],q['sid']);s=next(s for s in data['spaces'] if s['id']==sid)
    r.update(current_sid=sid,name=s['name'],type=s['type'],polygon_px=s['polygon_px']);updated.append(r)
(O/'本轮核对映射.json').write_text(json.dumps(updated,ensure_ascii=False,indent=2)+'\n')
result,code=at.check(data,path,check_dir=True)
assert result['valid'],result
assert len(data['spaces'])==127 and len(data['relations'])==156
assert {s['id'] for s in data['spaces'] if s['type']=='unknown'}=={nums[n] for n in [5,10,24]}
assert hashlib.sha256((D/'source.jpg').read_bytes()).digest()==hashlib.sha256((B/'source.jpg').read_bytes()).digest()
for s in data['spaces']:
    if s['type']=='unknown':continue
    g=root.find(f'.//s:g[@id="{s["id"]}"]',ns)
    shown=''.join(e.text or '' for e in g.findall('s:text',ns))
    assert s['id'] in shown and s['name'] in shown,(s['id'],shown)
doc=pymupdf.open(D/'标注.svg');p=doc[0]
p.get_pixmap(matrix=pymupdf.Matrix(.6,.6),alpha=False).save(O/'完整图.png')
for name,b in [('配液区',(1800,880,2780,1530)),('中庭与强弱电',(750,2140,2340,2380)),('急诊合并办公',(620,3070,1100,3380))]:
    x1,y1,x2,y2=b;p.get_pixmap(clip=pymupdf.Rect(x1,y1+125,x2,y2+125),matrix=pymupdf.Matrix(1.6,1.6),alpha=False).save(O/(name+'.png'))
# Focused unaltered photograph for the one remaining unnamed room.
im=Image.open(D/'source.jpg').convert('RGB');bounds=(1810,900,2150,1360);crop=im.crop(bounds).resize((850,1150))
dr=ImageDraw.Draw(crop);pts=[((x-bounds[0])*2.5,(y-bounds[1])*2.5) for x,y in by[nums[10]]['polygon_px']]
dr.line(pts+[pts[0]],fill='#d97706',width=4);font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Unicode.ttf',38)
dr.rectangle((420,353,492,405),fill='white',outline='#d97706',width=2);dr.text((427,355),'10',font=font,fill='#b45309');crop.save(O/'10号名称待确认.png')
(O/'核验结果.json').write_text(json.dumps({**result,'validation_exit':code,'merged_aliases':aliases,'removed_relations':removed,'original_source_unchanged':True},ensure_ascii=False,indent=2))
print(json.dumps({**result,'validation_exit':code,'merged_aliases':aliases,'removed_relations':removed},ensure_ascii=False))
