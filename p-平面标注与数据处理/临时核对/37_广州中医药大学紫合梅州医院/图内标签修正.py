"""Keep the whole visible label inside each irregular space; original geometry is unchanged."""
from pathlib import Path
import json,math,sys
import xml.etree.ElementTree as ET
from shapely.geometry import Polygon,box
from shapely.affinity import rotate
sys.path.insert(0,'/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts')
import annotation_tools as ann

def fit(poly,s):
    corners=list(poly.minimum_rotated_rectangle.exterior.coords)[:4]
    edges=[(math.hypot(b[0]-a[0],b[1]-a[1]),math.degrees(math.atan2(b[1]-a[1],b[0]-a[0])))
           for a,b in zip(corners,corners[1:]+corners[:1])]
    angle=max(edges)[1]
    if angle>90:angle-=180
    if angle<-90:angle+=180
    angles=[0]+([angle] if abs(angle)>1 else [])
    name='名称未确认' if s['type']=='unknown' else s['name']
    for fs in [10,9,8,7,6,5,4,3]:
        for theta in angles:
            p=rotate(poly,-theta,origin=(0,0));x0,y0,x1,y1=p.bounds;rp=p.representative_point()
            for width in [min(200,x1-x0-2),min(120,x1-x0-2),min(80,x1-x0-2),
                          min(50,x1-x0-2),min(32,x1-x0-2),min(20,x1-x0-2),min(12,x1-x0-2)]:
                if width<fs*2:continue
                lines=[s['id']]+ann.wrap(name,fs,width-4)
                if s['type']!='unknown':lines+=ann.wrap('〔'+ann.TYPE_NAMES[s['type']]+'〕',fs,width-4)
                w=max(ann.visual_width(a,fs) for a in lines)+4;h=len(lines)*(fs+1)+3
                if w>x1-x0 or h>y1-y0:continue
                centers=[(rp.x,rp.y)]+[(x0+w/2+(x1-x0-w)*ix/12,y0+h/2+(y1-y0-h)*iy/12)
                    for iy in range(13) for ix in range(13)]
                for cx,cy in centers:
                    rect=box(cx-w/2,cy-h/2,cx+w/2,cy+h/2)
                    if p.covers(rect):
                        world=rotate(rect,theta,origin=(0,0))
                        return dict(x=cx-w/2,y=cy-h/2,w=w,h=h,font=fs,lines=lines,
                                    angle=theta,world_polygon=list(world.exterior.coords))
    return None

def fix_labels(tree,data):
    ns={'s':ann.NS};S={s['id']:s for s in data['spaces']};audit=[]
    for group in tree.getroot().iter():
        sid=group.get('id')
        if sid not in S:continue
        s=S[sid];poly=Polygon([(y,2484-x) for x,y in s['polygon_px']]);rect=group.find('s:rect',ns)
        if rect is None:continue
        x,y,w,h=[float(rect.get(k)) for k in ['x','y','width','height']]
        if poly.covers(box(x,y,x+w,y+h)):
            audit.append(dict(space_id=sid,inside=True,changed=False));continue
        fitted=fit(poly,s)
        if not fitted:
            audit.append(dict(space_id=sid,inside=False,changed=False));continue
        for child in list(group):
            if child.tag in ('{'+ann.NS+'}rect','{'+ann.NS+'}text'):group.remove(child)
        color=group.find('s:polygon',ns).get('stroke')
        g=ann.element('g',{'data-label-for':sid,'transform':f'rotate({fitted["angle"]})',
                          'data-label-polygon':json.dumps(fitted['world_polygon'])})
        group.append(g)
        g.append(ann.element('rect',dict(x=fitted['x'],y=fitted['y'],width=fitted['w'],height=fitted['h'],
            fill='#fff7df' if s['type']=='unknown' else 'white',rx=1,**{'fill-opacity':'.94','stroke':color,'stroke-width':'.5'})))
        for i,line in enumerate(fitted['lines']):
            g.append(ann.txt(fitted['x']+2,fitted['y']+fitted['font']+1+i*(fitted['font']+1),line,fitted['font'],color,True))
        audit.append(dict(space_id=sid,inside=True,changed=True,font=fitted['font'],angle=fitted['angle']))
    return audit

if __name__=='__main__':
    R=Path(__file__).resolve().parent;P=R.parent.parent/'标注试样'/R.name
    d=json.loads((P/'annotation.json').read_text());tree=ET.parse(P/'标注.svg')
    audit=fix_labels(tree,d);tree.write(P/'标注.svg',encoding='unicode')
    (R/'逐房间SVG标签审计.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
    print('changed',sum(a['changed'] for a in audit),'failures',[a for a in audit if not a['inside']])
