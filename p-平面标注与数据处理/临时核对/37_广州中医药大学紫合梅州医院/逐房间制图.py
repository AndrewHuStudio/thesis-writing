from pathlib import Path
from collections import Counter
import json,copy,sys,os,math
import xml.etree.ElementTree as ET
from PIL import Image,ImageDraw,ImageFont
from shapely.geometry import Polygon,Point,box
import pymupdf

R=Path(__file__).resolve().parent;P=R.parent.parent/'标注试样'/R.name
D=json.loads((P/'annotation.json').read_text());state=json.loads((R/'review_state.json').read_text())
S={s['id']:s for s in D['spaces']};polys={sid:Polygon([(y,2484-x) for x,y in s['polygon_px']]) for sid,s in S.items()}
source=Image.open(P/D['image']['file']).convert('RGB').rotate(90,expand=True)
FONT='/System/Library/Fonts/Supplemental/Arial Unicode.ttf'
def font(n):return ImageFont.truetype(FONT,n)
sys.path.insert(0,'/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts')
import annotation_tools as ann
u=copy.deepcopy(D);u['image'].update(width=3236,height=2484)
for s in u['spaces']:s['polygon_px']=[list(p) for p in list(polys[s['id']].exterior.coords)[:-1]]
for rel in u['relations']:
    if rel['type']=='entrance':x,y=rel['position_px'];rel['position_px']=[y,2484-x]
    for o in rel.get('openings',[]):x,y=o['position_px'];o['position_px']=[y,2484-x]
ann.render(u,P/'annotation.json',P/'标注.svg')
tree=ET.parse(P/'标注.svg');root=tree.getroot();ns={'s':ann.NS}
im=root.find('.//s:image',ns);im.set('width','2484');im.set('height','3236');im.set('transform','matrix(0,-1,1,0,0,2484)')
raw={o['id']:o for r in D['relations'] for o in r.get('openings',[])}
for group in root.iter():
    oid=group.get('data-opening-id')
    if not oid:continue
    circle=group.find('s:circle',ns);x,y=raw[oid]['position_px']
    circle.set('cx',str(x));circle.set('cy',str(y));circle.set('transform','matrix(0,-1,1,0,0,2484)')
    label=group.find('s:text',ns);ux,uy=y,2484-x
    for key in ('stroke','stroke-width','paint-order'):label.attrib.pop(key,None)
    label.set('x',str(ux+5));label.set('y',str(uy-5));label.set('font-size','8')
    group.insert(2,ann.element('rect',dict(x=ux+4,y=uy-14,width=23,height=11,fill='white',rx=1,
                                         **{'fill-opacity':'.93'})))
positions={'E06':(710,1510),'E14':(2025,1500),'E13':(2130,1540),
           'E12':(2285,1500),'E05':(2488,1540),'E04':(2694,1500)}
for eid,(cx,cy) in positions.items():
    g=root.find(f'.//s:g[@id="{eid}"]',ns);rect=g.find('s:rect',ns);text=g.find('s:text',ns);line=g.find('s:line',ns)
    w,h=float(rect.get('width')),float(rect.get('height'));dx,dy=cx-w/2-float(rect.get('x')),cy-h/2-float(rect.get('y'))
    for e in (rect,text):e.set('x',str(float(e.get('x'))+dx));e.set('y',str(float(e.get('y'))+dy))
    line.set('x2',str(cx));line.set('y2',str(cy))
root.set('data-coordinate-system','original-jpeg:2484x3236; display:90deg-ccw')
texts=root.findall('s:text',ns);unknown=sum(s['type']=='unknown' for s in S.values());room_count=sum(s['level']=='room' for s in S.values())
texts[0].text='37 广州中医药大学紫合梅州医院｜逐房间轮廓标注草稿'
texts[1].text=f'{len(S)}个单元，其中{room_count}个房间级单元；{unknown}个无名单元保持unknown。房间与通道分别编号。'
from 图内标签修正 import fix_labels
label_audit=fix_labels(tree,D)
(R/'逐房间SVG标签审计.json').write_text(json.dumps(label_audit,ensure_ascii=False,indent=2)+'\n')
tree.write(P/'标注.svg',encoding='unicode')
if '--svg-only' in sys.argv:
    with pymupdf.open(P/'标注.svg') as doc:
        doc[0].get_pixmap(matrix=pymupdf.Matrix(.65,.65),alpha=False).save(R/'本轮连通_SVG全图.png')
        for name,b in [('妇儿',(1570,430,2320,960)),('药房办公',(480,430,1240,1520)),
                       ('医技',(1540,850,2245,1520)),('急诊东侧',(2200,490,3010,1500))]:
            doc[0].get_pixmap(matrix=pymupdf.Matrix(1.5,1.5),
                clip=pymupdf.Rect(b[0],b[1]+125,b[2],b[3]+125),alpha=False).save(R/f'本轮连通_SVG_{name}.png')
    print('SVG refreshed; editable MD unchanged')
    sys.exit(0)

