from pathlib import Path
import cv2,json,numpy as np
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parent
P=R.parent.parent/'标注试样/15_盐城市妇幼保健院'
d=json.loads((P/'annotation.json').read_text());spaces={s['id']:s for s in d['spaces']}
m=json.loads((R.parent/'15_盐城市妇幼保健院_名称核对_20261101/核对号映射.json').read_text());by_num={int(r['number']):r for r in m}
reg={r['photo']:np.array(r['H']) for r in json.loads((R/'照片配准结果.json').read_text())}
photos={n:cv2.imread(str(R/'用户补充照片'/f'照片{n:02}.jpg')) for n in range(1,12)}
selection={1:[11,12,14,15],3:[49,50,52,53],4:[87,90,98,99,102,103,172],6:[119,122,123,130,131,134,135],9:[179,182,184,188,197,199,200,251,253,256],10:[293,295,310,327]}
items=[]
for ph,nums in selection.items():
 for num in nums:
  row=by_num[num];s=spaces[row['id']];pts=np.array(s['polygon_px']);x0,y0=pts.min(0)-[10,8];x1,y1=pts.max(0)+[10,8]
  scale=5.;T=np.array([[scale,0,-x0*scale],[0,scale,-y0*scale],[0,0,1.]])
  im=cv2.warpPerspective(photos[ph],T@np.linalg.inv(reg[f'照片{ph:02}.jpg']),(int((x1-x0)*scale),int((y1-y0)*scale)),borderValue=(255,255,255))
  im=Image.fromarray(cv2.cvtColor(im,cv2.COLOR_BGR2RGB));im.thumbnail((490,270))
  items.append((num,row['id'],ph,im))
for page in range((len(items)+11)//12):
 canvas=Image.new('RGB',(2000,930),'white');draw=ImageDraw.Draw(canvas)
 for i,(num,sid,ph,im) in enumerate(items[page*12:(page+1)*12]):
  x=(i%4)*500;y=(i//4)*310
  draw.text((x+6,y+4),f'{num} / {sid} / photo {ph:02}',fill='black',font=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',18))
  canvas.paste(im,(x+(500-im.width)//2,y+33))
 canvas.save(R/f'疑字核对{page+1:02}.jpg')
