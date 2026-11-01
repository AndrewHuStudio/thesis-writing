from pathlib import Path
import json, math, base64, hashlib, shutil
from io import BytesIO
from xml.sax.saxutils import escape
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon, LineString, Point
from scipy.optimize import linprog
import pymupdf

ROOT=Path('/Users/hushili/Documents/毕业 - 大论文写作/大论文')
D=ROOT/'p-写作过程/标注试样/3晋中市第一人民医院_一层'
O=ROOT/'p-写作过程/临时核对/晋中一层_假设版_20261027'
O.mkdir(parents=True,exist_ok=True)
data=json.loads((D/'annotation.json').read_text())
by={s['id']:s for s in data['spaces']}
mapping_path=O/'原核对号映射.json'
if not mapping_path.exists():shutil.copy2('/tmp/jinzhong-annotation/假设版_20261027/原核对号映射.json',mapping_path)
mapping=json.loads(mapping_path.read_text())
initial={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in D.iterdir() if p.is_file()}
(O/'修改前备份').mkdir(exist_ok=True)
for p in D.iterdir():
    if p.is_file() and not (O/'修改前备份'/p.name).exists():shutil.copy2(p,O/'修改前备份'/p.name)

# These are review hypotheses. The core JSON keeps its 21 unknown spaces.
rows=[
 (4,'设备间','弱','紧邻交通核、形状狭长，未辨认出房名；暂拟设备用途。'),
 (9,'辅料室','较有依据','沿用用户的暂定原名；未擅自改为“敷料室”。'),
 (10,'器械检查室','较有依据','沿用用户暂定用途，图面可见器械处理工作台。'),
 (11,'敷料打包室','较有依据','沿用用户暂定用途，邻接器械检查及清洁处理区。'),
 (12,'纯水间','较有依据','模糊房名疑似“纯水”；仍只作假设。'),
 (13,'淋浴间','较有依据','图面字形及与14的成对布置支持淋浴／更衣组合。'),
 (14,'更衣室','较有依据','与13成对；用户确认13—14与15—16用途对应。'),
 (15,'淋浴间','较有依据','按用户指出的重复组合，与13采用相同假设。'),
 (16,'更衣室','较有依据','按用户指出的重复组合，与14采用相同假设。'),
 (17,'物品暂存间','弱','邻接去污及清洁处理区，房名不清；采用较粗的暂存功能。'),
 (21,'开水间','较有依据','位于工作人员支持用房一侧，模糊字形疑似“开水”。'),
 (23,'卫生间','较有依据','用户暂称“洁厕间”，图面可见类似卫生洁具的布置。'),
 (32,'更衣室','弱','与已确认31号更衣室相邻，暂按同组工作人员更衣用房理解；不细分男女。'),
 (33,'工作人员休息室','弱','位于住院支持用房排内、靠近更衣及交通核，仅作宽泛功能推测。'),
 (34,'设备间','弱','形状与北侧04对应、紧邻交通核，暂采用相同功能假设。'),
 (44,'卫生间','较有依据','用户给出厕所／洁具／更衣范围，图面可见成组洁具。'),
 (46,'盥洗间','弱','邻接44号卫生间，似有水池布置；具体房名无法确认。'),
 (48,'卫生间','较有依据','图面有成组类似洁具的符号，与用户给出的范围相符。'),
 (49,'卫生间前室','弱','狭窄条形空间、邻接卫生用房；暂按过渡空间理解。'),
 (50,'卫生间前室','弱','与48及51相邻的窄条空间；具体边界及用途仍待复核。'),
 (51,'更衣室','弱','沿用用户给出的用途范围，临近急诊手术支持区；不区分使用人群。'),
]
H={n:dict(number=n,name=name,basis=basis,reason=reason) for n,name,basis,reason in rows}
for q in mapping:
    s=by[q['sid']]
    q['polygon']=[[y,1440-x] for x,y in s['polygon_px']]
    q['confirmed_name']=s['name']
    if q['number'] in H:H[q['number']].update(sid=q['sid'],polygon=q['polygon'])
