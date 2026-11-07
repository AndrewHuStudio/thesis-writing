from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from shapely.geometry import Polygon,Point,box
import json
base=Path('/Users/hushili/Documents/研究-论文写作/大论文/p-平面标注与数据处理');root=base/'标注试样/29_内蒙古自治区国际蒙医医院扩建项目';w=base/'临时核对/29_内蒙古自治区国际蒙医医院扩建项目';run=Path((w/'当前续作目录.txt').read_text().strip());d=json.loads((root/'annotation.json').read_text());src=Image.open(root/d['image']['file']).transpose(Image.Transpose.ROTATE_90).convert('RGB');font='/System/Library/Fonts/STHeiti Medium.ttc'
def draw(name,b,scale=2):
 im=src.crop(b).resize(((b[2]-b[0])*scale,(b[3]-b[1])*scale));out=Image.new('RGB',(im.width+100,im.height+100),'white');out.paste(im,(50,50));dr=ImageDraw.Draw(out)
 for u in range((b[0]//50+1)*50,b[2],50):
  x=50+(u-b[0])*scale;dr.text((x-18,16),str(u),font=ImageFont.truetype(font,18),fill='black');dr.line((x,40,x,50),fill='black')
 for v in range((b[1]//50+1)*50,b[3],50):
  y=50+(v-b[1])*scale;dr.text((2,y-8),str(v),font=ImageFont.truetype(font,18),fill='black');dr.line((40,y,50,y),fill='black')
 for s in d['spaces']:
  p=Polygon([(y,2444-x) for x,y in s['polygon_px']]);c=p.representative_point()
  if not box(*b).covers(c):continue
  # Use a small badge and preserve the raw image alongside for opening judgment.
  candidates=[Point(c.x,c.y-12),Point(c.x,c.y+12),c]
  for q in candidates:
   if p.covers(box(q.x-9,q.y-5,q.x+9,q.y+5)):c=q;break
  label=s['id'][1:];x=50+(c.x-b[0])*scale;y=50+(c.y-b[1])*scale
  dr.rectangle((x-18,y-11,x+18,y+13),fill='white',outline='#0055bb');dr.text((x-16,y-11),label,font=ImageFont.truetype(font,20),fill='#0055bb')
 out.save(run/(name+'_S号坐标.png'))
for name,b in [('西部',(570,1120,1080,1790)),('检查',(1065,990,1445,1400)),('黄色',(1060,1450,1575,1785)),('主入口',(1430,1320,2035,1980)),('蓝色北',(1890,1070,2360,1445)),('蓝色南',(1900,1430,2365,1970)),('独立区',(1570,560,2410,995)),('东药库',(1995,340,2615,865)),('扇形',(85,1120,595,2010))]:draw(name,b)
print(run)
