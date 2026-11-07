from pathlib import Path
import ast, json, re, os, shutil, hashlib
from PIL import Image,ImageDraw,ImageFont,ImageOps
from shapely.geometry import Polygon,Point,LineString,box as geometry_box

W=Path(__file__).parent;ROOT=W.parents[2]
P=ROOT/'标注试样/26_济南军区总医院门诊综合楼'
OLD=W.parent/'20261105_首次补充'
d=json.loads((P/'annotation.json').read_text());ss={s['id']:s for s in d['spaces']}
changes=json.loads((W/'补图变更记录.json').read_text())
md=(W/'补充前四文件/标注说明.md').read_text()
current=(P/'标注说明.md').read_text()
last_digest=W/'最近生成说明.sha256'
assert current==md or (last_digest.exists() and hashlib.sha256(current.encode()).hexdigest()==last_digest.read_text().strip()),'MD changed since backup; merge new user edits first.'
mapfile=OLD/'固定核对映射.json'
if not (W/'补图前固定核对映射.json').exists():shutil.copy2(mapfile,W/'补图前固定核对映射.json')
mapping=json.loads((W/'补图前固定核对映射.json').read_text())
mapping.extend([
 dict(review_id='61',space_id='S114',group='09',group_title='补图新增空间'),
 dict(review_id='62',space_id='S115',group='09',group_title='补图新增空间'),
 dict(review_id='63',space_id='S109',group='09',group_title='原标签撤回核对'),
])
assert len(mapping)==63 and len({m['space_id'] for m in mapping})==63
mapfile.write_text(json.dumps(mapping,ensure_ascii=False,indent=2)+'\n')
mp={m['space_id']:m for m in mapping}
# Reuse the published geometry-to-review mapping and room badge placements.
tree=ast.parse((OLD/'制作核对26.py').read_text())
settings={}
for node in tree.body:
    if isinstance(node,ast.Assign):
        for target in node.targets:
            if isinstance(target,ast.Name) and target.id in ['positions','groups']:settings[target.id]=ast.literal_eval(node.value)
positions=settings['positions']
positions['left'].update({114:420,115:2255,109:2508,101:2528})
badge={}
for side,values in positions.items():
    for n,y in values.items():
        sid=f'S{n:03}';poly=Polygon(ss[sid]['polygon_px']);section=poly.intersection(LineString([(0,y),(2444,y)]))
        if section.geom_type=='MultiLineString':section=max(section.geoms,key=lambda g:g.length)
        lo,_,hi,_=section.bounds;x=lo+20 if side=='left' else hi-20
        if hi-lo<40:x=(lo+hi)/2
        assert poly.contains(Point(x,y)),sid
        badge[sid]=(x,y,side)

FP='/System/Library/Fonts/STHeiti Medium.ttc'
def font(n):return ImageFont.truetype(FP,n)
im=Image.open(P/d['image']['file']).convert('RGB')
canvas=Image.new('RGB',(3404,3260),'#f4f6fa');canvas.paste(im,(480,0));draw=ImageDraw.Draw(canvas)
colors=['#b42318','#175cd3','#027a48','#6938ef','#b54708','#0e7090','#c11574','#344054','#6b5b00']
for m in mapping:
    sid=m['space_id'];s=ss[sid];x,y,side=badge[sid];col=colors[int(m['group'])-1];xx=x+480
    pts=[(a+480,b) for a,b in s['polygon_px']];draw.line(pts+[pts[0]],fill=col,width=3)
    draw.line((xx,y,455 if side=='left' else 2949,y),fill=col,width=2)
    draw.rounded_rectangle((xx-13,y-8,xx+13,y+8),radius=3,fill='white',outline=col,width=1)
    draw.text((xx,y),m['review_id'],font=font(14),anchor='mm',fill=col)
    label=f"{m['review_id']}｜{sid} "+('名称待确认' if s['type']=='unknown' else '已辨认')
    draw.text((22 if side=='left' else 2964,y),label,font=font(17),anchor='lm',fill=col)
draw.rectangle((0,0,canvas.width,68),fill='white')
draw.text((20,18),'26号 补图更新｜固定01—60保留，新增61—63｜11项名称待确认',font=font(27),fill='#182230')
canvas.save(W/'26_补图后名称核对总图.png')
canvas.resize((1702,1630)).save(W/'26_补图后核对总图_预览.jpg',quality=95)