regions=[
 ('01','西北商服与办公',(350,430,1165,950)),
 ('02','儿科及妇科北排',(1570,430,2320,665)),
 ('03','妇科南排及输液',(1570,640,2320,960)),
 ('04','药房及两侧配套',(480,870,1240,1210)),
 ('05','专家门诊逐房间',(490,1180,1240,1520)),
 ('06','放射科北部房间',(1550,850,2240,1178)),
 ('07','放射科南部房间',(1550,1150,2245,1520)),
 ('08','急诊北侧斜排及中部房间',(2200,490,3010,850)),
 ('09','留观及急救周边',(2200,810,3010,1195)),
 ('10','VIP及肠道门诊',(2210,1070,2870,1360)),
 ('11','VIP南排及发热门诊',(2210,1300,2800,1500)),
 ('12','中央门厅与留白区',(1200,400,1600,1530)),
]

badge_audit=[]
opening_points=[Point(o['position_px'][1],2484-o['position_px'][0]) for rel in D['relations'] for o in rel.get('openings',[])]
def choose_badge(poly,label,scale):
    x0,y0,x1,y1=poly.bounds
    for vertical in (False,True):
        for fs in (28,24,20,16):
            lines=list(label) if vertical else [label]
            w=(max(map(len,lines))*fs*.65+8)/scale;h=(len(lines)*(fs+3)+6)/scale
            options=[]
            for iy in range(7):
                y=y0+(y1-y0-h)*iy/6
                for ix in range(7):
                    x=x0+(x1-x0-w)*ix/6;rect=box(x,y,x+w,y+h)
                    if not poly.covers(rect):continue
                    if any(rect.intersects(p.buffer(7)) for p in opening_points):continue
                    dark=sum(sum(source.getpixel((min(3235,max(0,int(x+w*(i+.5)/7))),
                          min(2483,max(0,int(y+h*(j+.5)/5))))))<330 for j in range(5) for i in range(7))
                    options.append((dark/35+.006*iy+.003*ix,x,y,w,h,fs,lines))
            if options:return min(options)[1:]
    return None

def draw_numbered(bounds,filename,scale=3,targets=None,doors=False):
    x0,y0,x1,y1=bounds;im=source.crop(bounds).resize(((x1-x0)*scale,(y1-y0)*scale),Image.Resampling.LANCZOS)
    dr=ImageDraw.Draw(im);crop=box(*bounds)
    for sid,poly in polys.items():
        if targets and sid not in targets:continue
        clipped=poly.intersection(crop)
        if clipped.is_empty:continue
        parts=list(clipped.geoms) if hasattr(clipped,'geoms') else [clipped]
        color='#b45309' if S[sid]['type']=='unknown' else '#0f766e' if S[sid]['type']=='corridor' else '#2563eb'
        for part in parts:
            if part.geom_type=='Polygon':dr.line([((x-x0)*scale,(y-y0)*scale) for x,y in part.exterior.coords],fill=color,width=3)
        pieces=[p for p in parts if p.geom_type=='Polygon']
        if not pieces:continue
        part=max(pieces,key=lambda p:p.area)
        if part.area<160:continue
        result=choose_badge(part,sid[1:],scale)
        if not result:
            badge_audit.append(dict(file=filename,space_id=sid,drawn=False,level=S[sid]['level']));continue
        x,y,w,h,fs,lines=result;xx,yy=(x-x0)*scale,(y-y0)*scale
        dr.rectangle((xx,yy,xx+w*scale,yy+h*scale),fill='white',outline=color,width=2)
        for i,line in enumerate(lines):dr.text((xx+4,yy+3+i*(fs+3)),line,font=font(fs),fill=color)
        badge_audit.append(dict(file=filename,space_id=sid,drawn=True,inside=poly.covers(box(x,y,x+w,y+h)),level=S[sid]['level']))
    if doors:
        for rel in D['relations']:
            for o in rel.get('openings',[]):
                x,y=o['position_px'][1],2484-o['position_px'][0]
                if not (x0<=x<=x1 and y0<=y<=y1):continue
                x,y=(x-x0)*scale,(y-y0)*scale
                dr.ellipse((x-5,y-5,x+5,y+5),fill='#dc2626',outline='white',width=2)
    im.save(R/filename)
    return im

overview=draw_numbered((0,0,3236,2484),'37_逐房间完整核对总图.png',2)
overview.resize((1618,1242),Image.Resampling.LANCZOS).save(R/'37_逐房间总图预览.png')
for no,title,bounds in regions:
    draw_numbered(bounds,f'逐房间_{no}.png')
    draw_numbered(bounds,f'逐房间_{no}_门洞检查.png',doors=True)
