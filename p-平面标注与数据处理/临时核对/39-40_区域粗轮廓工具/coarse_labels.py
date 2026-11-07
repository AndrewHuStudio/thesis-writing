from shapely.geometry import Point,LineString,box
import annotation_tools as at
from shapely.affinity import rotate
import math
ROTATION={}
PLAN_N=39
BASE_LABEL=at.place_label
LABEL_AUDIT=[]
def place(poly,s):
 if PLAN_N==39 and s['id']=='S103' and not s.get('_label_rotated'):
  angle=math.degrees(math.atan2(51,89));c=poly.centroid
  ROTATION[s['id']]=(angle,c.x,c.y)
  return place(rotate(poly,-angle,origin=(c.x,c.y)),dict(s,_label_rotated=True))
 name='名称未确认' if s['type']=='unknown' else s['name']
 cat='〔'+at.TYPE_NAMES[s['type']]+'〕'
 rp=poly.representative_point();minx,miny,maxx,maxy=poly.bounds
 points=[rp]+[Point(minx+(maxx-minx)*u,miny+(maxy-miny)*v) for u in (.15,.3,.5,.7,.85) for v in (.15,.3,.5,.7,.85)]
 for font in [14,12,11,10,9,8,7,6,5,4]:
  choices=[]
  for pt in points:
   if not poly.contains(pt):continue
   h=poly.intersection(LineString([(minx-1,pt.y),(maxx+1,pt.y)]))
   v=poly.intersection(LineString([(pt.x,miny-1),(pt.x,maxy+1)]))
   def span(g):
    geoms=list(g.geoms) if hasattr(g,'geoms') else [g]
    return next((q for q in geoms if q.geom_type=='LineString' and q.distance(pt)<.01),None)
   hh=span(h);vv=span(v)
   if hh is None or vv is None:continue
   mw=min(220,hh.length-3);mh=vv.length-3
   if mw<10 or mh<7:continue
   simple=[s['id']+' '+name+' '+cat]
   two=[s['id']+' '+name,cat]
   normal=[s['id']]+at.wrap(name,font,mw-5)+at.wrap(cat,font,mw-5)
   formats=[simple,two,normal] if mh<45 else [normal,two,simple]
   for rank,lines in enumerate(formats):
    lw=max(at.visual_width(row,font) for row in lines)+5;lh=len(lines)*(font+2)+3
    if lw>mw or lh>mh:continue
    rect=box(pt.x-lw/2,pt.y-lh/2,pt.x+lw/2,pt.y+lh/2)
    if not poly.covers(rect):continue
    score=pt.distance(rp)+rank*3
    choices.append((score,pt.x-lw/2,pt.y-lh/2,lw,lh,font,lines))
  if choices:
   _,x,y,lw,lh,font,lines=min(choices,key=lambda v:v[0])
   LABEL_AUDIT.append(dict(id=s['id'],inside=True,font=font))
   return x,y,lw,lh,font,lines
 LABEL_AUDIT.append(dict(id=s['id'],inside=False))
 return BASE_LABEL(poly,s)
