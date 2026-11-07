from pathlib import Path
from collections import Counter
import json,os,math,copy,re,hashlib,shutil
from PIL import Image,ImageDraw,ImageFont
from shapely.geometry import Polygon,Point
import pymupdf
P=next(Path('/Users/hushili/Documents/研究-论文写作/大论文/p-平面标注与数据处理/标注试样').glob('28_*'));B=P.parents[1]/'临时核对'/P.name;O=B/'20261105_照片补充';OLD=B/'20261105_首次补充'
d=json.loads((P/'annotation.json').read_text());by={s['id']:s for s in d['spaces']};r=json.loads((OLD/'固定核对映射.json').read_text());rby={a['id']:a for a in r};pending=[a for a in r if by[a['id']]['type']=='unknown'];source=Image.open(P/d['image']['file']).convert('RGB')
for n in [73,76,93,96]:by[f'S{n:03d}']['name']='备用'
(P/'annotation.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
updates={3:('护长／护士','新照片上排两字可见，但第二字仍有歧义；旧“办公室”识读不再采用','中'),13:('辅料／储料','黄色独立房名为两字，后一字为料，前一字仍有印刷纹理干扰','中'),123:('消毒室／准备室','急诊DSA北侧小间原字仍有歧义；不沿用上轮高把握定名','低'),194:('医护用房／医务用房','蓝色小间以医字起首，后一字不清；与更衣相邻只作辅助依据','低'),205:('医护用房／医务用房','东端蓝色小间与西端对应，但不能仅凭重复布局确定原名','低')}
for n,(c,b,cf) in updates.items():rby[f'S{n:03d}'].update(candidate=c,basis=b,confidence=cf)
for n in range(143,149):rby[f'S{n:03d}'].update(candidate='诊室（具体房名待辨）',basis='照片可见该房原文，但倾斜及印刷网纹仍影响完整辨读；不凭家具补专科名',confidence='低')
for a in r:
 s=by[a['id']]
 if s['type']!='unknown':a.update(candidate=s['name'],basis='原图或本轮补充照片直接识读，已同步；照片更正项见本说明',confidence='高')
(O/'固定核对映射.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
# 沿用原图的无交叉左右边栏算法，只展示剩余项；编号不重排。
s=(OLD/'历史取证/99_command.txt').read_text().split("<<'PY'\n",1)[1].split('\nPY\n',1)[0]
s=s.replace('p-写作过程','p-平面标注与数据处理').replace("Path('/tmp/outpatient28-review')",f'Path({str(O)!r})').replace("T/'review-map.json'","T/'剩余核对映射.json'")
(O/'剩余核对映射.json').write_text(json.dumps(pending,ensure_ascii=False,indent=2)+'\n')
s=s.replace("'标注草稿 · 125项待确认 · 完整原图居中 · 黄色框内为本轮核对号'",f"'照片补充后剩余{len(pending)}项；保留原核对号，跳号表示已解决'")
s=s.split("md=['# 28号名称核对表'",1)[0]+"print('pending leaders',len(paths),'crossings',len(cross))"
exec(s,{})
rev=pymupdf.open(O/'28_核对总图.svg');rev[0].get_pixmap(matrix=pymupdf.Matrix(2,2)).save(O/'28_剩余核对总图_高清.png');rev[0].get_pixmap(matrix=pymupdf.Matrix(.5,.5)).save(O/'28_剩余核对总图_预览.png')
def rel(p):return os.path.relpath(p,P)
F='/System/Library/Fonts/STHeiti Medium.ttc'
def badge(dr,x,y,label,size=15):
 font=ImageFont.truetype(F,size);bb=dr.textbbox((0,0),label,font=font);w=bb[2]-bb[0];h=bb[3]-bb[1]
 dr.rounded_rectangle((x-w/2-3,y-h/2-3,x+w/2+3,y+h/2+3),radius=2,fill='white',outline='#b45309',width=2);dr.text((x,y),label,fill='#a33b0b',font=font,anchor='mm')
def original_crop(ids,name,margin=23,number='review'):
 bounds=[Polygon(by[sid]['polygon_px']).bounds for sid in ids];box=(max(0,math.floor(min(b[0] for b in bounds)-margin)),max(0,math.floor(min(b[1] for b in bounds)-margin)),min(source.width,math.ceil(max(b[2] for b in bounds)+margin)),min(source.height,math.ceil(max(b[3] for b in bounds)+margin)));sc=2.5
 im=source.crop(box).resize((round((box[2]-box[0])*sc),round((box[3]-box[1])*sc)));dr=ImageDraw.Draw(im)
 for sid in ids:
  p=Polygon(by[sid]['polygon_px']);pts=[((x-box[0])*sc,(y-box[1])*sc) for x,y in by[sid]['polygon_px']];dr.line(pts+[pts[0]],fill='#bd4c19',width=3)
  x0,y0,x1,y1=p.bounds;x=x0+min(16,(x1-x0)/2);y=y0+min(12,(y1-y0)/2)
  if not p.contains(Point(x,y)):pt=p.representative_point();x,y=pt.x,pt.y
  badge(dr,(x-box[0])*sc,(y-box[1])*sc,rby[sid]['number'] if number=='review' else sid[1:],round(12*sc))
 im.save(O/name);return O/name
# 待确认原图局部按旧片区与旧编号组织；完整照片另存，不改原图坐标。
groups=[]
for group in dict.fromkeys(a['group'] for a in pending):
 rr=[a for a in pending if a['group']==group]
 for j in range(0,len(rr),6):groups.append((group,rr[j:j+6]))
# 在补充照片上给少数仍需辨字的空间加原核对号，位置人工对应。
photo_specs=[('供应字形',2,(680,985,1430,1330),[(3,1235,1000),(13,980,1225)]),('急诊字形',5,(1240,1365,1960,1840),[(123,1560,1397),(143,1305,1784),(144,1369,1803),(145,1430,1812),(146,1492,1812),(147,1552,1808),(148,1615,1787)]),('门诊南排字形',6,(1560,1750,2770,1940),[(194,1910,1880),(205,2660,1870)])]
photo_paths={}
for tag,n,box,items in photo_specs:
 im=Image.open(O/f'照片_{n:02d}_转正.png').crop(box);dr=ImageDraw.Draw(im)
 for sid,x,y in items:badge(dr,x-box[0],y-box[1],rby[f'S{sid:03d}']['number'],13)
 im=im.resize((im.width*2,im.height*2));p=O/(tag+'_房内编号.png');im.save(p)
 for sid,_,_ in items:photo_paths[f'S{sid:03d}']=p
c=Counter(x['type'] for x in d['relations']);op=sum(len(x.get('openings',[])) for x in d['relations']);nr=sum(bool(x.get('openings')) for x in d['relations']);coarse=[f'S{n:03d}' for n in list(range(165,189))+list(range(196,205))]
assert len(coarse)==33
md=['# 28号空间与连通性补充','',f'**标注草稿／未完成：{len(pending)}个名称待确认，其中33个可用一次统一命名处理；K01、K02两组关键疑点待确认。**','',
'本轮依据你补充的6张照片，新增识读61项、纠正7处旧名称；S123因新照片仍有字形歧义退回unknown。待确认名称从104项净降至44项。所有S编号、P编号和原核对号01—127保持；已解决项退出待填区，不重排剩余编号。未作答不视为接受预估名称。','',
f'**当前规模：**206个空间、{len(d["relations"])}条关系（人员可达{c["access"]}、服务{c["service"]}、共墙{c["shared_wall"]}、外部入口{c["entrance"]}）；{op}个已定位开口，对应{nr}条人员边。清晰开口保留，布局推断不编造P点。','',
'**重要更正：**S054为登记室，S092为示教室，S108为银行，S118为抢救室，S126为主任办公室，S128为DSA检查室；S129为DSA控制室。原P046误画在DSA南侧连续墙上，已随原R224撤回，编号不复用。S003原“办公室”更正为照片所写“护长”，S013识读为辅料间；S123原“消毒室”的高把握识读不再沿用。','',
'[原图]('+d['image']['file']+')｜[标注SVG](标注.svg)','',
'## 先处理这一项，可一次减少33项','',
'照片右侧24个成排小间S165—S188及南排9个小间S196—S204未写具体房名，家具与门诊布局支持“诊室”的粗名称。照片本身不能确定具体专科。','',
'**问题：**是否接受上述33项统一记录为“诊室”（type=consultation），分别保留原S编号和轮廓？','',
'**我的确认／备注（33项统一名称）：**待填写（可填“接受，统一为诊室”；不必逐行写33次）','',
'## 剩余核对总图','',
'![剩余待确认项，保留原号]('+rel(O/'28_剩余核对总图_高清.png')+')','',
'## 少量字形、空间属性与成排小间','',
'可改“预估名称（可改）”后填“已确认”，或直接在确认栏填写实际名称。33个成排小间可只回答上方一次统一命名问题。','']
used_photos=set()
for idx,(group,rr) in enumerate(groups,1):
 ids=[a['id'] for a in rr];p=original_crop(ids,f'剩余局部_{idx:02d}_{rr[0]["number"]}-{rr[-1]["number"]}.png')
 md+=['### '+rr[0]['number']+'—'+rr[-1]['number']+'｜'+group,'','![原图房内为原核对号]('+rel(p)+')','']
 for sid in ids:
  pp=photo_paths.get(sid)
  if pp and pp not in used_photos:md+=['![补充照片上的同号房间]('+rel(pp)+')',''];used_photos.add(pp)
 md+=['| 核对号 | S编号 | 预估名称（可改） | 备选名称 | 依据与把握 | 我的确认／备注 | 核对号（重复） |','| --- | --- | --- | --- | --- | --- | --- |']
 for a in rr:
  cand=a['candidate'];alts='—'
  if '／' in cand:cand,alts=cand.split('／',1)
  status='待统一命名（见上方一次确认）' if a['id'] in coarse else '待确认'
  md.append(f'| {a["number"]} | {a["id"]} | {cand} | {alts} | {a["basis"]}；候选共用此依据。把握：{a["confidence"]}。 | {status} | {a["number"]} |')
 md.append('')
md+=['## 关键空间属性与连通核对','']
qpath=original_crop(['S035','S036','S037','S038','S039','S040','S041','S042'],'K01_空间属性.png',23,'space')
md+=['### K01｜医院街两处白色区域','','![房内为S编号数字]('+rel(qpath)+')','','**问题：**S035、S040分别是庭院／挑空，还是可使用的室内大厅？','','**我的判断：**补充照片仍未写出用途，保留此关键问题。当前暂计室内；确认为庭院／挑空后设为courtyard、open_space，不计室内面积，不再追问是否有顶。','','**我的确认／备注：**待填写（请分别说明S035、S040）','']
qpath=original_crop(['S001','S009','S010','S012','S013','S017','S018','S024','S027'],'K02_供应人员通行.png',25,'space')
md+=['### K02｜中心供应打包区的人员入口','','![房内为S编号数字]('+rel(qpath)+')','','**问题：**打包区S001是否经内部通道S010西端的更衣过渡部分进入？若不是，请指出实际人员入口所连空间。','','**我的判断：**照片已能确定S009=清洗消毒、S001=打包、S017=无菌物品库，原“这三个区各叫什么”无需再问。打包经灭菌设备S012进入无菌库的箭头为物品流程，不能当人员门。S001↔S013有可见门，S017↔S018、S017↔S024及S024↔S027分别已按可见门或开放布局记录；S001主入口仍有更衣过渡小区的粒度歧义，暂不补S001↔S010。','','**我的确认／备注：**待填写','',
'### K03｜MR入口已转为自主布局判断，无需重复填写','','照片可见S047控制室朝S044患者通道开门，而两个MR检查室的北墙未见直接门。移除旧S046↔S044、S048↔S044；保留S047↔S044，并补S046↔S047、S048↔S047为**布局推断**，不定位推断的内部小门。这是助手判断，不写成用户确认。','',
'## 已同步名称与识读记录','',
'<details>','<summary>展开已解决的原核对行（保留原号与填写字段）</summary>','',
'| 核对号 | S编号 | 预估名称（可改） | 备选名称 | 依据与把握 | 我的确认／备注 | 核对号（重复） |','| --- | --- | --- | --- | --- | --- | --- |']
oldrows={}
for l in (O/'照片同步前四文件与用户填写备份/标注说明.md').read_text().splitlines():
 cells=[x.strip() for x in l.split('|')]
 if len(cells)==9 and cells[1].isdigit():oldrows[cells[2]]=cells
for a in r:
 sp=by[a['id']]
 if sp['type']=='unknown':continue
 old=oldrows[a['id']];status=old[6] if old[6] not in ['待确认','图面识读（可改）'] else '图面识读（可改）'
 md.append(f'| {a["number"]} | {a["id"]} | {sp["name"]} | — | 原图／补充照片识读，已同步。把握：高。 | {status} | {a["number"]} |')
md+=['','</details>','','**不在原127项中的更正：**S054登记室、S092示教室、S108银行、S118抢救室、S126主任办公室、S128 DSA检查室、S003护长；同样已写入JSON与SVG。','',
'## 本轮连通处理与范围','','新增门位按原图坐标逐个回看定位；照片只作判读证据，不把照片像素直接写入JSON。P001—P081中除撤回P046外均保留，新增P082—P091。原R027水处理间朝向、R113准备室端点、R115电梯厅端点、R116护士站端点以及MR两条直接患者通道边已修正，未重排其他R编号。','','**布局推断：**S046↔S047、S048↔S047；S017↔S024（发放连续组织）；S116↔S110（门诊电梯厅朝大厅开放）；S114↔S115（护士站与准备室工作联系中的人员通路）；S128↔S129（DSA经控制室组织人员进入）。均未虚构内部精确门位。S114↔S112仅记服务联系。','','**本轮无需细究：**管井、小辅助间、柜台后小门及交通核内部路线。其他影像室双侧旧边、商铺外廊接口仍待后续逐条复核；保留旧边不等于本轮已确认全部连通。不得凭服务窗口或共墙造人员边。','','**交付状态：**原图、JSON、SVG、MD四文件保留；照片、核对图、固定映射及备份均存放在样本外的持久临时核对目录。当前仍有名称和K01/K02未解决，不能宣称整张图完成。']
current=(P/'标注说明.md').read_bytes();backup=(O/'照片同步前四文件与用户填写备份/标注说明.md').read_bytes()
assert hashlib.sha256(current).hexdigest()=='e1322d124e6f86e3a8471609be38a6835e6027719f9fbb726b3aa6feb4e73b9e','MD在本轮期间有新修改，需先合并，不覆盖'
(P/'标注说明.md').write_text('\n'.join(md)+'\n')
shutil.copy2('/tmp/sync28_photos.py',O/'照片同步_已执行勿重复.py');shutil.copy2('/tmp/review28_photos.py',O/'更新核对材料.py');shutil.copy2('/tmp/ocr28.swift',O/'本地OCR辅助.swift')
print('pending rows',len(pending),'archive rows',127-len(pending),'pending groups',len(groups),'photo panels',len(used_photos))