draw_numbered((490,1170,1170,1490),'K01_逐房间连通.png',targets=families if False else ['S066','S067','S053','S087'])
draw_numbered((1570,1240,2245,1500),'K02_逐房间连通.png',targets=['S072','S073','S085'])
with pymupdf.open(P/'标注.svg') as doc:
    doc[0].get_pixmap(matrix=pymupdf.Matrix(.65,.65),alpha=False).save(R/'逐房间SVG全图检查.png')
    for no,title,b in regions:
        clip=pymupdf.Rect(b[0],b[1]+125,b[2],b[3]+125)
        doc[0].get_pixmap(matrix=pymupdf.Matrix(1.5,1.5),clip=clip,alpha=False).save(R/f'逐房间SVG_{no}检查.png')
(R/'逐房间图内编号审计.json').write_text(json.dumps(badge_audit,ensure_ascii=False,indent=2)+'\n')

# Keep original confirmations and review numbers. Added unknown names are optional to supply.
rel=os.path.relpath(R,P);by_id={n['space_id']:n for n in state['name_items']}
md=['# 37号｜逐房间轮廓标注','', '<!-- annotation:summary:start -->','草稿。','<!-- annotation:summary:end -->','',
 '本图按“可辨隔墙就逐间标记”处理。房名缺失不再作为合并理由；新增房间采用原图近似轮廓，具体用途不猜测，保持 `unknown`。',
 '药房、输液大室、急诊留观等可确定名称继续保留；科室名只作为原图背景，未扩写成每间小房的名称。交通核保留较粗轮廓，家具、床位、卫生间隔断不单列。',
 '原S001—S091及名称核对号01—21保留。被拆分的旧S号对应保留单元，其余房间续号；完整拆分对应、旧填写和旧图均已归档。',
 '图内三位数字均为稳定S编号，例如 `108` 对应 `S108`。可按S号补充你确实知道的名称；无法辨认的房间无需猜名。',
 '庭院／挑空一经确定便不计面积；07、11、14继续只核对用途。','',
 f'[完整原图逐房间核对总图]({rel}/37_逐房间完整核对总图.png)','',
 f'![逐房间总图]({rel}/37_逐房间总图预览.png)','', '## 逐区房间核对','']
assigned=set()
for no,title,bounds in regions:
    crop=box(*bounds);items=[]
    for sid,item in by_id.items():
        if sid in assigned or S[sid]['type']!='unknown':continue
        poly=polys[sid]
        if crop.covers(poly.representative_point()):items.append(item);assigned.add(sid)
    items.sort(key=lambda n:int(n['review_id']))
    md += [f'### {no}｜{title}','',f'![{title}，图内为S编号]({rel}/逐房间_{no}.png)','']
    if items:
        md+=['名称不可读可继续保留未知；仅填写确实知道的名称或轮廓修正。','',
             '| 核对号 | S编号 | 预估名称（可改） | 依据与把握 | 我的确认／备注 | 核对号（重复） |',
             '| --- | --- | --- | --- | --- | --- |']
        for item in items:
            rid=item['review_id'];sid=item['space_id'];c=item.get('candidates',[])
            if item.get('split_history'):reason='原房组已拆分；旧核对号保留在本S号，原组候选不能确定单间名称。'
            else:reason=item.get('evidence','房间轮廓可辨；房名缺失或不可读。')
            estimate=' / '.join(c) if c and not item.get('split_history') else '名称不可读'
            answer=item.get('answer','待确认')
            md.append(f'| {rid} | {sid} | {estimate} | {reason} 把握：低。 | {answer} | {rid} |')
        md.append('')
leftover=[sid for sid in by_id if S[sid]['type']=='unknown' and sid not in assigned]
if leftover:raise ValueError(('missing review regions',leftover))
md+=['## 关键连通问题','']
for item in state['connectivity_items']:
    rid=item['review_id'];md += [f'### {rid}','',f'![{rid}逐房间局部]({rel}/{rid}_逐房间连通.png)','',
     '**问题：**'+item['question'],'','**我的判断：**'+item['reason'],'',
     '**我的确认／备注：**'+item.get('answer','待填写（可写实际连接方式；不需要猜门位）'),'']
md+=['房间存在、房名可读、人员可达分别记录；未补关系的房间不代表不相通，也不作为负样本。','']
out=P/'标注说明.md'
if out.exists() and '逐房间轮廓标注' in out.read_text() and '已确认' in out.read_text():
    raise ValueError('当前逐房间MD含确认文字，先同步并备份用户填写，不能覆盖。')
out.write_text('\n'.join(md))
print('review images',len(regions),'unknown rows',len(assigned),'badges',len(badge_audit))
