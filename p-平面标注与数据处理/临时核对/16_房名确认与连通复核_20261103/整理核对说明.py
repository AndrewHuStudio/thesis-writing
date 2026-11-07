"""Keep all current user answers and place only critical connectivity questions first."""
from pathlib import Path
from collections import Counter
import json,sys,os,re
from PIL import ImageDraw,ImageFont
from shapely.geometry import Polygon
OUT=Path(__file__).resolve().parent
BASE=OUT.parents[1]
PROJECT=BASE/'标注试样/16_浙江大学医学院邵逸夫医院下沙院区'
sys.path.insert(0,str(OUT))
from 看图工具 import get_background,number_box,FONT
sys.path.insert(0,str(BASE/'临时核对/09-10_连通复核_20261102'))
from 连通工具 import annotation
A=json.loads((OUT/'待核验成果/annotation.json').read_text());SS={s['id']:s for s in A['spaces']}
BACKUP=Path((OUT/'本轮备份路径.txt').read_text());old=(BACKUP/'标注说明.md').read_text()
def link(p):return os.path.relpath(p,PROJECT)
def question(sid,num,bounds,name):
 scale=4.0;im,photo=get_background(bounds,scale,True);draw=ImageDraw.Draw(im)
 poly=Polygon(SS[sid]['polygon_px'])
 pts=[((x-bounds[0])*scale,(y-bounds[1])*scale) for x,y in poly.exterior.coords]
 draw.line(pts,fill='#d23214',width=5)
 x,y,w,h,font,bb=number_box(poly,num,bounds,scale,im,38)
 x,y=(x-bounds[0])*scale,(y-bounds[1])*scale
 draw.rounded_rectangle((x,y,x+w,y+h),radius=5,fill='white',outline='#d23214',width=3)
 draw.text((x+6,y+3-bb[1]),num,font=font,fill='#c52915')
 filename=OUT/(name+'.jpg');im.save(filename,quality=96)
 return f'![{name}：核对数字直接位于空间内]({link(filename)})'
