from pathlib import Path
import json,sys,xml.etree.ElementTree as ET
from shapely.geometry import Polygon,box
import pymupdf
sys.path.insert(0,'/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts')
import annotation_tools as at
D=Path('/Users/hushili/Documents/毕业 - 大论文写作/大论文/p-写作过程/标注试样/3晋中市第一人民医院_一层')
Q=Path(__file__).parent/'同步后核验'
d=json.loads((D/'annotation.json').read_text());by={s['id']:s for s in d['spaces']}
tree=ET.parse(D/'标注.svg');root=tree.getroot();ns={'s':at.NS}
for sid in ['S142','S261','S262','S334']:
    s=by[sid];poly=Polygon([[y,1440-x] for x,y in s['polygon_px']]);a=poly.representative_point();x,y=a.x,a.y
    maxw=poly.bounds[2]-poly.bounds[0]-.8
    selected=None
    for fs in [7,6,5,4,3.5,3,2.5,2]:
        lines=[sid]+at.wrap(s['name'],fs,maxw-1)
        lw=max(at.visual_width(t,fs) for t in lines)+1
        step=fs+.5;lh=len(lines)*step+1
        if poly.covers(box(x-lw/2,y-lh/2,x+lw/2,y+lh/2)):
            selected=(fs,lines,lw,lh,step);break
    assert selected,sid
    fs,lines,lw,lh,step=selected;g=root.find(f'.//s:g[@id="{sid}"]',ns)
    oldtexts=g.findall('s:text',ns);color=oldtexts[0].get('fill')
    for e in list(g):
        if e.tag in ['{'+at.NS+'}text','{'+at.NS+'}rect']:g.remove(e)
    g.append(at.element('rect',{'x':x-lw/2,'y':y-lh/2,'width':lw,'height':lh,'rx':.6,'fill':'white','fill-opacity':'.96','stroke':color,'stroke-width':'.45'}))
    for i,line in enumerate(lines):g.append(at.txt(x-lw/2+.5,y-lh/2+fs+.3+i*step,line,fs,color,True))
    print(sid,fs,lines)
tree.write(D/'标注.svg',encoding='unicode')
for s in d['spaces']:
    g=root.find(f'.//s:g[@id="{s["id"]}"]',ns)
    shown=''.join(e.text or '' for e in g.findall('s:text',ns))
    assert s['id'] in shown and s['name'] in shown
doc=pymupdf.open(D/'标注.svg');p=doc[0]
p.get_pixmap(matrix=pymupdf.Matrix(1.3,1.3),alpha=False).save(Q/'完整图.png')
for name,b in [('中心供应',(625,140,1040,405)),('南侧住院支持',(1080,580,1600,880)),('急诊服务',(800,925,1220,1305))]:
    x1,y1,x2,y2=b
    p.get_pixmap(matrix=pymupdf.Matrix(3,3),clip=pymupdf.Rect(x1,y1+86.25,x2,y2+86.25),alpha=False).save(Q/(name+'.png'))
