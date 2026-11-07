from pathlib import Path
import json, math, random
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon, LineString

TMP=Path('/tmp/outpatient39-review')
pending=json.loads((TMP/'review_mapping.json').read_text())
src=Image.open(TMP/'原图_阅读方向.png').convert('RGB')
FONT='/System/Library/Fonts/STHeiti Medium.ttc'
colors={'A':'#0f766e','B':'#7c3aed','C':'#c2410c','D':'#0369a1','E':'#a21caf','F':'#166534'}
names={'A':'会议片区','B':'后勤片区','C':'急诊片区','D':'影像／放射片区','E':'超声／药房片区','F':'门诊入口片区'}

def iso(vals,gap):
    pools=[]
    for i,v in enumerate(vals):
        pools.append([v-i*gap,1])
        while len(pools)>1 and pools[-2][0]/pools[-2][1]>pools[-1][0]/pools[-1][1]:
            a,b=pools[-2:];pools[-2:]=[[a[0]+b[0],a[1]+b[1]]]
    out=[]
    for su,n in pools:out.extend([su/n]*n)
    return [v+i*gap for i,v in enumerate(out)]

def crosses(a,b):
    def cross(p,q,r):return (q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])
    p,q=a;r,s=b
    return cross(p,q,r)*cross(p,q,s)<-1e-6 and cross(r,s,p)*cross(r,s,q)<-1e-6