def rel(path):return os.path.relpath(path,P)
def make_crop(number,box,ids,out,review=True):
    x0,y0,x1,y1=box
    source=im.resize((4888,6520)) if number==0 else Image.open(W/f'补图{number:02}_对应原图坐标.jpg')
    crop=source.crop((2*x0,2*y0,2*x1,2*y1));dr=ImageDraw.Draw(crop)
    for sid in ids:
        s=ss[sid];poly=Polygon(s['polygon_px']);visible=poly.intersection(geometry_box(*box))
        if visible.is_empty:continue
        dr.line([((a-x0)*2,(b-y0)*2) for a,b in s['polygon_px']+[s['polygon_px'][0]]],fill='#a4144c',width=3)
        if review and sid in badge:x,y,_=badge[sid];label=mp[sid]['review_id']
        else:
            a,b,c,e=visible.bounds;y=b+min(18,(e-b)/2);seg=visible.intersection(LineString([(0,y),(2444,y)]))
            if seg.geom_type=='MultiLineString':seg=max(seg.geoms,key=lambda g:g.length)
            lo,_,hi,_=seg.bounds;x=(lo+hi)/2 if hi-lo<60 else lo+28;label=sid[1:]
        xx,yy=(x-x0)*2,(y-y0)*2
        dr.rounded_rectangle((xx-26,yy-17,xx+26,yy+17),radius=4,fill='white',outline='#a4144c',width=2)
        dr.text((xx,yy),label,font=font(25),anchor='mm',fill='#a4144c')
    crop.save(out)

# Keep all existing rows and confirmation fields; change only image-read facts and evidence.
uncertain={
 'S019':('财务科／现金业务室','财务或现金业务用房','补图1可辨“财务科／现金…”；后半房名仍模糊，两个候选共用文字依据。把握：中。'),
 'S020':('档案','档案或储藏用房','补图1字形较原图清楚，但两字尚不能可靠排除其他读法；候选共用字形与相邻财务房依据。把握：中。'),
 'S022':('医保稽核室','医保管理用房','补图1可辨医保业务语境，具体中间文字仍有歧义；两个候选共用文字和窗口后台位置依据。把握：中。'),
 'S028':('存款室（保险柜）','清款室（保险柜）','补图1可辨“…款室（保险柜）”，首字仍不够确定；两候选共用该字形线索，不据业务常识确定。把握：中。'),
 'S034':('侧翼门厅','门厅','补图1显示侧翼外门与大厅衔接，正式房名仍未完整读清；两候选共用布局依据。把握：中。'),
 'S055':('门诊采集／接收存放','门诊器材存放','补图2的房名似含“门诊…／…存放”，具体业务词仍有歧义；备选只据存放字样及长条房布局推测。把握：低。'),
 'S066':('暂无可靠候选','诊疗辅助房','补图5的两字仍不能可靠释读，窄房及内部隔断可见；备选仅依片区功能推测，缺乏房间级证据。把握：低。'),
 'S076':('EICU前室','EICU出入口通行区','补图2显示这里是EICU至缓冲S079之间的连续通行分片，没有明确房名；两候选共用连续布局依据。把握：中。'),
 'S096':('办公休息室','工作人员休息室','此次补图未充分覆盖该房，仍沿用原图字形候选；两候选共用桌椅和洗手设施依据。把握：中。'),
 'S111':('配药／药房','取药／药房','补图2、5中“／药房”可辨，前半两字仍不够清楚；两候选共用后半文字和房间设施依据。把握：中。'),
}
lines=[]
for line in md.splitlines():
    if re.match(r'^\| \d{2} \| S\d{3} \|',line):
        cols=[c.strip() for c in line.strip('|').split('|')];sid=cols[1]
        if sid in changes['names_read_from_photos']:
            info=changes['names_read_from_photos'][sid];cols[2]=ss[sid]['name'];cols[3]='—'
            cols[4]=f"补图{info['photo']}文字可辨，已同步JSON/SVG；为图面辨认，不视为用户确认。把握：高。"
            if cols[5] in ['待确认','图面辨认已同步（非用户确认）']:cols[5]='补图辨认已同步（非用户确认）'
        elif sid in uncertain:
            cand,alt,basis=uncertain[sid]
            if cols[5]=='待确认':cols[2:5]=[cand,alt,basis]
        line='| '+' | '.join(cols)+' |'
    lines.append(line)
