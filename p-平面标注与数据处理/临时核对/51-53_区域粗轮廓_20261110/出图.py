from pathlib import Path
import sys,json,math,xml.etree.ElementTree as ET
import pymupdf
from shapely.geometry import Polygon,box,Point
from 本轮工具 import BASE,OUT
import annotation_tools as a
from region_overlay import COLORS

def label(parent,p,s,inverse=None):
    x,y,w,h,font,lines=a.place_label(p,s)
    color='#b45309' if s['type']=='unknown' else '#18314c'
    g=a.element('g',{'data-label-for':s['id']})
    if inverse:g.set('transform',inverse)
    g.append(a.element('rect',{'x':x,'y':y,'width':w,'height':h,'rx':2,'fill':'white',
        'fill-opacity':'.87','stroke':color,'stroke-width':'.6'}))
    for k,line in enumerate(lines):g.append(a.txt(x+3,y+font+2+k*(font+2),line,font,color,True))
    parent.append(g)
    return box(x,y,x+w,y+h)

for n in [51,52,53]:
    sample=next((BASE/'标注试样').glob(f'{n}_*'));q=OUT/sample.name
    d=json.loads((sample/'annotation.json').read_text());state=json.loads((q/'review_state.json').read_text())
    a.render(d,sample/'annotation.json',sample/'标注.svg',q/'review_state.json')
    tree=ET.parse(sample/'标注.svg');root=tree.getroot();ns='{'+a.NS+'}'
    plan=next(x for x in root if x.get('id')=='plan');w=d['image']['width'];h=d['image']['height'];head=125
    rotate=n in [51,52];dw,dh=(h,w) if rotate else (w,h)
    inverse=f'matrix(0 1 -1 0 {w} 0)' if rotate else None
    plan.set('transform',f'translate(0 {head})'+(f' translate(0 {w}) rotate(-90)' if rotate else ''))
    sp={s['id']:s for s in d['spaces']}
    label_boxes=[]
    for group in list(plan):
        if group.get('id') in sp:
            s=sp[group.get('id')]
            for child in list(group):
                if child.tag in [ns+'text',ns+'rect']:group.remove(child)
            pts=[(y,w-x) for x,y in s['polygon_px']] if rotate else s['polygon_px']
            label_boxes.append(label(group,Polygon(pts),s,inverse))
    point_positions=[]
    for r in d['relations']:
        for p in r.get('openings',[]):
            x,y=p['position_px'];point_positions.append((y,w-x) if rotate else (x,y))
    for group in list(plan):
        if group.get('data-opening-id'):
            circ=next(x for x in group if x.tag==ns+'circle')
            x,y=float(circ.get('cx')),float(circ.get('cy'))
            if rotate:x,y=y,w-x
            for child in list(group):
                if child.tag in [ns+'text',ns+'rect']:group.remove(child)
            g=a.element('g',{'transform':inverse} if inverse else {});font=8;tx,ty=x+5,y-5
            found=False
            for radius in (5,13,22,32,42,55):
                for dx,dy in [(radius,-5),(radius,13),(-24-radius,-5),(-24-radius,13),(0,-radius),(0,13+radius)]:
                    trial=box(x+dx-1,y+dy-font,x+dx+24,y+dy+3)
                    if any(trial.intersects(b) for b in label_boxes):continue
                    if any(trial.distance(Point(px,py))<4 for px,py in point_positions):continue
                    tx,ty=x+dx,y+dy;label_boxes.append(trial);found=True;break
                if found:break
            g.append(a.element('rect',{'x':tx-1,'y':ty-font,'width':25,'height':11,'fill':'white','fill-opacity':'.9'}))
            g.append(a.txt(tx,ty,group.get('data-opening-id'),font,'#b91c1c',True));group.append(g)
        elif rotate and str(group.get('id','')).startswith('E'):
            circle=next(x for x in group if x.tag==ns+'circle')
            x,y=float(circle.get('cx')),float(circle.get('cy'));x,y=y,w-x
            for c in list(group):
                if c is not circle:group.remove(c)
            r=next(r for r in d['relations'] if r['id']==group.get('id'))
            g=a.element('g',{'transform':inverse});t=r['id']+' '+r['name'];lw=a.visual_width(t,12)
            pts=[(yy,w-xx) for xx,yy in sp[r['target']]['polygon_px']];center=Polygon(pts).representative_point()
            dx,dy=x-center.x,y-center.y
            tx=x-lw-12 if dx<0 and abs(dx)>abs(dy) else x+12
            ty=y-14 if dy<0 and abs(dy)>=abs(dx) else y+20
            g.append(a.element('rect',{'x':tx-3,'y':ty-14,'width':a.visual_width(t,12)+6,'height':18,'fill':'white','fill-opacity':'.92'}))
            g.append(a.txt(tx,ty,t,12,'#9d174d',True));group.append(g)
    for child in list(root):
        if child is not plan:root.remove(child)
    rows=math.ceil(len(state['regions'])/3);legend_y=dh+head+20;totalh=legend_y+70+rows*32
    root.set('width',str(dw));root.set('height',str(totalh));root.set('viewBox',f'0 0 {dw} {totalh}')
    root.insert(0,a.element('rect',{'width':dw,'height':totalh,'fill':'white'}))
    root.append(a.txt(15,37,f'{sample.name}｜逐空间粗轮廓',26,bold=True))
    unknown=sum(s['type']=='unknown' for s in d['spaces']);pn=sum(len(r.get('openings',[])) for r in d['relations'])
    root.append(a.txt(15,72,f'{len(sp)} 个空间；{len(state["regions"])} 个区域外框；{pn} 个定位开口；{unknown} 项缺名保持 unknown',18,'#b45309'))
    root.append(a.txt(15,101,'粗轮廓为近似范围；区域外框不另计面积。红点对应人员通行开口，E 为建筑／楼层边界接口。',16,'#52677b'))
    root.append(a.txt(15,legend_y+25,'区域概览（成员归属不表示内部所有房间互通）',21,bold=True))
    for k,r in enumerate(state['regions']):
        root.append(a.txt(15+(k%3)*dw/3,legend_y+62+(k//3)*32,r['id']+' '+r['name'],17,COLORS[k%len(COLORS)],True))
    tree.write(sample/'标注.svg',encoding='utf-8',xml_declaration=True)
    doc=pymupdf.open(sample/'标注.svg');page=doc[0];page.get_pixmap().save(q/'正式SVG全图.png')
    # 本轮阅读坐标统一转正，仅显示变换，核心数据坐标不改。
    boxes={51:[(130,1180,1080,1530),(1060,1510,1700,1860),(130,1840,1660,2100)],
           52:[(420,1040,1460,1755),(1420,1040,1900,1600)],
           53:[(640,90,1745,420),(450,590,980,1100),(1370,670,1790,1190),(900,1220,1460,1700)]}
    for k,b in enumerate(boxes[n],1):
        rect=pymupdf.Rect(b[0],b[1]+head,b[2],b[3]+head)
        page.get_pixmap(matrix=pymupdf.Matrix(1.5,1.5),clip=rect).save(q/f'正式SVG局部{k}.png')
    print(n,'rendered',dw,totalh)