def make(items,bounds,name,scale=2,full=False):
    x0,y0,x1,y1=bounds
    # 原图完整保留；总图的右栏利用建筑与原图图例之间的非建筑留白。
    margin=780 if full else 720
    top=180
    w=int((x1-x0)*scale+2*margin);h=int((y1-y0)*scale+top+180)
    if full:h=max(h,4900)
    base=Image.new('RGB',(w,h),'#f2f5f8')
    base.paste(src.crop(bounds).resize((int((x1-x0)*scale),int((y1-y0)*scale))),(margin,top))
    d=ImageDraw.Draw(base)
    def f(size):return ImageFont.truetype(FONT,size)
    d.text((35,25),'39｜梅州市蕉岭县人民医院 · 首层标注草稿',font=f(38),fill='#18314c')
    d.text((35,82),f'本图 {len(items)} 项待核对｜按连续片区由上至下、同排由左至右｜候选用途均未写入核心JSON',font=f(26),fill='#4b5563')
    if full:d.text((35,124),'原图仅转正显示，原文件未修改；科室按功能块标注，内部无名房间不推定为具体机房。',font=f(24),fill='#4b5563')
    placements=[]
    for s in items:
        side='left' if s['group'] in 'ACF' else 'right'
        if not full:
            # 局部图连续号前半组放左，后半组放右。
            side='left' if items.index(s)<math.ceil(len(items)/2) else 'right'
        poly=Polygon(s['polygon']);rp=poly.representative_point();ay=rp.y
        scan=poly.intersection(LineString([(poly.bounds[0]-1,ay),(poly.bounds[2]+1,ay)]))
        minx,_,maxx,_=scan.bounds
        ax=minx+3 if side=='left' else maxx-3
        # 锚点位于框内近侧边缘，彩框和编号都对应同一个稳定S编号。
        anchor=(margin+(ax-x0)*scale,top+(ay-y0)*scale)
        labelx=25 if side=='left' else (margin+(1760-x0)*scale if full else w-margin+25)
        labelw=margin-55 if side=='left' else (900 if full else margin-55)
        endx=labelx+labelw if side=='left' else labelx
        placements.append(dict(s=s,side=side,anchor=list(anchor),lx=labelx,lw=labelw,ex=endx,ly=anchor[1],poly=poly))
    for side in ['left','right']:
        pp=[p for p in placements if p['side']==side]
        ys=iso([p['ly'] for p in pp],112)
        for p,y in zip(pp,ys):p['ly']=max(255,min(h-140,y))
    # 对同栏引线做确定性搜索，微调锚点和标签高度，直到不相交。
    rng=random.Random(3901+len(items))
    def lines():return [((p['ex'],p['ly']),tuple(p['anchor'])) for p in placements]
    def bad_pairs():
        ls=lines();return [(i,j) for i in range(len(ls)) for j in range(i+1,len(ls)) if crosses(ls[i],ls[j])]
    initial=len(bad_pairs())
    for it in range(22000):
        bad=bad_pairs()
        if not bad:break
        i,j=rng.choice(bad);p=placements[rng.choice([i,j])]
        old=(p['ly'],p['anchor'].copy())
        if rng.random()<.55:
            same=[q for q in placements if q['side']==p['side']];idx=same.index(p)
            lo=(same[idx-1]['ly']+112) if idx else 255
            hi=(same[idx+1]['ly']-112) if idx<len(same)-1 else h-140
            if lo<=hi:p['ly']=rng.uniform(lo,hi)
        else:
            poly=p['poly'];bx,by,ex,ey=poly.bounds
            ay=rng.uniform(by+2,ey-2)
            scan=poly.intersection(LineString([(bx-1,ay),(ex+1,ay)]))
            if not scan.is_empty:
                sx,_,tx,_=scan.bounds;ax=(sx+3 if p['side']=='left' else tx-3)
                p['anchor']=[margin+(ax-x0)*scale,top+(ay-y0)*scale]
        new=len(bad_pairs())
        if new>len(bad) or (new==len(bad) and rng.random()<.15):p['ly'],p['anchor']=old
    bad=bad_pairs()
    # 连线先画，框、编号与标签最后画，防止连线覆盖文字。
    for p in placements:
        col=colors[p['s']['group']]
        d.line([(p['ex'],p['ly']),tuple(p['anchor'])],fill=col,width=3)
    for p in placements:
        s=p['s'];col=colors[s['group']]
        pts=[(margin+(x-x0)*scale,top+(y-y0)*scale) for x,y in s['polygon']]
        d.line(pts+[pts[0]],fill=col,width=4)
        ax,ay=p['anchor'];rr=20
        d.ellipse((ax-rr,ay-rr,ax+rr,ay+rr),fill=col,outline='white',width=2)
        d.text((ax,ay),s['review'],font=f(23),fill='white',anchor='mm')
        lx,ly,lw=p['lx'],p['ly'],p['lw'];pad=12
        d.rounded_rectangle((lx,ly-50,lx+lw,ly+50),radius=9,fill='white',outline=col,width=2)
        d.text((lx+pad,ly-44),f"{s['review']}｜{s['id']} · {names[s['group']]}",font=f(27),fill=col)
        text=' / '.join(s['candidates'])+f"（把握：{s['confidence']}）"
        d.text((lx+pad,ly-10),text,font=f(22),fill='#172b4d')
        why=s['why']
        # 主图短依据，完整依据另存临时清单；局部图保留相同候选。
        if len(why)>27:why=why[:26]+'…'
        d.text((lx+pad,ly+20),'依据：'+why,font=f(20),fill='#52677b')
    d.text((35,h-90),'回复格式：01=名称，02=名称；可以分批，也可直接用S编号。无把握可保留未知。',font=f(28),fill='#18314c')
    path=TMP/(name+'.png');base.save(path)
    report=dict(file=str(path),size=[w,h],items=[p['s']['review'] for p in placements],initial_crossings=initial,crossings=[(placements[i]['s']['review'],placements[j]['s']['review']) for i,j in bad])
    print(json.dumps(report,ensure_ascii=False))
    return report

reports=[make(pending,(0,0,3104,2424),'39_首层_核对总图',2,True)]
for g,b in [('A',(160,370,700,955)),('B',(750,420,1740,880)),('C',(160,925,735,1700)),('D',(755,1130,1450,1255)),('E',(755,1220,1450,1700)),('F',(315,1665,880,1920))]:
    reports.append(make([s for s in pending if s['group']==g],b,'39_局部_'+g+'_'+names[g],2.5))
(TMP/'review_layout_check.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2)+'\n')
lines=['# 39号首层：39项待确认（标注草稿）','','编号以本轮核对总图为准，分批回答时不改号。候选只用于核对，不是已确认名称。','']
for s in pending:
    lines.extend([f"- **{s['review']}｜{s['id']}**：{' / '.join(s['candidates'])}（把握：{s['confidence']}）。依据：{s['why']}。"])
(TMP/'待确认清单.md').write_text('\n'.join(lines)+'\n')
