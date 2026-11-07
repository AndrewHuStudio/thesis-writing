from pathlib import Path
import json,base64,hashlib,xml.etree.ElementTree as E
from shapely.geometry import Polygon,Point,LineString,box
out=Path(__file__).parent;stage=out/'待核验成果';d=json.loads((stage/'annotation.json').read_text());types=json.loads(Path('/Users/hushili/.codex/skills/outpatient-plan-annotation/references/space-types.json').read_text());NS='http://www.w3.org/2000/svg';XL='http://www.w3.org/1999/xlink';E.register_namespace('',NS);E.register_namespace('xlink',XL)
def el(tag,attr=None,text=None):
 e=E.Element('{'+NS+'}'+tag,{k:str(v) for k,v in (attr or {}).items()});e.text=text;return e
def txt(x,y,t,size=12,color='#18314c',bold=False):return el('text',{'x':x,'y':y,'font-size':size,'font-family':'Arial, PingFang SC, Microsoft YaHei, sans-serif','fill':color,'font-weight':700 if bold else 400},t)
def vw(t,f):return sum(f*(.59 if ord(c)<128 else 1) for c in t)
def wrap(t,f,w):
 lines=['']
 for c in t:
  if lines[-1] and vw(lines[-1]+c,f)>w:lines.append('')
  lines[-1]+=c
 return lines
W,H=3672,3064;head=125;foot=45
root=el('svg',{'width':W,'height':H+head+foot,'viewBox':f'0 0 {W} {H+head+foot}'})
root.append(el('rect',{'width':W,'height':H+head+foot,'fill':'white'}));root.append(txt(24,45,'晋中市第一人民医院迁建项目｜一层空间与开口标注',30,bold=True));root.append(txt(24,84,'343 个独立空间／区域；245 个门洞红点；名称沿用已确认内容，连通疑点见标注说明.md',22,'#854d0e'))
plan=el('g',{'id':'plan','transform':f'translate(0 {H+head}) rotate(-90)'});root.append(plan)
plan.append(el('image',{'width':3064,'height':3672,'{'+XL+'}href':'data:image/jpeg;base64,'+base64.b64encode((stage/d['image']['file']).read_bytes()).decode()}))
# 形状留在原图坐标；文字经逆变换保持转正可读。
inverse=f'translate({H} 0) rotate(90)'
opening_points=[Point(o['position_px'][1],H-o['position_px'][0]) for r in d['relations'] for o in r.get('openings',[])]
used=[];labelinfo=[]
def label_layout(poly,s):
 a=poly.representative_point();cx,cy=a.x,a.y;minx,miny,maxx,maxy=poly.bounds
 candidates=[(cx,cy),(poly.centroid.x,poly.centroid.y)]
 candidates.extend((minx+(maxx-minx)*fx,miny+(maxy-miny)*fy) for fx in [.25,.5,.75] for fy in [.25,.5,.75])
 opts=[]
 for x,y in candidates:
  if not poly.contains(Point(x,y)):continue
  def span(line):
   g=poly.intersection(line);gs=list(g.geoms) if hasattr(g,'geoms') else [g];parts=[q for q in gs if q.geom_type=='LineString' and q.distance(Point(x,y))<.1];return max(parts,key=lambda q:q.length).bounds if parts else poly.bounds
  hb=span(LineString([(minx-1,y),(maxx+1,y)]));vb=span(LineString([(x,miny-1),(x,maxy+1)]));mw=max(8,min(330,hb[2]-hb[0]-2));mh=max(8,vb[3]-vb[1]-2)
  for f in [14,12,11,10,9,8,7,6,5,4,3]:
   variants=[[s['id']]+wrap(s['name'],f,mw-6)+wrap('〔'+types[s['type']]+'〕',f,mw-6)]
   if vw(s['id']+' '+s['name'],f)<=mw-6:variants.insert(0,[s['id']+' '+s['name']]+wrap('〔'+types[s['type']]+'〕',f,mw-6))
   if mh<30 and vw(s['id']+' '+s['name']+'〔'+types[s['type']]+'〕',f)<=mw-6:variants.insert(0,[s['id']+' '+s['name']+'〔'+types[s['type']]+'〕'])
   for lines in variants:
    lw=max(vw(v,f) for v in lines)+6;lh=len(lines)*(f+2)+4
    if lw>mw or lh>mh:continue
    bb=box(x-lw/2,y-lh/2,x+lw/2,y+lh/2)
    if not poly.covers(bb):continue
    pts=[q for q in opening_points if q.distance(bb)<8]
    overlap=sum(bb.intersection(v).area for v in used if bb.intersects(v))
    score=f*1000-len(pts)*5000-overlap*20-Point(x,y).distance(a)-len(lines)*2
    opts.append((score,x-lw/2,y-lh/2,lw,lh,f,lines,bb))
 if opts:
  best=max(opts,key=lambda z:z[0]);return best[1:]
 f=5;lines=[s['id']]+wrap(s['name'],f,max(12,min(180,maxx-minx-8)))+wrap('〔'+types[s['type']]+'〕',f,max(12,min(180,maxx-minx-8)));lw=max(vw(l,f) for l in lines)+6;lh=len(lines)*7+4;return cx-lw/2,cy-lh/2,lw,lh,f,lines,box(cx-lw/2,cy-lh/2,cx+lw/2,cy+lh/2)
