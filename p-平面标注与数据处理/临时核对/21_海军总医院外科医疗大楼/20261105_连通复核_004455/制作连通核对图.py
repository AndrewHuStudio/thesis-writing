"""Create plan-specific opening overlays and numbered questions, without editing answers."""
import ast
import json
import math
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from shapely.geometry import Polygon,box

WORK=Path(__file__).resolve().parent
data=json.loads((WORK/'连通复核候选.json').read_text())
raw=Image.open(WORK/'阅读原图.jpg').convert('RGB')
FONT='/System/Library/Fonts/STHeiti Medium.ttc'
font=lambda n:ImageFont.truetype(FONT,n)
spaces={s['id']:s for s in data['spaces']}
colors=['#2563eb','#0f766e','#a21caf','#c2410c','#be123c','#0369a1']
helper=WORK.parents[1]/'21-25_名称核对_20261105'/'补充房内数字.py'
tree=ast.parse(helper.read_text())
tree.body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='choose_badge']
exec(compile(tree,str(helper),'exec'))


def label_image(rect,ids,badges):
    crop=raw.crop(rect)
    image=crop.resize((crop.width*3,crop.height*3))
    draw=ImageDraw.Draw(image)
    def local(points):
        return [((y-rect[0])*3,(2443-x-rect[1])*3) for x,y in points]
    for i,sid in enumerate(ids):
        pts=local(spaces[sid]['polygon_px'])
        color=colors[i%len(colors)]
        draw.line(pts+[pts[0]],fill=color,width=5)
        poly=Polygon(pts).intersection(box(0,0,image.width,image.height))
        if poly.geom_type != 'Polygon' or poly.area < 1200:
            continue
        text=badges.get(sid,sid)
        try:
            location,f,ink=choose_badge(image,poly,text)
        except ValueError:
            continue
        draw.rounded_rectangle(location,radius=7,fill='white',outline=color,width=3)
        draw.text(((location[0]+location[2])/2,(location[1]+location[3])/2),text,
                  font=f,anchor='mm',fill=color)
    return image


questions=[
    dict(key='K01',title='急诊手术与准备区的主要入口',rect=[220,530,510,995],
         ids=['S010','S009','S008','S012','S011','S025'],
         badges={'S011':'01 S011','S012':'01 S012'},
         question='S011手术、S012手术准备间，实际从哪个空间进入，先后经过哪些空间？',
         judgment='右侧是急诊西侧通道S025，但手术及准备间朝该侧的门不清楚；也不能仅因邻接器械、抢救空间就认定内部相通。暂未补这两间的access。',
         answer='待填写（写直接通行顺序即可，例如S025→S012→S011；若实际从别处进入请写实际空间）'),
    dict(key='K02',title='首长电梯及前室的对外连接',rect=[2410,835,2890,1085],
         ids=['S113','S115','S116','S117','S112'],badges={'S115':'02 S115'},
         question='S115首长电梯以及前室，直接从哪个空间进入：首长门厅S116、公共楼梯核S113，还是其他空间？',
         judgment='已移除原稿跨过S115的“S116直接到S113”。S115右侧边界的通行口不够清楚，暂不把隔墙或同色区域直接当作相通。',
         answer='待填写（写与S115直接相通的空间即可，无须定位门）'),
    dict(key='K03-A',title='护发室S123的直接入口',rect=[2030,650,2375,855],
         ids=['S117','S124','S123','S129','S128'],badges={'S123':'03A S123','S128':'03B S128'},
         question='S123护发室是直接开向主通道S117，还是先经过育发S124进入？',
         judgment='北侧育发S124朝主通道的门可辨；下侧护发S123与通道、育发之间的门线仍不清，原直接连接暂移出。',
         answer='待填写（写S123直接相连的空间；可直接写S117、S124或实际情况）'),
    dict(key='K03-B',title='纹眉室S128的直接入口',rect=[2030,650,2375,855],
         ids=['S117','S124','S123','S129','S128'],badges={'S123':'03A S123','S128':'03B S128'},
         question='S128纹眉室是直接开向主通道S117，还是先经过激光S129进入？',
         judgment='北侧激光S129朝主通道的门可辨；下侧纹眉S128的门线仍不清，不能仅由共墙确定上下相通。',
         answer='待填写（写S128直接相连的空间；可直接写S117、S129或实际情况）'),
    dict(key='K04-A',title='整形主通道与东侧处置通道',rect=[2460,610,2890,870],
         ids=['S117','S149','S151','S144','S148','S147','S146'],badges={'S151':'04A S151','S147':'04B S147'},
         question='整形主通道S117与东侧处置通道S151是否直接相通？若不直接相通，S151的入口在哪个空间？',
         judgment='两段通道在东南角衔接，但双扇门线与卫生间入口混在一起，不能确定门归属；原S117—S151直接关系暂移出。整形厅S149东侧的连续墙线不作为捷径。',
         answer='待填写（可填“相通”；否则写S151实际直接连接的入口空间）'),
    dict(key='K04-B',title='处理室S147的直接入口',rect=[2460,610,2890,870],
         ids=['S117','S149','S151','S144','S148','S147','S146'],badges={'S151':'04A S151','S147':'04B S147'},
         question='处理室S147是否直接开向通道S151，还是经准备S146或其他房间进入？',
         judgment='换药S148及准备S146朝东侧通道的门可辨；处理室S147西侧入口未能辨清，暂不据功能关系补连。',
         answer='待填写（写S147实际直接相连的空间即可）'),
]
for q in questions:
    filename=q['key']+'_连通核对.png'
    label_image(q['rect'],q['ids'],q['badges']).save(WORK/filename)
    raw.crop(q['rect']).resize(((q['rect'][2]-q['rect'][0])*3,(q['rect'][3]-q['rect'][1])*3)).save(WORK/(q['key']+'_无标记原图.png'))
    q['image']=filename
(WORK/'关键连通疑点.json').write_text(json.dumps(questions,ensure_ascii=False,indent=2))

# Every plotted red point comes from the manually reviewed openings list.
overlay=raw.copy()
draw=ImageDraw.Draw(overlay)
for row in data['relations']:
    for point in row.get('openings',[]):
        x,y=point['position_px'];u,v=y,2443-x
        draw.ellipse((u-4,v-4,u+4,v+4),fill='#dc2626',outline='white',width=1)
        draw.text((u+5,v-12),point['id'],font=font(11),fill='#b91c1c',stroke_width=1,stroke_fill='white')
overlay.save(WORK/'门洞原图定位总图.png')
inventory=json.loads((WORK/'工作目录.json').read_text())
for name,rect in inventory['crops']:
    region=overlay.crop(rect)
    region.resize((region.width*2,region.height*2)).save(WORK/(name+'_门洞定位.png'))
print('6 independently fillable questions; room labels placed inside outlines; opening overview rendered')
