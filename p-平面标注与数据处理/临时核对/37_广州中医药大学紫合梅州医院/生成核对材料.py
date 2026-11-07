from pathlib import Path
import json, copy, sys, os, math
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon, Point, box, LineString
from shapely.ops import nearest_points
import pymupdf

R=Path(__file__).resolve().parent
P=R.parent.parent/'标注试样'/R.name
sys.path.insert(0,'/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts')
import annotation_tools as ann
from review_workflow import load_state, save_state
D=json.loads((P/'annotation.json').read_text())
state=load_state(R/'review_state.json',D,P/'annotation.json')
save_state(R/'review_state.json',state)
S={s['id']:s for s in D['spaces']}
polys={sid:Polygon([(y,2484-x) for x,y in s['polygon_px']]) for sid,s in S.items()}
source=Image.open(P/D['image']['file']).convert('RGB').rotate(90,expand=True)
FONT='/System/Library/Fonts/Supplemental/Arial Unicode.ttf'
def font(n):return ImageFont.truetype(FONT,n)
openings=[Point(o['position_px'][1],2484-o['position_px'][0])
          for r in D['relations'] for o in r.get('openings',[])]
badges=[]

# Render upright labels, preserving raw JPEG coordinates explicitly on opening circles.
u=copy.deepcopy(D)
u['image'].update(width=3236,height=2484)
for s in u['spaces']:s['polygon_px']=list(polys[s['id']].exterior.coords)[:-1]
for rel in u['relations']:
    if rel['type']=='entrance':
        x,y=rel['position_px'];rel['position_px']=[y,2484-x]
    for o in rel.get('openings',[]):
        x,y=o['position_px'];o['position_px']=[y,2484-x]
ann.render(u,P/'annotation.json',P/'标注.svg')
tree=ET.parse(P/'标注.svg');root=tree.getroot();ns={'s':ann.NS}
im=root.find('.//s:image',ns)
im.set('width','2484');im.set('height','3236');im.set('transform','matrix(0,-1,1,0,0,2484)')
raw={o['id']:o for r in D['relations'] for o in r.get('openings',[])}
for group in root.iter():
    oid=group.get('data-opening-id')
    if oid:
        circle=group.find('s:circle',ns)
        x,y=raw[oid]['position_px'];circle.set('cx',str(x));circle.set('cy',str(y))
        circle.set('transform','matrix(0,-1,1,0,0,2484)')
        label=group.find('s:text',ns);ux,uy=y,2484-x
        label.attrib.pop('stroke',None);label.attrib.pop('stroke-width',None)
        label.attrib.pop('paint-order',None)
        label.set('x',str(ux+6));label.set('y',str(uy-6));label.set('font-size','10')
        group.insert(2,ann.element('rect',dict(x=ux+5,y=uy-17,width=28,height=13,
                      fill='white',**{'fill-opacity':'.92','rx':2})))
root.set('data-coordinate-system','original-jpeg:2484x3236; display:90deg-ccw')
positions={'E06':(710,1510),'E14':(2025,1500),'E13':(2130,1540),
           'E12':(2285,1500),'E05':(2488,1540),'E04':(2694,1500)}
for eid,(cx,cy) in positions.items():
    g=root.find(f'.//s:g[@id="{eid}"]',ns)
    rect=g.find('s:rect',ns);text=g.find('s:text',ns);line=g.find('s:line',ns)
    w,h=float(rect.get('width')),float(rect.get('height'))
    dx,dy=cx-w/2-float(rect.get('x')),cy-h/2-float(rect.get('y'))
    for e in (rect,text):
        e.set('x',str(float(e.get('x'))+dx));e.set('y',str(float(e.get('y'))+dy))
    line.set('x2',str(cx));line.set('y2',str(cy))
texts=root.findall('s:text',ns)
texts[0].text='37 广州中医药大学紫合梅州医院｜首层标注与连通草稿'
texts[1].text='91个空间／功能块；21项名称及2项关键连通待确认。P为门洞；连续分区不虚构门位。'
tree.write(P/'标注.svg',encoding='unicode')
with pymupdf.open(P/'标注.svg') as doc:
    doc[0].get_pixmap(matrix=pymupdf.Matrix(.65,.65),alpha=False).save(R/'SVG全图检查.png')
    for n,b in [('西北',(310,420,1170,960)),('药房',(480,870,1240,1520)),
                ('妇儿',(1570,420,2320,950)),('急诊',(2210,490,3005,1190)),
                ('医技',(1550,870,2240,1520))]:
        head=125
        clip=pymupdf.Rect(b[0],b[1]+head,b[2],b[3]+head)
        doc[0].get_pixmap(matrix=pymupdf.Matrix(1.6,1.6),clip=clip,alpha=False).save(R/f'SVG_{n}检查.png')

