from pathlib import Path
import json,math,hashlib,xml.etree.ElementTree as ET
from PIL import Image,ImageDraw,ImageFont
from shapely.geometry import Polygon,LineString

ROOT=Path('/Users/hushili/Documents/研究-论文写作/大论文')
TMP=ROOT/'p-写作过程/临时核对/10_石家庄_20261029'
OUT=ROOT/'p-写作过程/标注试样/10_石家庄第一医院新建赵卜口院区'
d=json.loads((OUT/'annotation.json').read_text()); m=json.loads((TMP/'draft_metadata.json').read_text())
meta=m['meta']; aliases=m['aliases']; sp={s['id']:s for s in d['spaces']}
src=Image.open(OUT/d['image']['file']).convert('RGB')
assert hashlib.sha256((OUT/d['image']['file']).read_bytes()).hexdigest()==m['source_sha256']
fontfile='/System/Library/Fonts/STHeiti Medium.ttc'
def font(n):return ImageFont.truetype(fontfile,n)
palette=['#b91c1c','#0f766e','#6d28d9','#0369a1','#a21caf','#a16207','#15803d','#4338ca']

def unks(prefix):return [s['id'] for s in d['spaces'] if s['type']=='unknown' and meta[s['id']]['key'].startswith(prefix)]
def bounds(sid):return Polygon(meta[sid]['base_polygon']).bounds
def rowset(sids,ys,side,title):
    """Place row comb leaders only in the narrow corridor immediately beside a row."""
    rows={}
    for sid in sids:
        x1,y1,x2,y2=bounds(sid)
        val=y2 if side=='left' else y1
        y=min(ys,key=lambda yy:abs(yy-val))
        rows.setdefault(y,[]).append(sid)
    result=[]
    for y in sorted(rows):
        ss=sorted(rows[y],key=lambda sid:bounds(sid)[0])
        for j,sid in enumerate(ss):
            x1,y1,x2,y2=bounds(sid); x=(x1+x2)/2
            if side=='left':
                # West boundary anchors prevent leaders entering the next stacked western room.
                if x1<220:x=x1
                lane=y+3+j*1.7
                path=[(x,y2),(x,lane),(70,lane)]
            else:
                lane=y-3-(len(ss)-1-j)*1.7
                path=[(x,y1),(x,lane),(1290,lane)]
            result.append(dict(sid=sid,side=side,path=path,phase=title))
    return result