md='\n'.join(lines)+'\n'
# Regenerate only the overview. The existing table and free-form notes survive intact.
suffix=md[md.index('## 名称与范围核对'):]
intro=(W/'补图后概览.md').read_text()
intro+='\n## 本轮补图更新\n\n本轮依据你提供的6张照片更新26号；原图文件及2444×3260坐标基准不变。照片保存在正式四文件之外，经过方向调整和几何对齐后仅用作判读与核对；不将手机照片坐标直接写入JSON。\n\n'
was_unknown={s['id'] for s in json.loads((W/'补充前四文件/annotation.json').read_text())['spaces'] if s['type']=='unknown'}
resolved=sorted(sid for sid in was_unknown if ss[sid]['type']!='unknown')
intro+=f'**空间与名称：**补入{len(resolved)}项原未定名称；新增S114“中药煎药室”和S115“处置”。S006按补图可见隔墙缩为药品库，另一侧独立保存为S114。原有S编号不变，固定核对01—60保持，新增61—63。\n\n'
intro+='**旧名称纠正：**S014“卫生间”改为“办公室”；S015“值班室”改为“炮制间”；S027“卫生间”改为“值班室”；S074改为“EICU床位区”；S078“卫生间”改为“医生办公”；S098改为“污洗”；S110为“护士站”，S112为“发热门诊门厅”。S081更衣室内的卫生设施按现有整体范围保留，不再拆小隔间。S109原“卫生间”缺乏明确文字和设施支持，撤回为unknown。以上均为补图判读，未写成用户已确认。\n\n'
intro+='**功能范围：**EICU、清创、抢救及相关支持区按急诊范围记录；东侧观察、隔离、治疗、诊室、收费及发热门诊门厅按发热门诊范围记录；挂号收费与医保后台仍为公共服务。\n\n'
intro+='**连通及红点：**中药煎药室—S007沿用原门位P008，仅修正所属空间对；处置S115—S076补入可见门P110。撤回浮在EICU连续通行区的P049，R065保留为无定位的概念连接（布局推断）；撤回更衣间隔墙上的R153/P106及缺乏依据的R148/P101。其余既有R/P/E编号保持，撤回编号不复用。S072—S074及S072—S076为同一EICU内的连续分块；现有S075治疗区内部出入口不继续穷尽。\n\n'
intro+='**仍未完成：**11项名称待确认；K02、K03已由清晰补图判读解决，K01仍待确认。S109为本轮不细究的交通核辅助小间，其用途尚不能确定，不据此推断可达或不可达。\n\n'
intro+='[原图]('+d['image']['file']+') · [具名SVG](标注.svg)\n\n'
intro+='**正向补充照片：**'+' · '.join(f'[补图{i}]({rel(W/f"补图{i:02}_正向.jpg")})' for i in range(1,7))+'。\n\n'
md=intro+suffix
md=md.replace('## 名称与范围核对（固定01—60）','## 名称与范围核对（固定01—60保留，新增61—63）')
md=md.replace('9项已辨认行保留以便纠正，不代表用户已确认。','原已辨认及本轮补图辨认行均保留以便纠正，不代表用户已确认。')
md=md.replace('![26号完整名称核对总图]('+rel(OLD/'26_名称核对总图.png')+')','![26号补图后完整名称核对总图]('+rel(W/'26_补图后名称核对总图.png')+')')
photo_choice=[3,1,1,2,6,2,5,0]
for gi,(title,nums,box) in enumerate(settings['groups'],1):
    ids=[f'S{n:03}' for n in nums]
    if gi==1:ids+=['S114']
    if gi==6:ids+=['S115']
    if gi==8:ids+=['S109']
    out=W/f'{gi:02}_补图名称核对.png'
    make_crop(photo_choice[gi-1],box,ids,out)
    md=md.replace(rel(OLD/f'{gi:02}_{title}_名称局部.png'),rel(out))
    # Pair every updated crop with its unmarked supplemental image.
    raw=W/f'{gi:02}_补图无标记.png';src=im.resize((4888,6520)) if photo_choice[gi-1]==0 else Image.open(W/f'补图{photo_choice[gi-1]:02}_对应原图坐标.jpg');src.crop(tuple(v*2 for v in box)).save(raw)
    md=md.replace(rel(OLD/f'{gi:02}_{title}_无标记.png'),rel(raw))