def badge(poly,label,scale,avoid):
    x0,y0,x1,y1=poly.bounds
    for fs in (34,28,24,20,16):
        w=(len(label)*fs*.62+14)/scale;h=(fs+10)/scale
        candidates=[]
        for iy in range(11):
            y=y0+(y1-y0-h)*iy/10
            for ix in range(11):
                x=x0+(x1-x0-w)*ix/10
                rect=box(x,y,x+w,y+h)
                if not poly.covers(rect) or any(rect.intersects(q) for q in avoid):continue
                dark=0
                for j in range(5):
                    for i in range(9):
                        px=min(3235,max(0,int(x+w*(i+.5)/9)))
                        py=min(2483,max(0,int(y+h*(j+.5)/5)))
                        dark+=sum(source.getpixel((px,py)))<330
                score=dark/45+.004*iy+.002*ix
                candidates.append((score,x,y,w,h,fs))
        if candidates:
            best=min(candidates)
            if best[0]<.23 or fs==16:return best[1:]
    raise ValueError(('No room for badge',label,poly.bounds))

def mark(draw,poly,label,scale,offset,color,avoid,filename,sid):
    x,y,w,h,fs=badge(poly,label,scale,avoid)
    ox,oy=offset;bb=(ox+x*scale,oy+y*scale,ox+(x+w)*scale,oy+(y+h)*scale)
    draw.rounded_rectangle(bb,radius=5,fill='white',outline=color,width=3)
    draw.text((bb[0]+7,bb[1]+3),label,font=font(fs),fill=color)
    rect=box(x,y,x+w,y+h);avoid.append(rect)
    badges.append(dict(file=filename,space_id=sid,label=label,bbox_upright=[x,y,x+w,y+h],inside=polys[sid].covers(rect)))

def local(filename,bounds,focus,mode='name'):
    scale=3;x0,y0,x1,y1=bounds
    im=source.crop(bounds).resize(((x1-x0)*scale,(y1-y0)*scale),Image.Resampling.LANCZOS)
    dr=ImageDraw.Draw(im);avoid=[p.buffer(13) for p in openings]
    targets={n['space_id']:n['review_id'] for n in state['name_items']}
    for sid in focus:
        poly=polys[sid].intersection(box(*bounds));color='#b45309' if mode=='name' else '#2563eb'
        parts=list(poly.geoms) if hasattr(poly,'geoms') else [poly]
        for part in parts:
            if part.geom_type=='Polygon':
                pts=[((x-x0)*scale,(y-y0)*scale) for x,y in part.exterior.coords]
                dr.line(pts,fill=color,width=5)
        if poly.geom_type=='MultiPolygon':poly=max(poly.geoms,key=lambda p:p.area)
        label=targets[sid] if mode=='name' else sid[1:]
        mark(dr,poly,label,scale,(-x0*scale,-y0*scale),color,avoid,filename,sid)
    im.save(R/filename)

groups=[
 ('01-05','商服与办公片区',(350,430,1165,950),['01','02','03','04','05']),
 ('06-08','妇科与输液配套',(1620,710,2160,960),['06','08']),
 ('07','东北侧矩形留白',(2020,630,2495,925),['07']),
 ('09-12','急诊配套与东侧留白',(2230,925,2910,1240),['09','10','11','12']),
 ('13','药房东侧配套',(1020,1010,1250,1220),['13']),
 ('14','中央南侧休憩区',(1210,1030,1595,1530),['14']),
 ('15-18','专家门诊周边',(490,1170,1170,1475),['15','16','17','18']),
 ('19-21','南侧厚边界单元与配套',(1570,1240,2245,1475),['19','20','21']),
]
N={n['review_id']:n for n in state['name_items']}
for no,title,bounds,ids in groups:
    local(f'名称_{no}.png',bounds,[N[i]['space_id'] for i in ids])
local('K01_连通核对.png',(490,1170,1170,1490),['S066','S067','S053','S087'],'connectivity')
local('K02_连通核对.png',(1570,1240,2245,1500),['S072','S073','S085'],'connectivity')

# Complete-source overview, with the recovered side-label routes.
W,H=9400,5340;OX,OY=1460,190;scale=2
canvas=Image.new('RGB',(W,H),'#f5f7fb');dr=ImageDraw.Draw(canvas)
canvas.paste(source.resize((6472,4968),Image.Resampling.LANCZOS),(OX,OY))
dr.text((35,25),'37｜广州中医药大学紫合梅州医院 · 21项名称核对（沿用原号）',font=font(58),fill='#18314c')
dr.text((35,110),'完整原图正向显示；房内与边栏同号。候选未写入JSON。具体用途可在同一份标注说明中填写。',font=font(34),fill='#475569')
left=[1,2,3,4,5,13,14,15,16,17,18];right=[6,7,8,9,10,11,12,19,20,21]
ys=dict(zip(left,[650,1200,1550,1900,2250,2600,2900,3300,3650,4000,4350]))
ys.update(zip(right,[600,950,1300,1650,2000,2350,2700,3250,3600,3950]))
anchors={1:(604,470),2:(831,470),3:(1049,515),4:(1055,580),5:(420,860),6:(1870,790),
 7:(2290,795),8:(2139,910),9:(2309,990),10:(2850,1110),11:(2600,1140),12:(2420,1170),
 13:(1055,1150),14:(1235,1180),15:(506,1305),16:(598,1310),17:(506,1390),18:(783,1415),
 19:(1841,1330),20:(2004,1390),21:(2187,1450)}