items=[]
an=unks('A_n'); an=[x for x in an if meta[x]['key'].startswith('A_n') and meta[x]['key'][3:].isdigit()]
items+=rowset(an,[365],'left','北排急诊用房')
sid=aliases['F_green1'];items.append(dict(sid=sid,side='left',path=[(565,383),(70,383)],phase='中央北庭院'))
ar=[x for x in unks('A_') if x not in an and x!=aliases['A_green']]
# Keep the garden beside the hall, with its leader through the hall below the desk.
ar1=[x for x in ar if bounds(x)[3]<=485];ar2=[x for x in ar if bounds(x)[3]>485]
items+=rowset(ar1,[420,485],'left','急诊内排与抢救支持')
items.append(dict(sid=aliases['A_green'],side='left',path=[(272,540),(70,540)],phase='急诊庭院'))
items+=rowset(ar2,[596,636,674],'left','急诊候诊及南排')
items+=rowset(unks('B_'),[321,366,389,429,447,478,507,519,538,595],'right','东北影像组团')
c=unks('C_'); specials={aliases['C_green'],aliases['C_green2']}
c1=[x for x in c if x not in specials and bounds(x)[3]<=905]
c2=[x for x in c if x not in specials and bounds(x)[3]>905]
items.append(dict(sid=aliases['C_green'],side='left',path=[(239,740),(70,740)],phase='西中北庭院'))
items+=rowset(c1,[828,905],'left','西中诊疗北排与设备用房')
items.append(dict(sid=aliases['C_green2'],side='left',path=[(300,1009),(70,1009)],phase='西中南庭院'))
items+=rowset(c2,[1062,1141],'left','西中诊疗南排')
items+=rowset(unks('D_'),[697,753,792,833],'right','药房及配套用房')
items.append(dict(sid=aliases['F_green2'],side='right',path=[(678,952),(678,990),(1290,990)],phase='中央南庭院'))
e=unks('E_')
south=[x for x in e if meta[x]['key'].startswith(('E_southcounter','E_n')) or meta[x]['key'] in [f'E_s{i}' for i in range(5,10)]]
ew=[x for x in e if x not in south and x!=aliases['E_green']]
items.append(dict(sid=aliases['E_green'],side='left',path=[(315,1206),(70,1206)],phase='西南庭院'))
items+=rowset(ew,[1257,1315,1380],'left','西南门诊用房')
items.append(dict(sid=aliases['F_foyer'],side='right',path=[(1044,1067),(1044,1062),(1290,1062)],phase='弧形入口范围'))
items+=rowset(south,[1256,1280,1340],'right','南侧柜台与附属用房')
assert len(items)==len({i['sid'] for i in items})==sum(s['type']=='unknown' for s in d['spaces'])
assert {i['sid'] for i in items}=={s['id'] for s in d['spaces'] if s['type']=='unknown'}
for n,i in enumerate(items,1):
    i['number']=f'{n:02d}'; mm=meta[i['sid']]
    i.update(candidate=mm['candidate'],evidence=mm['evidence'],confidence=mm['confidence'])
    if any(v in i['evidence'] for v in ['没有足够','无可靠用途依据','暂无可靠完整','没有可靠']):i['candidate']='用途未知'
    i['color']=palette[(n-1)//8%len(palette)]

# Source-space leaders and gutter fan leaders are checked independently for crossings.
cross=[]
for j,a in enumerate(items):
    for b in items[j+1:]:
        z=LineString(a['path']).intersection(LineString(b['path']))
        if not z.is_empty:cross.append([a['number'],b['number'],z.wkt])
(TMP/'leader_intersections.json').write_text(json.dumps(cross,ensure_ascii=False,indent=2))
print('source leader intersections:',len(cross))
if cross:
    print(json.dumps(cross[:30],ensure_ascii=False,indent=2))

scale=4; bar=1440; gap=70; top=230
IW,IH=1367*scale,1824*scale
canvas=Image.new('RGB',(bar*2+gap*2+IW,IH+top+190),'#f8fafc')
ox=bar+gap;oy=top
canvas.paste(src.resize((IW,IH),Image.Resampling.LANCZOS),(ox,oy))
draw=ImageDraw.Draw(canvas)
draw.text((60,35),'10号平面｜名称与范围核对总图（标注草稿）',font=font(54),fill='#0f172a')
draw.text((60,112),f'{len(items)}项待确认；数字按相邻片区排列，标签同时标出稳定S编号；所有候选尚未写入核心JSON。',font=font(30),fill='#475569')
draw.text((60,164),'回复示例：01=诊室，02=治疗室；可分批确认。绿色区域请同时说明是否为露天／挑空庭院。',font=font(28),fill='#475569')
def pt(p):return (ox+p[0]*scale,oy+p[1]*scale)
def badge_anchor(poly):
    p=Polygon(poly);x1,y1,x2,y2=p.bounds
    # Keep the room's original central lettering unobscured.
    q=(x1+7,y1+7)
    from shapely.geometry import box
    return q if p.covers(box(q[0]-5,q[1]-5,q[0]+5,q[1]+5)) else (p.representative_point().x,p.representative_point().y)
for side in ['left','right']:
    ss=[i for i in items if i['side']==side]
    # Items on each side have increasing corridor ports. Preserve that order throughout the gutter.
    bad=[(a['number'],b['number'],a['path'][-1][1],b['path'][-1][1]) for a,b in zip(ss,ss[1:]) if a['path'][-1][1]>=b['path'][-1][1]]
    assert not bad,(side,bad)
    last=top+300
    for i in ss:
        target=top+i['path'][-1][1]*scale
        cy=max(target,last+67);last=cy
        i['label_y']=cy
        xend=bar-12 if side=='left' else ox+IW+gap+12
        i['canvas_path']=[pt(p) for p in i['path']]+[(xend,cy)]
        draw.line(i['canvas_path'],fill=i['color'],width=3,joint='curve')
        lx=38 if side=='left' else ox+IW+gap+28
        draw.rounded_rectangle((lx-8,cy-27,lx+bar-78,cy+29),radius=7,fill='white',outline=i['color'],width=2)
        draw.text((lx,cy-25),f'{i["number"]}｜{i["sid"]}  候选：{i["candidate"]}',font=font(25),fill=i['color'])
        evidence=i['evidence']
        while draw.textlength(f'把握：{i["confidence"]}｜{evidence}',font=font(19))>bar-100:evidence=evidence[:-2]+'…'
        draw.text((lx,cy+5),f'把握：{i["confidence"]}｜{evidence}',font=font(19),fill='#475569')
        assert cy+35<canvas.height-70
for i in items:
    poly=meta[i['sid']]['base_polygon'];pp=[pt(p) for p in poly]
    draw.line(pp+[pp[0]],fill=i['color'],width=5,joint='curve')
    cx,cy=pt(badge_anchor(poly))
    text=i['number'];bw=draw.textlength(text,font=font(28))+14
    draw.rounded_rectangle((cx-bw/2,cy-20,cx+bw/2,cy+20),radius=5,fill='white',outline=i['color'],width=3)
    draw.text((cx-bw/2+7,cy-17),text,font=font(28),fill=i['color'])
fullcross=[]
for j,a in enumerate(items):
    for b in items[j+1:]:
        z=LineString(a['canvas_path']).intersection(LineString(b['canvas_path']))
        if not z.is_empty:fullcross.append([a['number'],b['number'],z.wkt])
assert not fullcross,fullcross
(TMP/'全图引线核验.json').write_text(json.dumps(dict(source_crossings=cross,full_canvas_crossings=fullcross,
    frames=len(items),unique_numbers=len({x['number'] for x in items}),unique_space_ids=len({x['sid'] for x in items})),ensure_ascii=False,indent=2)+'\n')
draw.text((60,canvas.height-100),'原图完整保留居中；彩框及引线为叠加层，入口箭头与家具不作为新增墙线。核对号映射只保存在临时目录。',font=font(26),fill='#475569')
canvas.save(TMP/'10号_高清核对总图.png',optimize=True)
canvas.resize((round(canvas.width*.3),round(canvas.height*.3)),Image.Resampling.LANCZOS).save(TMP/'10号_核对总图预览.jpg',quality=92)

# Supplemental dense-region enlargements keep the same numbers and show the underlying room words.
regions=[('01_西北急诊',(165,310,490,680),'A_'),('02_东北影像',(725,310,1180,685),'B_'),
 ('03_西中诊疗',(165,675,490,1145),'C_'),('04_药房',(725,680,1180,995),'D_'),
 ('05_西南门诊',(165,1135,490,1395),'E_'),('06_南侧附属',(475,1245,740,1395),'E_south')]
for name,b,prefix in regions:
    if prefix=='E_south':sel=[i for i in items if i['sid'] in south]
    elif prefix=='E_':sel=[i for i in items if meta[i['sid']]['key'].startswith('E_') and i['sid'] not in south]
    else:sel=[i for i in items if meta[i['sid']]['key'].startswith(prefix)]
    z=4;pw=(b[2]-b[0])*z;ph=(b[3]-b[1])*z; legend=1300
    hh=max(ph+140,len(sel)*68+150)
    im=Image.new('RGB',(pw+legend+100,hh),'#f8fafc');dd=ImageDraw.Draw(im)
    crop=src.crop(tuple(round(v*src.width/1367) if k%2==0 else round(v*src.height/1824) for k,v in enumerate(b))).resize((pw,ph),Image.Resampling.LANCZOS)
    im.paste(crop,(35,100))
    dd.text((35,25),name+'｜与总图使用相同核对号',font=font(34),fill='#0f172a')
    for j,i in enumerate(sel):
        poly=meta[i['sid']]['base_polygon'];pp=[(35+(x-b[0])*z,100+(y-b[1])*z) for x,y in poly]
        dd.line(pp+[pp[0]],fill=i['color'],width=4,joint='curve')
        ax,ay=badge_anchor(poly);cx=35+(ax-b[0])*z;cy=100+(ay-b[1])*z
        bw=dd.textlength(i['number'],font=font(28))+12
        dd.rounded_rectangle((cx-bw/2,cy-20,cx+bw/2,cy+20),radius=4,fill='white',outline=i['color'],width=2)
        dd.text((cx-bw/2+6,cy-17),i['number'],font=font(28),fill=i['color'])
        xx=pw+70;yy=110+j*68
        dd.text((xx,yy),f'{i["number"]}｜{i["sid"]}  候选：{i["candidate"]}',font=font(26),fill=i['color'])
        dd.text((xx,yy+34),f'把握：{i["confidence"]}｜{i["evidence"]}',font=font(20),fill='#475569')
    im.save(TMP/(name+'_放大.png'),optimize=True)

mapping=[{k:i[k] for k in ['number','sid','phase','candidate','evidence','confidence','side']} for i in items]
mp=TMP/'核对编号映射.json'
if mp.exists():
    old=json.loads(mp.read_text());assert [(v['number'],v['sid']) for v in old]==[(v['number'],v['sid']) for v in mapping], 'Mapping changed; preserve established numbers.'
mp.write_text(json.dumps(mapping,ensure_ascii=False,indent=2)+'\n')
lines=['# 10号平面名称核对（标注草稿）','',f'共 {len(items)} 项待确认。候选仅供辨认，核心 JSON 仍为 unknown。','',
 '按相邻片区从上到下、同排从左到右阅读；核对号在本轮分批回答期间保持不变。可按 `01=名称，02=名称` 回复，也可用 S 编号。',
 '','庭院类请同时说明露天／挑空还是可步入室内；弧形入口需确认室内门厅还是室外雨棚。','',
 '|核对号|S编号|片区|候选（均待确认）|依据|把握|','|---|---|---|---|---|---|']
for i in items:lines.append(f'|{i["number"]}|{i["sid"]}|{i["phase"]}|{i["candidate"]}|{i["evidence"]}|{i["confidence"]}|')
(TMP/'核对清单.md').write_text('\n'.join(lines)+'\n')

# Fit each visible SVG label fully within its spatial polygon, including thin circulation strips.
svg=OUT/'标注.svg';tree=ET.parse(svg);ns={'s':'http://www.w3.org/2000/svg'}
for sid,s in sp.items():
    g=tree.find(f'.//s:g[@id="{sid}"]',ns)
    if g is None:continue
    rect=g.find('s:rect',ns);texts=g.findall('s:text',ns)
    if rect is None or not texts:continue
    poly=Polygon(s['polygon_px']);rep=poly.representative_point();rx,ry=rep.x,rep.y
    x,y,w,h=[float(rect.get(k)) for k in ['x','y','width','height']]
    # Uniform scaling around interior anchor keeps the full name visible without intruding on neighbouring labels.
    f=1.
    from shapely.geometry import box
    while f>.08 and not poly.covers(box(rx-w*f/2,ry-h*f/2,rx+w*f/2,ry+h*f/2)):f*=.94
    if f<.999:
        holder=ET.Element('{'+ns['s']+'}g',{'transform':f'translate({rx} {ry}) scale({f}) translate({-x-w/2} {-y-h/2})'})
        for el in [rect]+texts:g.remove(el);holder.append(el)
        g.append(holder)
tree.write(svg,encoding='unicode')

# Render the actual SVG with system fonts for visual inspection.
import subprocess
rendered=TMP/'10号_SVG浏览器检查.png'
subprocess.run(['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome','--headless','--disable-gpu','--no-first-run','--no-default-browser-check','--hide-scrollbars',
    '--user-data-dir=/tmp/sgz10-svg-render','--force-device-scale-factor=2','--window-size=2444,3418','--screenshot='+str(rendered),svg.as_uri()],check=True,capture_output=True)
r=Image.open(rendered).convert('RGB')
r.save(TMP/'10号_标注完整检查.png')
r.resize((1222,round(r.height*1222/r.width)),Image.Resampling.LANCZOS).save(TMP/'10号_标注检查预览.jpg',quality=92)
for name,b in [('急诊',(170,315,490,680)),('影像',(730,315,1180,685)),('南侧',(300,1240,740,1390))]:
    # SVG adds a 122.2 px title above the original image.
    head=max(65,min(125,d['image']['width']*.05))
    actual_scale=r.width/d['image']['width']
    bb=(round(b[0]*d['image']['width']/1367*actual_scale),round((b[1]*d['image']['height']/1824+head)*actual_scale),round(b[2]*d['image']['width']/1367*actual_scale),round((b[3]*d['image']['height']/1824+head)*actual_scale))
    r.crop(bb).save(TMP/f'10号_SVG密集检查_{name}.png')
print(json.dumps(dict(review_count=len(items),overview_size=canvas.size,source_leader_crossings=len(cross),mapping=str(mp)),ensure_ascii=False))
