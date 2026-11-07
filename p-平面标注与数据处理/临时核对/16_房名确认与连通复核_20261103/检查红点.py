"""Draw manual opening selections over the source image for visual QA."""
from pathlib import Path
import json,sys
from PIL import ImageDraw,ImageFont
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT))
from 看图工具 import get_background,number_box,Polygon,box,DATA,FONT
A=json.loads((OUT/'待核验成果/annotation.json').read_text())
BOUNDS={'感染':(190,550,625,875),'药房':(615,550,1365,875),'服务':(1435,620,1890,885),
'住院核心':(1905,625,2580,885),'住院东侧':(2515,625,3210,980),
'办公':(190,945,530,1525),'儿科':(1028,945,1360,1545),
'急诊':(1345,945,1885,1545),'抢救':(1825,945,2485,1545)}
for n,b in BOUNDS.items():
 scale=3.0;im,_=get_background(b,scale,False);d=ImageDraw.Draw(im)
 f=ImageFont.truetype(FONT,18)
 for r in A['relations']:
  for o in r.get('openings',[]):
   x,y=o['position_px']
   if not (b[0]<=x<=b[2] and b[1]<=y<=b[3]):continue
   x,y=(x-b[0])*scale,(y-b[1])*scale
   d.ellipse((x-6,y-6,x+6,y+6),fill='#ff0000',outline='white',width=1)
   d.text((x+7,y-18),o['id'][1:],font=f,fill='#c00000',stroke_width=2,stroke_fill='white')
 for s in A['spaces']:
  poly=Polygon(s['polygon_px']);p=poly.representative_point()
  if not box(*b).covers(p):continue
  x,y,w,h,f2,bb=number_box(poly,s['id'][1:],b,scale,im,22)
  x,y=(x-b[0])*scale,(y-b[1])*scale
  d.rectangle((x,y,x+w,y+h),fill='white',outline='#0056a6',width=1)
  d.text((x+6,y+3-bb[1]),s['id'][1:],font=f2,fill='#0056a6')
 im.save(OUT/f'红点目检_{n}.jpg',quality=96)
print('9 opening review crops')
