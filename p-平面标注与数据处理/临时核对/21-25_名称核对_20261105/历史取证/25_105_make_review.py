from pathlib import Path
import json,importlib.util,copy,base64,xml.etree.ElementTree as ET
from PIL import Image,ImageDraw,ImageFont
from shapely.geometry import Polygon,LineString
T=Path('/tmp/outpatient25-review')
B=Path('/Users/hushili/Documents/研究-论文写作/大论文/p-写作过程/标注试样/25_上海市第十人民医院内科病房综合楼')
SK=Path('/Users/hushili/.codex/skills/outpatient-plan-annotation')
spec=importlib.util.spec_from_file_location('ann',SK/'scripts/annotation_tools.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
data=json.loads((B/'annotation.json').read_text());qs=json.loads((T/'review-map.json').read_text())
# Use the Skill's renderer with upright display coordinates. The embedded source is the original JPEG,
# transformed only at SVG display time. JSON always keeps untouched original-image coordinates.
u=copy.deepcopy(data);u['image'].update(width=3232,height=2472)
for s in u['spaces']:s['polygon_px']=[[y,2472-x] for x,y in s['polygon_px']]
for r in u['relations']:
 if r['type']=='entrance':x,y=r['position_px'];r['position_px']=[y,2472-x]
a.render(u,B/'annotation.json',B/'标注.svg')
root=ET.parse(B/'标注.svg');ns={'s':a.NS}
im=root.find('.//s:image',ns);im.set('width','2472');im.set('height','3232');im.set('transform','matrix(0 -1 1 0 0 2472)')
texts=root.findall('s:text',ns)
texts[0].text='25 上海市第十人民医院内科病房综合楼｜一层标注草稿'
texts[0].set('font-size','28')
texts[1].text='97个空间／区域，18项名称待确认；住院支持、干部特诊、医技检查及会议教学功能分范围记录'
for e in root.findall('.//s:text',ns):e.set('font-family','Hiragino Sans GB, PingFang SC, Microsoft YaHei, sans-serif')
root.write(B/'标注.svg',encoding='unicode')
# Readable short overview; candidates and review numbering stay only in temporary review materials.
a.summary(data,B/'标注说明.md')
p=B/'标注说明.md';md=p.read_text().replace('# 平面标注概览','# 25 上海市第十人民医院内科病房综合楼｜一层标注草稿')
md=md.replace('未完成：18 个空间名称尚未确认。','**状态：标注草稿，尚未完成。18个空间名称／用途待确认。**\n\n**图面范围：**仅当前原图所示一层，包含西侧干部特诊（诊室、化注候选区、药库及候诊）、X光／心电图／脑电图／B超／胃镜等医技检查、中央住院大厅与出入院办理、东侧会议教学中心及办公、接待、制作支持、南侧多功能教室及休息厅。本层未见病房单元，不把建筑名称中的“病房综合楼”当作本图存在病床的证据。\n\n**范围编码：**`special_outpatient` 干部特诊；`medical_technical` 医技检查；`inpatient_support` 住院支持；`conference_support` 会议教学支持；`public_service` 公共服务；`public_circulation` 公共交通；`building_support` 建筑设备支持。范围是概念级片区归属，东侧“医办”等名称按原字保留。')
md+='\n**图像与几何：**原图2472×3232像素，文件未改动；JSON使用原图坐标。SVG仅在显示时整体转正，编号按转正后的相邻片区先上后下、同排先左后右组织。矩形及折线边界为概念范围，按墙线和开口近似描绘；细小墙厚、柱及家具不单独建节点。相对面积仅表示所标室内区域的几何占比，不是实测建筑面积。外侧室外台阶、坡道及外置疏散梯未纳入室内面积。交通核整体记录，不展开内部精确路线。\n\n**关系边界：**只记录可辨门口／开放连接／连续区域的概念可达；服务台另记服务联系。共墙单独记录，未记关系不表示不连通。外部入口彼此独立，不通过室外总节点串联。入口用概念用途或方位命名；东侧入口标示原字未读清，未据此扩张本图功能。关系不表达患者或医护的门禁权限。\n\n**核验边界：**目前仅进行允许未确认名称的草稿结构检查及图面复查；18项未确认均为 `unknown`，不作为训练真值。全部名称确认后仍需重新执行normalize、render、summary和正式validate，并查看全图与密集局部，才可宣布本张完成。\n'
p.write_text(md)
font_path='/System/Library/Fonts/Hiragino Sans GB.ttc'
def font(n):return ImageFont.truetype(font_path,n)
def wrap(text,fn,width):
 rows=['']
 for ch in text:
  if ImageDraw.Draw(Image.new('RGB',(1,1))).textlength(rows[-1]+ch,font=fn)>width:rows.append('')
  rows[-1]+=ch
 return rows
source=Image.open(T/'upright.png').convert('RGB')
scale=1.2;sc=3232/2300*scale;ox=720;oy=180
W=5318;H=3266
out=Image.new('RGB',(W,H),'#f6f8fc');out.paste(source.resize((round(3232*scale),round(2472*scale))), (ox,oy))
d=ImageDraw.Draw(out,'RGBA')
d.text((35,25),'25｜一层平面名称集中核对（标注草稿）',font=font(44),fill='#17324d')
d.text((35,92),'18项待确认｜按片区从上到下、同排从左到右；回复“01=名称，02=名称”，可分批。候选尚未写为确定名称。',font=font(27),fill='#42556a')
d.text((35,H-65),'完整原图仅在临时核对图中转正；原文件未改动。编号对应关系本轮固定。框与引线仅用于定位，不表示通行关系。',font=font(25),fill='#42556a')
colors=['#8b3ca8']*6+['#1976ab']+['#cc4b32']*10+['#16866a']
anchors=[(425,482),(506,506),(425,543),(425,589),(448,613),(867,690),(1318,800),(1501,400),(1625,480),(1685,495),(1809,510),(1785,535),(1809,550),(1564,567),(1685,580),(1809,595),(1992,610),(1948,1030)]
paths=[]
for i,(q,color,anc) in enumerate(zip(qs,colors,anchors)):
 pts=[(ox+x*sc,oy+y*sc) for x,y in q['polygon']]
 d.polygon(pts,fill=color+'12',outline=color,width=4)
 x0=min(x for x,y in pts);y0=min(y for x,y in pts)
 d.rounded_rectangle((x0+3,y0+3,x0+47,y0+39),radius=5,fill=color)
 d.text((x0+6,y0+4),q['review_no'],font=font(25),fill='white')
 ax,ay=ox+anc[0]*sc,oy+anc[1]*sc
 if i<7:
  lx=18;ly=580+i*270;rx=675;cy=ly+34
  channel=ox+225*sc;path=[(rx,cy),(channel,ay),(ax,ay)]
 else:
  lx=4640;ly=410+(i-7)*240;rx=5300;cy=ly+34
  channel=ox+2007*sc;path=[(ax,ay),(channel,ay),(lx,cy)]
 paths.append(LineString(path))
 d.line(path,fill=color,width=3)
 d.ellipse((ax-6,ay-6,ax+6,ay+6),fill='white',outline=color,width=3)
 d.rounded_rectangle((lx,ly,rx,ly+215),radius=13,fill='white',outline=color,width=3)
 d.text((lx+16,ly+12),q['review_no']+'｜'+q['id']+' 名称未确认',font=font(28),fill=color)
 rows=wrap('候选：'+' / '.join(q['candidates']),font(24),rx-lx-32)
 yy=ly+56
 for row in rows:
  d.text((lx+16,yy),row,font=font(24),fill='#182b3d');yy+=30
 ev=q['evidence']
 for row in wrap('依据：'+ev,font(21),rx-lx-32)[:3]:
  d.text((lx+16,yy),row,font=font(21),fill='#526170');yy+=27
 d.text((lx+16,ly+183),'把握：'+q['confidence']+'（待你确认）',font=font(21),fill=color)
# No leader crossings, and exactly one frame and label per pending ID.
cross=[]
for i,p1 in enumerate(paths):
 for j,p2 in enumerate(paths[i+1:],i+1):
  if p1.intersects(p2):cross.append((i+1,j+1))
assert not cross,cross
assert {q['id'] for q in qs}=={s['id'] for s in data['spaces'] if s['type']=='unknown'}
out.save(T/'25_名称核对总图.png')
preview=out.copy();preview.thumbnail((2660,1700));preview.save(T/'25_核对总图_预览.png')
# Supplemental enlargements retain the exact same review numbers and source context.
for name,b in [('西侧特诊密集区',(240,340,940,758)),('东侧支持密集区',(1430,337,2000,635))]:
 x1,y1,x2,y2=b; z=3.7
 crop=source.crop(tuple(round(v*3232/2300) for v in b)).resize((round((x2-x1)*z),round((y2-y1)*z)))
 cd=ImageDraw.Draw(crop,'RGBA')
 for q,color in zip(qs,colors):
  pp=Polygon(q['polygon']);region=Polygon([(x1,y1),(x2,y1),(x2,y2),(x1,y2)])
  if not pp.intersects(region):continue
  pts=[((x-x1)*z,(y-y1)*z) for x,y in q['polygon']]
  cd.polygon(pts,fill=color+'10',outline=color,width=5)
  xx=min(x for x,y in pts)+4;yy=min(y for x,y in pts)+4
  cd.rectangle((xx,yy,xx+65,yy+45),fill=color)
  cd.text((xx+5,yy+1),q['review_no'],font=font(34),fill='white')
 crop.save(T/(name+'.png'))
lines=['# 25号核对号与稳定S编号','', '本轮18项；候选未写成核心JSON确定名称，可分批确认。','', '|核对号|S编号|候选|图面依据|把握|','|---|---|---|---|---|']
for q in qs:lines.append('|'+ '|'.join([q['review_no'],q['id'],' / '.join(q['candidates']),q['evidence'],q['confidence']])+'|')
(T/'核对清单.md').write_text('\n'.join(lines)+'\n')
(T/'visual_checks.json').write_text(json.dumps(dict(pending=len(qs),frames=len(qs),labels=len(qs),leader_crossings=cross,review_resolution=out.size),ensure_ascii=False,indent=2))
print(json.dumps(dict(review=str(T/'25_名称核对总图.png'),size=out.size,pending=len(qs),leader_crossings=cross),ensure_ascii=False))