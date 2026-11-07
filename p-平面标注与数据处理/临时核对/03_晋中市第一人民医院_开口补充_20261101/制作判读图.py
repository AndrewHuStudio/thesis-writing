from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
out=Path(__file__).parent
regions={'A中心供应':(640,155,990,390),'B_MRI_CT':(640,400,990,655),'C普放':(640,650,990,870),'D北病房':(1090,45,1590,295),'E南病房':(1090,585,1590,875),'F门诊上':(205,375,550,820),'G门诊下':(205,860,555,1310),'H急诊':(800,915,1220,1300),'I中部衔接':(530,370,1040,990)}
font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',17)
for name,(x0,y0,x1,y1) in regions.items():
 for kind,src in [('原图','原图转正.png'),('编号','S编号底图.png')]:
  im=Image.open(out/src);box=tuple(round(v*f) for v,f in zip((x0,y0,x1,y1),(3672/1725,3064/1440)*2));im=im.crop(box);dr=ImageDraw.Draw(im)
  for x in range((x0//20+1)*20,x1,20):
   xx=round((x-x0)*3672/1725);dr.line((xx,0,xx,10),fill='red',width=1);dr.text((xx+2,0),str(x),font=font,fill='#c40000',stroke_width=1,stroke_fill='white')
  for y in range((y0//20+1)*20,y1,20):
   yy=round((y-y0)*3064/1440);dr.line((0,yy,10,yy),fill='red',width=1);dr.text((0,yy+1),str(y),font=font,fill='#c40000',stroke_width=1,stroke_fill='white')
  im.save(out/f'{name}_{kind}.png')
