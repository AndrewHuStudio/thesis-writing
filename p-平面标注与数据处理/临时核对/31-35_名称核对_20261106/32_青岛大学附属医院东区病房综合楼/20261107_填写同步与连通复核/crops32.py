from sync_paths import P,W
from PIL import Image,ImageDraw,ImageFont
im=Image.open(P/'32_青岛大学附属医院东区病房综合楼_原图.jpg')
font=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',20)
regions={'A北侧':(1380,235,1930,645),'B西侧上':(365,1180,860,1605),'C西侧中':(365,1590,860,2145),'D西侧下':(365,2140,1050,2465),'E南侧':(365,2450,1045,2930),'F东侧中':(1380,1235,1930,2085),'G东侧下':(1380,2465,1810,2920),'H交通核':(875,790,1040,1190)}
for name,(x0,y0,x1,y1) in regions.items():
 scale=2
 out=Image.new('RGB',((x1-x0)*scale+100,(y1-y0)*scale+100),'white');out.paste(im.crop((x0,y0,x1,y1)).resize(((x1-x0)*scale,(y1-y0)*scale)),(60,60));dr=ImageDraw.Draw(out)
 for x in range((x0//50+1)*50,x1,50):
  xx=60+(x-x0)*scale;dr.line((xx,50,xx,60),fill='red',width=2);dr.text((xx-17,20),str(x),font=font,fill='red')
 for y in range((y0//50+1)*50,y1,50):
  yy=60+(y-y0)*scale;dr.line((50,yy,60,yy),fill='red',width=2);dr.text((0,yy-10),str(y),font=font,fill='red')
 out.save(W/f'{name}_原图坐标.png')
