from pathlib import Path
import json,xml.etree.ElementTree as ET,importlib.util,re,hashlib
from shapely.geometry import Polygon,box
out=Path(__file__).parent;p=out.parents[2]/'02_嘉兴市第一医院迁建工程';d=json.loads((p/'annotation.json').read_text());spec=importlib.util.spec_from_file_location('at','/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts/annotation_tools.py');at=importlib.util.module_from_spec(spec);spec.loader.exec_module(at);tag=lambda n:'{'+at.NS+'}'+n
root=ET.parse(p/'标注.svg').getroot();groups={e.get('id'):e for e in root.iter() if e.get('id') in {s['id'] for s in d['spaces']}};adjust=[]
for s in d['spaces']:
 g=groups[s['id']];poly=Polygon(s['polygon_px']);rs=[e for e in g if e.tag==tag('rect')]
 if len(rs)!=1 or s['id'] in ['S023','S261','S269','S270','S273']:continue
 r=rs[0];oldb=box(float(r.get('x')),float(r.get('y')),float(r.get('x'))+float(r.get('width')),float(r.get('y'))+float(r.get('height')))
 if poly.buffer(.5).covers(oldb):continue
 x0,y0,x1,y1=poly.bounds
 if x1-x0>80 or y1-y0>135:continue
 for fs in [6.5,6,5.5,5]:
  maxw=x1-x0-3;lines=[s['id']]+at.wrap(s['name'],fs,maxw-4)+at.wrap('〔'+at.TYPE_NAMES[s['type']]+'〕',fs,maxw-4);w=max(at.visual_width(t,fs) for t in lines)+4;h=len(lines)*(fs+1.2)+3;xx=(x0+x1-w)/2;yy=(y0+y1-h)/2
  if poly.buffer(.2).covers(box(xx,yy,xx+w,yy+h)):
   for e in list(g):
    if e.tag in [tag('rect'),tag('text')]:g.remove(e)
   attrs=dict(r.attrib);attrs.update(x=str(xx),y=str(yy),width=str(w),height=str(h));g.append(at.element('rect',attrs));col=r.get('stroke','#0f766e')
   for i,line in enumerate(lines):g.append(at.txt(xx+2,yy+fs+1+i*(fs+1.2),line,fs,col,True))
   adjust.append((s['id'],fs));break
ET.ElementTree(root).write(p/'标注.svg',encoding='unicode');print('dense labels adjusted',adjust)
md=(p/'标注说明.md').read_text();begin=md.index('| 核对号 | S编号 | 待确认内容');end=md.index('**校验状态：**',begin);prefix='../临时核对/'+p.name+'/'+out.name
qs=json.loads((out/'核对映射.json').read_text());table='| 核对号 | S编号 | 预估名称（可改） | 备选名称 | 依据与把握 | 我的确认／备注 | 核对号（重复） |\n| --- | --- | --- | --- | --- | --- | --- |\n'
for q in qs:
 n=q['number'];sids=q['spaces'];guess='沿用既有名称';alt='本项仅核对连接';ev=q['question']+' '+q['evidence']+' 连通把握：低，待确认。'
 if n=='09':guess='卫生间';alt='原名称：废物存放';ev='图中文字更接近“卫生间”，并见洁具；原名称保留仅为尊重既有确认，不作为反向证据。功能候选把握：中。'+q['question']
 if n=='10':guess='独立空间属性未确认';alt='S023 卫生间内洁具区域（可能不应独立分区）';ev='仅见洁具形构件，未见独立通道及通向 S024 的门；依据为构件与邻接范围。把握：中。'+q['question']
 table+=f'| {n} | {sids} | {guess} | {alt} | {ev} [局部]({prefix}/核对{n}_局部.png) | 待确认 | {n} |\n'
md=md[:begin]+table+'\n09、10 可修改“预估名称（可改）”，核对后在“我的确认／备注”填写实际名称、范围处理意见或“已确认”；其他项直接在确认栏填写连接的 S 编号及说明。每个核对项仅在本表填写一次。\n\n'+md[end:]
md=md.replace('**名称待确认：**','**功能／空间属性待确认（原名保留）：**')
md=md.replace('**校验状态：**待运行本轮正式 `validate --check-dir`；格式检查不能替代上述连通语义确认。','**正式校验结果（2026-11-01）：**`validate --check-dir` 返回 2：`valid=true`、结构/几何/四文件及红点对应错误 0；`names_complete=false`，未完成项为 S023、S273（原名称均保留，type=unknown）。因此正式完成校验尚未通过；另外 16 组功能、边界和连通核对项尚未闭环。已完成全图与急诊、药房、放射、核医学、行政区密集局部目视检查。')
(p/'标注说明.md').write_text(md)
# Independent consistency checks beyond the standard validator.
base=json.loads((out/'修改前备份'/'annotation.json').read_text());assert [(s['id'],s['name']) for s in base['spaces']]==[(s['id'],s['name']) for s in d['spaces']]
assert (p/d['image']['file']).read_bytes()==(out/'修改前备份'/d['image']['file']).read_bytes()
assert [r for r in base['relations'] if r['type']!='access']==[r for r in d['relations'] if r['type']!='access']
for s in d['spaces']:
 text=''.join(e.text or '' for e in groups[s['id']] if e.tag==tag('text'));assert s['id'] in text and s['name'] in text and '〔'+at.TYPE_NAMES[s['type']]+'〕' in text,(s['id'],text)
for match in re.finditer(r'\]\(([^)]+)\)',md):
 target=match.group(1)
 if '://' not in target:assert (p/target).exists(),target
assert [q['number'] for q in qs]==[f'{i:02}' for i in range(1,17)]
print('independent QA: stable 276 IDs/names; original bytes; all 276 visible labels/categories; non-access records; 16 review mappings; all MD links: OK')
print('original SHA256',hashlib.sha256((p/d['image']['file']).read_bytes()).hexdigest());print('files',sorted(f.name for f in p.iterdir() if f.is_file()))
