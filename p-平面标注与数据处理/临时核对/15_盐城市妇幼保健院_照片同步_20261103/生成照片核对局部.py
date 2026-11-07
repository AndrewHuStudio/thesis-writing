from pathlib import Path
import json,cv2,numpy as np
R=Path(__file__).resolve().parent
P=R.parent.parent/'标注试样/15_盐城市妇幼保健院'
d=json.loads((P/'annotation.json').read_text());spaces={s['id']:s for s in d['spaces']}
m=json.loads((R.parent/'15_盐城市妇幼保健院_名称核对_20261101/核对号映射.json').read_text())
reg={r['photo']:r for r in json.loads((R/'照片配准结果.json').read_text())}
out=R/'照片定位局部';out.mkdir(exist_ok=True)
# Crops remain in the coordinate system of the existing plan.
tasks=[(0,2),(1,1),(2,3),(3,4),(3,5),(4,6),(5,4),(5,7),(6,5),(7,6),(8,7),(9,5),(10,8),(11,7),(12,10),(13,10),(13,11),(6,9),(9,9),(11,10),(10,11),(12,11),(0,5)]
for group,photo in tasks:
    rows=[r for r in m if r['group']==group]
    pts=np.array([pt for r in rows for pt in spaces[r['id']]['polygon_px']])
    x0,y0=pts.min(0)-8;x1,y1=pts.max(0)+8
    scale=3
    T=np.array([[scale,0,-x0*scale],[0,scale,-y0*scale],[0,0,1.]])
    H=np.array(reg[f'照片{photo:02}.jpg']['H'])
    src=cv2.imread(str(R/'用户补充照片'/f'照片{photo:02}.jpg'))
    im=cv2.warpPerspective(src,T@np.linalg.inv(H),(int((x1-x0)*scale),int((y1-y0)*scale)),borderValue=(255,255,255))
    name=f'片区{group+1:02}_照片{photo:02}'
    cv2.imwrite(str(out/(name+'_无标记.jpg')),im)
    for row in rows:
        poly=np.array(spaces[row['id']]['polygon_px'])
        pp=np.int32((poly-[x0,y0])*scale)
        cv2.polylines(im,[pp],True,(220,100,25),2)
        ax,ay=pp.min(0)+[3,18]
        text=row['number']
        cv2.rectangle(im,(ax-1,ay-15),(ax+len(text)*12+3,ay+3),(255,255,255),-1)
        cv2.putText(im,text,(ax,ay),cv2.FONT_HERSHEY_SIMPLEX,.55,(180,55,0),1,cv2.LINE_AA)
    cv2.imwrite(str(out/(name+'_编号.jpg')),im)
    print(name,'bounds',[int(v) for v in [x0,y0,x1,y1]])
