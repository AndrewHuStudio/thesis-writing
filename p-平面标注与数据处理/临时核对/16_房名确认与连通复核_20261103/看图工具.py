"""Evidence crops in original plan coordinates, with in-room stable identifiers."""
from pathlib import Path
import json,sys
import numpy as np,cv2
from PIL import Image,ImageDraw,ImageFont
from shapely.geometry import Polygon,box
OUT=Path(__file__).resolve().parent
BASE=OUT.parents[1]
sys.path.insert(0,str(BASE/'临时核对/16_房内编号核对_20261103'))
from 重绘房内编号 import get_background,number_box
DATA=json.loads((OUT/'待核验成果/annotation.json').read_text())
FONT='/System/Library/Fonts/STHeiti Medium.ttc'
def crop(bounds,name,scale=3,photo=True,labels=True):
 scale=float(scale)
 im,ph=get_background(bounds,scale,use_photo=photo)
 d=ImageDraw.Draw(im)
 if labels:
  for s in DATA['spaces']:
   poly=Polygon(s['polygon_px']);p=poly.representative_point()
   if not box(*bounds).covers(p):continue
   r=number_box(poly,s['id'][1:],bounds,scale,im,25)
   x,y,w,h,f,bb=r;x=(x-bounds[0])*scale;y=(y-bounds[1])*scale
   d.rectangle((x,y,x+w,y+h),fill='white',outline='#0056a6',width=2)
   d.text((x+6,y+3-bb[1]),s['id'][1:],font=f,fill='#0056a6')
 im.save(OUT/(name+'.jpg'),quality=95)
 print(name,bounds,ph,im.size)
if __name__=='__main__':
 for bounds,name in [((190,550,625,875),'感染'),((615,550,1365,875),'药房'),
 ((1445,625,1885,880),'北侧服务'),((1905,530,3210,980),'住院'),
 ((190,945,530,1525),'办公'),((1028,945,1360,1545),'儿科'),
 ((1345,945,1885,1545),'急诊'),((1825,945,2485,1545),'医护抢救')]:
  crop(bounds,name)
 crop((190,530,3210,1550),'一层原图',1,False,False)