palette=['#2563eb','#0f766e','#7c3aed','#15803d','#b45309','#0369a1','#a21caf','#475569']
for s in d['spaces']:
 poly=Polygon([(y,H-x) for x,y in s['polygon_px']]);color=palette[int(hashlib.sha256(s['type'].encode()).hexdigest()[:4],16)%len(palette)]
 if s['level']=='semi_open_space':color='#059669'
 sg=el('g',{'id':s['id'],'data-space-name':s['name'],'data-space-type':s['type'],'data-space-type-name':types[s['type']]});plan.append(sg);sg.append(el('title',text=s['id']+' | '+s['name']+' | '+types[s['type']]));pa={'points':' '.join(f'{x},{y}' for x,y in s['polygon_px']),'fill':color,'fill-opacity':'.055','stroke':color,'stroke-width':'1.4'}
 if s['level']=='semi_open_space':pa['stroke-dasharray']='6 3'
 sg.append(el('polygon',pa));x,y,lw,lh,f,lines,bb=label_layout(poly,s);used.append(bb);lg=el('g',{'transform':inverse});sg.append(lg);lg.append(el('rect',{'x':x,'y':y,'width':lw,'height':lh,'rx':2,'fill':'white','fill-opacity':'.93','stroke':color,'stroke-width':'.7'}))
 for i,line in enumerate(lines):lg.append(txt(x+3,y+f+2+i*(f+2),line,f,color,True))
 labelinfo.append({'id':s['id'],'font':f,'lines':lines,'inside':poly.covers(bb),'bbox':[x,y,x+lw,y+lh]})
for r in d['relations']:
 for o in r.get('openings',[]):
  x,y=o['position_px'];g=el('g',{'id':o['id'],'data-opening-id':o['id'],'data-relation-id':r['id'],'data-source':r['source'],'data-target':r['target'],'data-kind':o['kind']});plan.append(g);g.append(el('title',text=f"{o['id']} | {r['id']} | {r['source']} ↔ {r['target']} | 门洞"));g.append(el('circle',{'cx':x,'cy':y,'r':4.7,'fill':'#dc2626','stroke':'white','stroke-width':'1.3'}));lg=el('g',{'transform':inverse});g.append(lg);t=txt(y+6,H-x-6,o['id'],9,'#b91c1c',True);t.set('stroke','white');t.set('stroke-width','2');t.set('paint-order','stroke');lg.append(t)
for r in d['relations']:
 if r['type']!='entrance':continue
 x,y=r['position_px'];ux,uy=y,H-x;g=el('g',{'id':r['id']});plan.append(g);g.append(el('circle',{'cx':x,'cy':y,'r':9,'fill':'white','stroke':'#be185d','stroke-width':'2'}));lg=el('g',{'transform':inverse});g.append(lg);label=r['id']+' '+r['name'];tx=max(8,min(W-vw(label,14)-10,ux+18));ty=uy+28;lg.append(txt(tx,ty,label,14,'#9d174d',True));lg.append(el('line',{'x1':ux,'y1':uy,'x2':tx,'y2':ty-7,'stroke':'#be185d','stroke-width':1.5}))
root.append(txt(24,H+head+30,'标签：S 编号＋具体名称＋〔标准功能类别〕；实心红点 P：已定位门洞；粉圈 E：建筑入口。无红点的连通状态详见 MD。',17,'#52677b'))
E.ElementTree(root).write(stage/'标注.svg',encoding='unicode');(out/'标签布局检查.json').write_text(json.dumps(labelinfo,ensure_ascii=False,indent=2));print('labels',len(labelinfo),'outside',[q['id'] for q in labelinfo if not q['inside']],'smallfont',sum(q['font']<7 for q in labelinfo))
