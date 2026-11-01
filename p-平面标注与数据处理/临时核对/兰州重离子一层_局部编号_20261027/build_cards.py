from pathlib import Path
import json,hashlib,math
from PIL import Image,ImageDraw,ImageFont
from shapely.geometry import Polygon,box

ROOT=Path('/Users/hushili/Documents/毕业 - 大论文写作/大论文')
D=ROOT/'p-写作过程/标注试样/5兰州重离子医用加速应用示范区_一层'
O=Path(__file__).parent;O.mkdir(parents=True,exist_ok=True)
data=json.loads((D/'annotation.json').read_text())
pending=[s for s in data['spaces'] if s['type']=='unknown']
expected=['S003','S019','S022','S031','S034','S037','S038','S039','S041','S042','S046','S049','S050','S053','S054','S055','S056','S057','S058','S063','S065','S066','S069','S074','S076','S077','S110','S111','S112','S113','S114','S128']
assert [s['id'] for s in pending]==expected
hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in D.iterdir() if p.is_file()}
src=Image.open(D/data['image']['file']).convert('RGB')
FONT='/System/Library/Fonts/Supplemental/Arial Unicode.ttf'
def font(n):return ImageFont.truetype(FONT,n)
factor=data['image']['width']/1374
groups=[
 ('西北上部房间',1,1,(148,438,345,588),'#2563eb'),
 ('影像区西侧及MR周边',2,4,(210,770,560,975),'#2563eb'),
 ('西侧交通核旁小房间',5,7,(290,956,490,1070),'#2563eb'),
 ('配液区北部',8,10,(812,397,978,597),'#ad245f'),
 ('东北通道两侧',11,13,(913,443,1230,598),'#ad245f'),
 ('配液区东侧',14,16,(972,555,1244,693),'#ad245f'),
 ('配液区南侧',17,19,(812,600,1040,699),'#ad245f'),
 ('北部药房及周边',20,23,(812,660,1130,983),'#b45309'),
 ('东侧交通核旁小房间',24,26,(891,957,1106,1075),'#ad245f'),
 ('南侧弧形外墙房间',27,31,(272,1370,510,1507),'#047857'),
 ('南侧入口旁房间',32,32,(774,1395,944,1504),'#b45309'),
]
index=[];mapping=[]
for page,(name,lo,hi,crop,color) in enumerate(groups,1):
    bounds=tuple(round(v*factor) for v in crop);x1,y1,x2,y2=bounds
    cw,ch=x2-x1,y2-y1;scale=min(1320/cw,1250/ch)
    pw,ph=round(cw*scale),round(ch*scale);W=max(1120,pw+64);H=ph+250
    canvas=Image.new('RGB',(W,H),'#f3f6fa');dr=ImageDraw.Draw(canvas)
    span=f'{lo:02d}' if lo==hi else f'{lo:02d}—{hi:02d}'
    dr.text((32,20),f'{page:02d}｜{name} · 核对 {span}',font=font(34),fill=color)
    dr.text((32,72),'兰州重离子一层｜彩框内数字为核对号；沿用原来的01—32编号。',font=font(24),fill='#52677b')
    ox=(W-pw)//2;oy=122
    canvas.paste(src.crop(bounds).resize((pw,ph),Image.Resampling.LANCZOS),(ox,oy))
    def cv(x,y):return ox+(x-x1)*scale,oy+(y-y1)*scale
    for n in range(lo,hi+1):
        s=pending[n-1];poly=Polygon(s['polygon_px'])
        assert box(*bounds).covers(poly),(n,bounds,poly.bounds)
        pts=[cv(x,y) for x,y in s['polygon_px']]
        dr.line(pts+[pts[0]],fill='white',width=7,joint='curve')
        dr.line(pts+[pts[0]],fill=color,width=3,joint='curve')
        bx1,by1,bx2,by2=poly.bounds
        # Keep the badge inside a corner so the room's central printed name
        # remains available for the user to read.
        fw=min(36,max(20,(bx2-bx1)*scale/2.4),(by2-by1)*scale/2)
        f=font(round(fw));text=f'{n:02d}';tb=dr.textbbox((0,0),text,font=f)
        bw=tb[2]-tb[0]+16;bh=tb[3]-tb[1]+12
        px,py=cv(bx1,by1);px+=5;py+=5
        badge=box(bx1+5/scale,by1+5/scale,bx1+(5+bw)/scale,by1+(5+bh)/scale)
        assert poly.covers(badge),(n,'badge outside space')
        dr.rounded_rectangle((px,py,px+bw,py+bh),radius=4,fill='#ffffff',outline=color,width=2)
        dr.text((px+8-tb[0],py+6-tb[1]),text,font=f,fill=color)
        mapping.append(dict(number=n,sid=s['id'],group=page,group_name=name,polygon_px=s['polygon_px']))
    legend='   '.join(f'{n:02d} → {pending[n-1]["id"]}' for n in range(lo,hi+1))
    dr.text((32,oy+ph+28),legend,font=font(26),fill=color)
    dr.text((32,oy+ph+73),f'本张 {hi-lo+1} 处待确认。可回复：{lo:02d}=名称；看不清的可先跳过。',font=font(23),fill='#52677b')
    stem=f'{page:02d}_{name}_核对{lo:02d}-{hi:02d}';canvas.save(O/(stem+'.png'))
    index.append(dict(page=page,name=name,first=lo,last=hi,file=stem+'.png',size=[W,H]))
    print(stem,[W,H],flush=True)

assert [m['number'] for m in mapping]==list(range(1,33))
assert len({m['sid'] for m in mapping})==32
(O/'编号对应.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2)+'\n')
(O/'局部图索引.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n')
lines=['# 兰州重离子一层｜32处名称局部核对','','共11张，按文件名01—11顺序查看。房间核对号沿用原来的01—32；原S编号保持不变。彩框圈定待确认空间，数字放在房间角落。当前仍是标注草稿。','','回复格式：`01=名称，02=名称……`；可分批回复，也可直接使用S编号。','']
for r in index:
    lines += [f'## {r["page"]:02d}｜{r["name"]}（{r["first"]:02d}—{r["last"]:02d}）','','![局部编号图](<'+str(O/r['file'])+'>)','','```text']
    lines += [f'{n:02d}（{pending[n-1]["id"]}）=' for n in range(r['first'],r['last']+1)]
    lines += ['```','']
(O/'按局部顺序查看.md').write_text('\n'.join(lines))

# The overview is supplementary navigation; the 11 cards are the main review.
overview=src.copy();dr=ImageDraw.Draw(overview)
for q in mapping:
    pts=[tuple(p) for p in q['polygon_px']];dr.line(pts+[pts[0]],fill='#d97706',width=5)
    x=min(p[0] for p in pts)+3;y=min(p[1] for p in pts)+3
    tb=dr.textbbox((0,0),f'{q["number"]:02d}',font=font(27));bw=tb[2]+12;bh=tb[3]-tb[1]+10
    dr.rectangle((x,y,x+bw,y+bh),fill='white',outline='#d97706',width=2)
    dr.text((x+6,y+5-tb[1]),f'{q["number"]:02d}',font=font(27),fill='#b45309')
overview.save(O/'编号定位总图.png')
for name,h in hashes.items():assert hashlib.sha256((D/name).read_bytes()).hexdigest()==h,name
assert len(list(D.iterdir()))==4
print(json.dumps({'local_images':len(index),'review_numbers':len(mapping),'unique_S_ids':32,'sample_four_files_unchanged':True},ensure_ascii=False))