newsection='### 09｜新增空间与原标签撤回（61—63）\n\n'
for rid,sid,photo,box in [('61','S114',3,(970,350,1380,585)),('62','S115',2,(1380,2160,1560,2310)),('63','S109',2,(1660,2475,1820,2580))]:
    out=W/f'{rid}_{sid}_补图核对.png';make_crop(photo,box,[sid],out)
    newsection+=f'![核对{rid}，{sid}]({rel(out)})\n\n'
    newsection+='| 核对号 | S编号 | 预估名称（可改） | 备选名称 | 依据与把握 | 我的确认／备注 | 核对号（重复） |\n| --- | --- | --- | --- | --- | --- | --- |\n'
    if sid!='S109':name=ss[sid]['name'];alt='—';basis=f'补图{photo}文字及独立边界可辨，已同步JSON/SVG。把握：高。';state='补图辨认已同步（非用户确认）'
    else:name='暂无可靠候选';alt='交通核辅助小间';basis='补图2仅见狭小边界，未见可确认的厕位或原名；撤回原卫生间标签。备选仅依相邻交通核推测，缺乏房间级证据。把握：低。';state='待确认'
    newsection+=f'| {rid} | {sid} | {name} | {alt} | {basis} | {state} | {rid} |\n\n'
md=md.replace('## 连通性关键核对',newsection+'## 连通性关键核对')
# Extra detail for the right end of group 08, which is covered by the photographs.
extra=W/'08B_发热门诊门厅与辅助房.png';make_crop(2,(1665,2475,2005,2720),['S108','S109','S110','S111'],extra)
md=md.replace('### 09｜新增空间与原标签撤回',f'![08B，发热门诊门厅与辅助房补图]({rel(extra)})\n\n### 09｜新增空间与原标签撤回')

# Keep K01 unanswered. Resolve only what the new evidence actually clarifies.
md=md.replace('以下为助手判读，均未作用户确认。','以下为助手判读，均未作用户确认。K01继续待确认；K02、K03已由本轮补图解决，保留原题号与说明供追溯。')
k2=md.index('### K02｜');k3=md.index('### K03｜')
oldk2=md[k2:k3];oldk3=md[k3:]
def confirmed_text(block):
    return block.split('**我的确认／备注：**',1)[1].strip() if '**我的确认／备注：**' in block else ''
answer2=confirmed_text(oldk2);answer3=confirmed_text(oldk3)
if answer2.startswith('待填写'):answer2='无需再填写；补图判读已解决，仍可纠正（非用户确认）'
if answer3.startswith('待填写'):answer3='无需再填写；补图判读已解决，仍可纠正（非用户确认）'
out2=W/'K02_补图EICU出入口.png';make_crop(2,(1190,1638,1810,2425),['S051','S052','S054','S057','S072','S073','S074','S075','S076','S077','S078','S079','S080','S081','S082','S083','S113','S115'],out2,False)
out3=W/'K03_补图发热门诊.png';make_crop(5,(1740,1848,2010,2725),['S083','S084','S085','S086','S087','S088','S089','S090','S091','S092','S107','S110','S111','S112'],out3,False)
md=md[:k2]
md+='### K02｜床位区范围及主要出入口（补图判读已解决）\n\n'
md+=f'![K02补图，房内数字为S编号]({rel(out2)})\n\n'
md+='**核对结论：**补图2明确标“EICU（9床）”，S074内两张床与S072属于同一连续床位区，保留原分块编号，将S074改为EICU床位区。主要出入口按S072—S076—S079—S083记录。S072—S076是连续通行分片，没有P049所指的实体门；已撤回该红点，保留概念关系。S072与S057、S052、S083之间未见新增直接门，不恢复旧跨界连接。\n\n'
md+=f'**我的确认／备注：**{answer2}\n\n'
md+='### K03｜东侧诊室带与底部入口（补图判读已解决）\n\n'
md+=f'![K03补图，房内数字为S编号]({rel(out3)})\n\n'
md+='**核对结论：**补图2、5可辨“发热门诊”标识；观察、隔离、治疗、诊室、挂号收费、护士站及药房后台形成独立诊疗带。S089接S112，由E007发热门诊入口进入；S083与S089之间无清晰直接通口，继续不保存跨房间的直接关系。此结论来自补图，无需为连成一个室内网络另造连接。\n\n'
md+=f'**我的确认／备注：**{answer3}\n'
(P/'标注说明.md').write_text(md)
last_digest.write_text(hashlib.sha256(md.encode()).hexdigest()+'\n')
print('review rows',len(mapping),'pending',[s['id'] for s in d['spaces'] if s['type']=='unknown'])