assert {q['sid'] for q in H.values()}=={s['id'] for s in data['spaces'] if s['type']=='unknown'}
assert len(H)==21
(O/'假设清单及编号映射.json').write_text(json.dumps({'hypotheses':list(H.values()),'review_number_map':mapping},ensure_ascii=False,indent=2))
hi=Image.open(ROOT/'i-医院门诊平面/3晋中市第一人民医院_一层平面图.jpg').transpose(Image.Transpose.ROTATE_90)
# Align the high-resolution reference with the existing 1725 x 1440 upright coordinates.
hi=hi.resize((5175,4320),Image.Resampling.LANCZOS)
spec=[
 (1,'北侧病房楼',(1090,45,1590,305),[4]),
 (2,'中心供应',(630,145,1035,400),[9,10,11,12,13,14,15,16,17,21]),
 (3,'西侧门诊',(205,430,505,665),[23]),
 (5,'南侧住院支持',(1080,580,1590,880),[32,33,34]),
 (8,'急诊及相邻服务',(800,925,1220,1305),[44,46,48,49,50,51]),
]
ys={4:82,9:184,10:196,11:208,12:237,13:284,14:288,15:292,16:296,17:312,21:376,23:561,32:712,33:715,34:719,44:1015,46:1032,48:1058,49:1070.8,50:1077.2,51:1094}
results=[]
for page,name,bounds,ns in spec:
    x1,y1,x2,y2=bounds;scale=3.;pw=(x2-x1)*scale;ph=(y2-y1)*scale
    right=page in (1,5)
    # Sidebar rows retain review-number order. Linear constraints keep every
    # pair of leaders vertically ordered over their shared horizontal extent.
    ax=[];ay=[]
    for n in ns:
        p=Polygon(H[n]['polygon']);a=p.representative_point();yy=ys[n]
        cross=p.intersection(LineString([(x1-10,yy),(x2+10,yy)]))
        xx=(cross.bounds[0]+cross.bounds[2])/2
        assert p.covers(Point(xx,yy))
        localx=(xx-x1)*scale
        ax.append(pw-localx if right else localx);ay.append((yy-y1)*scale)
    # Solve the fan using the original overview's distant sidebar, then clip
    # at the crop edge. A close sidebar can make dense, interleaved rooms
    # impossible to connect in number order with straight segments.
    k=len(ns);start=-((1725-x2 if right else x1)+44)*scale;gap=85.
    A=[];B=[]
    for i in range(k-1):
        row=[0.]*(2*k);row[i]=1;row[i+1]=-1;A.append(row);B.append(-gap)
    for i in range(k):
        for j in range(i+1,k):
            near=min(ax[i],ax[j]);ti=(near-start)/(ax[i]-start);tj=(near-start)/(ax[j]-start)
            row=[0.]*(2*k);row[i]=1-ti;row[j]=-(1-tj)
            A.append(row);B.append(tj*ay[j]-ti*ay[i]-2.)
    for i in range(k):
        row=[0.]*(2*k);row[i]=1;row[k+i]=-1;A.append(row);B.append(ay[i])
        row=[0.]*(2*k);row[i]=-1;row[k+i]=-1;A.append(row);B.append(-ay[i])
    lp=linprog([0.]*k+[1.]*k,A_ub=A,b_ub=B,bounds=[(None,None)]*k+[(0,None)]*k,method='highs')
    assert lp.success,lp.message
    fan=lp.x[:k]
    ports=[fan[i]+(ay[i]-fan[i])*(-start)/(ax[i]-start) for i in range(k)]
    assert all(ports[i]<ports[i+1] for i in range(k-1))
    ly=[]
    for port in ports:ly.append(max(port,ly[-1]+gap) if ly else port)
    shift=170-min(0,min(ly)-37)
    picx=35. if right else 790.;labelx=picx+pw+180 if right else 35.;labelw=575.
    W=math.ceil(labelx+labelw+35 if right else picx+pw+35);height=math.ceil(max(shift+ph,shift+max(ly)+37)+100)
    def cv(x,y):return picx+(x-x1)*scale,shift+(y-y1)*scale
    paths=[LineString([(labelx if right else labelx+labelw,shift+ly[i]),(picx+pw if right else picx,shift+ports[i]),(picx+pw-ax[i] if right else picx+ax[i],shift+ay[i])]) for i in range(k)]
    assert not [(i,j) for i in range(k) for j in range(i+1,k) if paths[i].intersects(paths[j])]
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{height}" viewBox="0 0 {W} {height}">','<rect width="100%" height="100%" fill="#f3f6fa"/>','<style>text{font-family:Arial,"PingFang SC","Microsoft YaHei",sans-serif}</style>']
    def tx(x,y,t,size=27,color='#263b50',weight=400):svg.append(f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" font-weight="{weight}" fill="{color}">{escape(t)}</text>')
    tx(35,57,f'{page:02d}｜{name} · 功能假设',40,'#9a5708',700)
    tx(35,102,'晋中市第一人民医院一层｜原核对号及 S 编号不变；橙色均为假设，名称仍未确认。',24)
    buf=BytesIO();hi.crop(tuple(v*3 for v in bounds)).save(buf,format='PNG')
    src=base64.b64encode(buf.getvalue()).decode()
    svg.append(f'<image x="{picx}" y="{shift}" width="{pw}" height="{ph}" xlink:href="data:image/png;base64,{src}"/>')
    for p in paths:
        pts=' '.join(f'{x:.2f},{y:.2f}' for x,y in p.coords)
        svg.append(f'<polyline points="{pts}" fill="none" stroke="white" stroke-width="7" opacity=".9"/>')
        svg.append(f'<polyline points="{pts}" fill="none" stroke="#b86d0d" stroke-width="2.5"/>')
    for i,n in enumerate(ns):
        q=H[n];p=Polygon(q['polygon']);pts=' '.join(f'{cv(x,y)[0]:.2f},{cv(x,y)[1]:.2f}' for x,y in q['polygon'])
        svg.append(f'<polygon points="{pts}" fill="#fbbf24" fill-opacity=".16" stroke="#b86d0d" stroke-width="3"/>')
        # The small room badge fits inside even the narrow transition spaces.
        fs=min(12,(p.bounds[3]-p.bounds[1])*0.65,(p.bounds[2]-p.bounds[0])*0.45)
        a=p.representative_point();cx,cy=cv(a.x,a.y);fs*=scale
        svg.append(f'<rect x="{cx-fs*.8:.2f}" y="{cy-fs*.65:.2f}" width="{fs*1.6:.2f}" height="{fs*1.3:.2f}" rx="3" fill="white" stroke="#b86d0d"/>')
        svg.append(f'<text x="{cx:.2f}" y="{cy+fs*.35:.2f}" text-anchor="middle" font-size="{fs:.2f}" fill="#9a5708" font-weight="700">{n:02d}</text>')
        top=shift+ly[i]-36
        svg.append(f'<rect x="{labelx}" y="{top:.2f}" width="{labelw}" height="72" rx="8" fill="#fff2d6" stroke="#b86d0d" stroke-width="2"/>')
        tx(labelx+14,top+29,f'{n:02d}｜{q["sid"]}  假设：{q["name"]}',25,'#874b07',700)
        tx(labelx+14,top+56,'依据较弱，保留其他可能' if q['basis']=='弱' else '有图面或用户暂定名称支持，仍待确认',19,'#705f48')
    tx(35,height-43,f'本张 {k} 项假设｜原有已确认名称保留；完整依据见《21项功能假设》。',24)
    svg.append('</svg>');stem=f'{page:02d}_{name}_功能假设'
    sp=O/(stem+'.svg');sp.write_text('\n'.join(svg))
    doc=pymupdf.open(sp);doc[0].get_pixmap(alpha=False).save(O/(stem+'.png'))
    results.append(dict(page=page,name=name,numbers=ns,png=stem+'.png',svg=stem+'.svg',width=W,height=height,crossings=0))
    print(stem,W,height,flush=True)

lines=['# 晋中市第一人民医院一层｜21项功能假设','','这是一轮可审核的功能假设。原来明确确认的35项、43号收费处及56号过道修正均保留。正式JSON仍有21处 unknown；本轮未把假设写成已确认名称。','','核对号沿用上一轮01—56，不重新编号。32、33不区分男女；49、50暂按卫生间前室理解，不能据此认定原图房名或调整边界。','','| 核对号 | S编号 | 假设名称 | 依据程度 | 依据与限制 |','|---|---|---|---|---|']
for n in sorted(H):
    q=H[n];lines.append(f'| {n:02d} | {q["sid"]} | {q["name"]} | {q["basis"]} | {q["reason"]} |')
lines+=['','可按“全部按假设采用”或“04改为……，其余采用”回复；也可保留部分未知。','']
for r in results:
    lines += [f'## {r["page"]:02d}｜{r["name"]}','','![组团功能假设](<'+str(O/r['png'])+'>)','','[打开可放大的SVG](<'+str(O/r['svg'])+'>)','','本张核对号：'+ '、'.join(f'{n:02d}' for n in r['numbers'])+'。','']
(O/'21项功能假设.md').write_text('\n'.join(lines))
(O/'组团索引.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
# Keep the four-file sample overview current; no hypothesis fields enter JSON.
mp=D/'标注说明.md';md=mp.read_text();mark='**当前核对入口：**'
if mark in md:md=md[:md.index(mark)].rstrip()+'\n'
md+='\n**功能假设核对：**已为剩余21处制作[假设清单与五张组团图](<'+str(O/'21项功能假设.md')+'>)，沿用本轮核对号，明确标注“假设”。假设尚未确认为原图名称；核心JSON和标注SVG仍保留21处未确认。\n'
mp.write_text(md)
for name,h in initial.items():
    if name!='标注说明.md':assert hashlib.sha256((D/name).read_bytes()).hexdigest()==h,name
assert len(list(D.iterdir()))==4
assert sum(len(r['numbers']) for r in results)==21
font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Unicode.ttf',26)
qa=Image.new('RGB',(1800,1500),'#e5ebf2');dr=ImageDraw.Draw(qa)
for i,r in enumerate(results):
    im=Image.open(O/r['png']);im.thumbnail((870,440));x=(i%2)*900;y=(i//2)*500
    qa.paste(im,(x+(900-im.width)//2,y+45));dr.text((x+20,y+10),f'{r["page"]:02d} {r["name"]}',font=font,fill='#263b50')
qa.save(O/'排版检查.png')
print(json.dumps({'hypotheses':len(H),'groups':len(results),'core_files':len(list(D.iterdir())),'core_json_svg_source_unchanged':True,'output':str(O)},ensure_ascii=False))