q1=question('S185','01',(1825,1025,2175,1245),'K01_采光通道范围')
q2a=question('S172','02',(1320,1400,1560,1570),'K02a_急诊西南交通核')
q2b=question('S206','02',(2250,1320,2510,1500),'K02b_急诊东南交通核')
annotation.summary(A,OUT/'连通同步概览.md')
base=(OUT/'连通同步概览.md').read_text()
# Replace generated completion wording: structural passing is not semantic completion.
lines=base.splitlines()
print('\n'.join(lines[:20]))
head=['# 16号｜浙江大学医学院邵逸夫医院下沙院区 · 一层标注', '',
'**当前状态：房名已同步；连通性首轮复核已开展，尚有 K01、K02 两组关键项待确认。**', '',
'2026-11-03：已读取你最新填写的141行核对记录，落实68项明确房名／用途填写（包括对照片初读的修正），其余已辨认房名沿用。当前名称未确认项为0。141行原填写、原核对号及S编号映射保留在文末。', '',
'按你的备注将25／S038并入24／S037“贵重药品”，80／S125并入79／S124“挂号收费”；排除120／S181室外空间和121／S182采光井。保留合并后的S037、S124，不重排其他S编号。', '',
'室内通路核查补出服务岛东侧漏记的连续通道S211，并校正药房纵向工作人员通道S030、相邻小间边界及手术专用电梯前室S184的南侧范围。因此当前207个标注单元＝原210个－2个合并单元－2个排除单元＋1段补记通道；并非207间房。', '',
'**结构与名称校验：**207个空间、未确认房名0；室内相对面积已重新归一化。K01涉及的S185仍暂留原草稿面积口径，确认后再处理，不将当前面积分母视为最终值。', '',
'**关系首轮结果：**230条人员可达、9条服务联系、16个独立入口；193个可定位室内开口已保存原图近似坐标并同步为SVG红点。另有无定位的概念连接；红点数量不等于关系数。', '',
'**已纠正的主要路径：**VIP大厅S072经交通核S058进入S061，不再跨交通核直连；EICU S196经北侧医护通道S174和抢救区S195出入，未见东侧实墙门，不保留S196—S197旧直连。S206与S197的旧连接暂不采用，列入K02。柜台服务窗口未当作患者穿行通道。', '',
'## 连通性关键核对', '',
'本轮不要求逐间追问管井、设备小间或交通核内部路线。下面只保留会影响标注范围或主要交通核可达性的两组问题。图中01、02为本节核对号；与文末旧房名核对号分开使用。', '',
'### K01｜S185是否也属于室外采光通道', '',q1,'',
'**问题：**你已将邻接的120／S181标为室外、121／S182标为采光井。图中01对应的S185小段，是否同样属于室外采光通道，应一并排除？', '',
'**我的判断：**倾向同属室外采光通道。它位于已排除空间南侧，向右侧室外空地延续，不能先当作室内捷径连接交通核S180与医护通道S174。本轮没有为S185新增通行边；原草稿的名称和面积口径仅暂存，等范围确认后调整。', '',
'| 核对号 | 我的确认／备注 |', '| --- | --- |', '| K01 | 待确认（可填：室外，一并排除／室内通道，保留） |', '',
'### K02｜两个急诊交通核的室内接口', '',q2a,'',q2b,'',
'**问题：**西南交通核S172是否直接连急诊大厅S159？东南交通核S206是否直接连EICU东侧通道S197？若连其他空间，请写实际空间。两图中的02分别位于这两个交通核内。', '',
'**我的判断：**南侧对外开口清楚，已分别记录为独立外部接口；室内侧入口在缩印图中不能可靠定位。本轮不以共墙替代通行依据，尚未加入S172—S159和S206—S197。确认概念可达即可，无须提供精确门位。', '',
'| 核对号 | 我的确认／备注 |', '| --- | --- |', '| K02 | 待确认（可填：S172连S159、S206连S197；或逐个修正） |', '',
'## 连通判读范围与精度', '',
'复核范围为完整一层主体：感染门诊、药房与公共服务岛、门诊大厅及办公、儿科、急诊观察与诊室、急诊医护、抢救／EICU及住院支持。原图下缘被截断的其他楼层不纳入。', '',
'连续大厅或候诊区的人工分片、开放服务工作节点及成组交通核接口保存为概念可达，不自动生成门位。需要依据通行组织推断而不能可靠定位的边，依据保存在外部判读记录中；均不是用户逐项确认。共墙、服务窗口及未记录关系均不作为不通行的负例。', '',
'本轮不细究的内部细节：卫生间内隔间、交通核内部楼梯／电梯精确走线、设备与控制小间的内部门扇、半墙工作区的小门形状。证据不足的细节留空，不要求你逐项补门。', '',
'[查看更新后的标注SVG](标注.svg)｜[查看JSON](annotation.json)｜[本轮持久核对材料]('+link(OUT)+')', '',
'## 房名确认记录（保留原填写）', '',
'以下141行及其房内数字图保留你的原始填写。预估列和证据列是历史判读，最终名称以确认栏及当前JSON／SVG为准；合并与排除项不再作为独立空间。未改写自动照片识别状态，避免将助手识别伪称为你逐项确认。', '',
'合并映射：25／S038→24／S037；80／S125→79／S124。已排除：120／S181、121／S182。原图未改动。', '']
start=old.index('### 01—06')
text='\n'.join(head)+'\n'+old[start:]
# Preserve actual table row bytes, even when user has aligned table columns.
def rows(t):
 return [l for l in t.splitlines() if re.match(r'^\|\s*\d+\s*\|\s*S\d+\s*\|',l)]
assert rows(old)==rows(text) and len(rows(text))==141
for ref in re.findall(r'!\[[^\]]*\]\(([^)]+)\)',text):assert (PROJECT/ref).resolve().is_file(),ref
(OUT/'待核验成果/标注说明.md').write_text(text)
print('preserved 141 rows; new questions K01 K02')