colors={i:('#b45309' if i<6 else '#0369a1' if i<9 else '#a21caf' if i<13 else '#047857' if i<15 else '#6d28d9' if i<19 else '#be123c') for i in range(1,22)}
segments={}
for i in range(1,22):
    item=N[f'{i:02}'];sid=item['space_id'];p=nearest_points(polys[sid].boundary,Point(anchors[i]))[0]
    start=(1425 if i in left else 7975,ys[i]);end=(OX+p.x*scale,OY+p.y*scale)
    segments[i]=LineString([start,end]);dr.line([start,end],fill='white',width=10);dr.line([start,end],fill=colors[i],width=4)
for i in range(1,22):
    item=N[f'{i:02}'];sid=item['space_id'];color=colors[i]
    pts=[(OX+x*scale,OY+y*scale) for x,y in polys[sid].exterior.coords];dr.line(pts,fill=color,width=6)
    mark(dr,polys[sid],f'{i:02}',scale,(OX,OY),color,[p.buffer(13) for p in openings],'37_高清核对总图.png',sid)
    x=30 if i in left else 7995;y=ys[i];w=1375;h=284
    dr.rounded_rectangle((x,y-h/2,x+w,y+h/2),radius=16,fill='white',outline=color,width=4)
    dr.text((x+22,y-h/2+16),f'{i:02}｜{sid} 名称未确认',font=font(43),fill=color)
    def wrap(text,fs,maxwidth):
        lines=['']
        for c in text:
            if dr.textlength(lines[-1]+c,font=font(fs))>maxwidth:lines.append('')
            lines[-1]+=c
        return lines
    yy=y-h/2+78
    for line in wrap('候选：'+' / '.join(item['candidates']),35,w-45)[:2]:
        dr.text((x+22,yy),line,font=font(35),fill='#18314c');yy+=43
    for line in wrap('依据：'+item['evidence'],29,w-45)[:2]:
        dr.text((x+22,yy),line,font=font(29),fill='#475569');yy+=36
    dr.text((x+22,y+h/2-39),'把握：'+item['confidence']+'；保留原核对号',font=font(28),fill=color)
cross=[(i,j) for i,a in segments.items() for j,b in segments.items() if i<j and a.intersects(b)]
canvas.save(R/'37_高清核对总图.png')
canvas.resize((1880,1068),Image.Resampling.LANCZOS).save(R/'37_核对总图预览.png')
(R/'核对图审计.json').write_text(json.dumps(dict(badges=badges,leader_crossings=cross),ensure_ascii=False,indent=2)+'\n')

# One editable document; prefilled candidates never count as user confirmation.
rel=os.path.relpath(R,P)
md=['# 37号｜广州中医药大学紫合梅州医院','',
 '<!-- annotation:summary:start -->','草稿；待更新概览。','<!-- annotation:summary:end -->','',
 '沿用原S编号及名称核对号；以科室功能块为粒度。名称未确认的21项在JSON中保持 `unknown`。',
 '请直接修改“预估名称（可改）”，将确认栏改为“已确认”；也可在确认栏写实际名称。聊天可按 `01=名称` 回复。',
 '07、11、14只需确认空间用途；确定为庭院／挑空时统一不计面积，无须说明顶盖。','',
 f'[完整高清核对总图]({rel}/37_高清核对总图.png)','',
 f'![名称核对总图]({rel}/37_核对总图预览.png)','', '## 名称与用途核对','']
for no,title,bounds,ids in groups:
    md += [f'### {no}｜{title}','',f'![{no}名称核对局部]({rel}/名称_{no}.png)','',
      '| 核对号 | S编号 | 预估名称（可改） | 备选名称 | 依据与把握 | 我的确认／备注 | 核对号（重复） |',
      '| --- | --- | --- | --- | --- | --- | --- |']
    for rid in ids:
        item=N[rid];c=item['candidates']
        ev=item['evidence']+' 候选共用上述依据，尚不能区分。把握：'+item['confidence']+'。'
        md.append(f'| {rid} | {item["space_id"]} | {c[0]} | '+(' / '.join(c[1:]) or '暂无')+f' | {ev} | 待确认 | {rid} |')
    md.append('')
md += ['## 关键连通核对','']
for item in state['connectivity_items']:
    rid=item['review_id'];md += [f'### {rid}','',f'![{rid}连通局部]({rel}/{rid}_连通核对.png)','',
      '**问题：**'+item['question'],'','**我的判断：**'+item['reason'],'',
      '**我的确认／备注：**待填写（可写同意、实际相连空间，或仍待确认）','']
md+=['已可判断的主要关系及门洞已同步；功能块内部小间、电梯轿厢门和柜台小门本轮不逐项细究。','']
(P/'标注说明.md').write_text('\n'.join(md))
print('overview crossings',cross,'badges',len(badges),'all inside',all(b['inside'] for b in badges))
