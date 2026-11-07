from pathlib import Path
import json,re,os,math,copy
from collections import Counter
from PIL import Image,ImageDraw,ImageFont
from shapely.geometry import Polygon,Point,LineString
import pymupdf
P=Path('/Users/hushili/Documents/研究-论文写作/大论文/p-平面标注与数据处理/标注试样/28_广东省人民医院心脑血管专科医院一期项目');O=P.parents[1]/'临时核对'/P.name/'20261105_首次补充'
d=json.loads((P/'annotation.json').read_text());by={s['id']:s for s in d['spaces']};r=json.loads((O/'固定核对映射.json').read_text());im=Image.open(P/d['image']['file']).convert('RGB')
for a in r:
 if by[a['id']]['type']!='unknown':a.update(candidate=by[a['id']]['name'],basis='本轮放大原图，名称可辨；已同步核心数据',confidence='高')
 if a['candidate']=='工作人员用房':a.update(candidate='暂无可靠候选',basis='房名模糊，缺乏房间级证据，不能仅凭供应区位置确定用途',confidence='低')
 if a['confidence']=='无依据':a['confidence']='低'
(O/'固定核对映射.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
# 复用本图历史已审计的左右边栏总图算法，改用持久目录。
s=(O/'历史取证/99_command.txt').read_text().split("<<'PY'\n",1)[1].split('\nPY\n',1)[0]
s=s.replace('p-写作过程','p-平面标注与数据处理').replace("Path('/tmp/outpatient28-review')",f'Path({str(O)!r})').replace("T/'review-map.json'","T/'固定核对映射.json'")
s=s.replace("f'标注草稿 · {len(r)}项待确认", "f'标注草稿 · {len(r)}项固定核对号")
s=s.replace("'标注草稿 · 125项待确认 · 完整原图居中 · 黄色框内为本轮核对号'", "f'固定核对号01—127，保留已识读行；当前104项待确认 · 完整原图居中'")
s=s.split("md=['# 28号名称核对表'",1)[0]+"print('leaders',len(paths),'crossings',len(cross))"
exec(s,{})
svg=pymupdf.open(O/'28_核对总图.svg');svg[0].get_pixmap(matrix=pymupdf.Matrix(2,2)).save(O/'28_核对总图_高清.png');svg[0].get_pixmap(matrix=pymupdf.Matrix(.42,.42)).save(O/'28_核对总图_预览.png')
FONT='/System/Library/Fonts/STHeiti Medium.ttc'
def font(n):return ImageFont.truetype(FONT,round(n))
colors=['#b45309','#7c3aed','#0369a1','#047857','#be185d']
def crop(box,items,path,mode='review'):
 scale=2.4;x0,y0,x1,y1=box;out=im.crop(box).resize((round((x1-x0)*scale),round((y1-y0)*scale)))
 dr=ImageDraw.Draw(out)
 for j,item in enumerate(items):
  sid=item['id'];p=Polygon(by[sid]['polygon_px']);c=colors[j%len(colors)];pts=[((x-x0)*scale,(y-y0)*scale) for x,y in by[sid]['polygon_px']]
  dr.line(pts+[pts[0]],fill=c,width=3)
  txt=item['number'] if mode=='review' else sid[1:]
  # 逐轮廓选择内部上角的数字徽标，原图房名多位于中央。
  bx,yy,bw,bh=p.bounds;cx=bx+min(16,(bw-bx)/2);cy=yy+min(12,(bh-yy)/2)
  if not p.contains(Point(cx,cy)):q=p.representative_point();cx,cy=q.x,q.y
  xx=(cx-x0)*scale;yy=(cy-y0)*scale;f=font(12*scale);bb=dr.textbbox((0,0),txt,font=f);tw=bb[2]-bb[0];th=bb[3]-bb[1]
  dr.rounded_rectangle((xx-tw/2-4,yy-th/2-4,xx+tw/2+4,yy+th/2+4),radius=4,fill='white',outline=c,width=2)
  dr.text((xx,yy),txt,fill=c,font=f,anchor='mm')
 out.save(path)
def relpath(path):return os.path.relpath(path,P)
# 每片区按原顺序分小组，所有127行包括已识读行一并保留。
groups=[]
for group in dict.fromkeys(a['group'] for a in r):
 rr=[a for a in r if a['group']==group]
 for j in range(0,len(rr),6):groups.append((group,rr[j:j+6]))
md=['# 28号空间与连通性补充','', '**标注草稿／未完成：104个名称待确认，3组关键空间属性／连通疑点待确认。**','',
'本轮沿用S001—S206及原核对号01—127，不重排已有映射。已自主识读23个名称；未确认项在JSON中继续为unknown。可改“预估名称（可改）”并填“已确认”，也可直接在“我的确认／备注”填实际名称。聊天回复可用 `核对号=名称` 或 `S编号=名称`。本轮识读行保留供复核，标记为“图面识读”，不记成用户确认。','',
'[原图]('+d['image']['file']+')｜[标注SVG](标注.svg)','',
'**当前规模：**206个空间、235条关系（199条人员可达、6条服务、20条共墙、10个外部入口）；81个门洞／开口红点，对应80条人员可达关系；119条人员可达暂不带门位，其中包含尚待专项复核的旧草稿边。未记关系不表示不相通。','',
'**本轮修正：**原R117把急诊内通道S131直接连到外环大厅S141，改为S113↔S131的北侧连续开口；原R147把药房S119连到S113，改为S119↔S141的南侧门。保留其余R编号，新增R222—R227。S112↔S140、S128↔S141、S009↔S016及S156↔S189按图上可辨门补充。','',
'**面积口径：**已知庭院S163、S164不计室内面积；S035、S040用途未定，待K01确认后处理。','',
'## 固定编号总图','', '总图完整保留原图，左右边栏与房内核对号对应；同侧按编号自上而下。高清图可打开原尺寸，以下各组局部图与填写表相邻。','',
'![28号固定编号总图]('+relpath(O/'28_核对总图_高清.png')+')','', '## 名称与空间范围核对','']
for n,(group,rr) in enumerate(groups,1):
 bounds=[Polygon(by[a['id']]['polygon_px']).bounds for a in rr];box=(max(0,math.floor(min(b[0] for b in bounds)-26)),max(0,math.floor(min(b[1] for b in bounds)-26)),min(im.width,math.ceil(max(b[2] for b in bounds)+26)),min(im.height,math.ceil(max(b[3] for b in bounds)+26)))
 name=f'局部_{n:02d}_核对{rr[0]["number"]}-{rr[-1]["number"]}.png';crop(box,rr,O/name)
 md+=['### '+rr[0]['number']+'—'+rr[-1]['number']+'｜'+group,'','![本组房内数字]('+relpath(O/name)+')','', '| 核对号 | S编号 | 预估名称（可改） | 备选名称 | 依据与把握 | 我的确认／备注 | 核对号（重复） |','| --- | --- | --- | --- | --- | --- | --- |']
 for a in rr:
  sp=by[a['id']];known=sp['type']!='unknown';cand=sp['name'] if known else a['candidate'];alts='—';basis=('本轮放大原图，房名可辨；把握：高。' if known else a['basis']+'；候选共用上述依据，现有证据不足以定名。把握：'+a['confidence']+'。');status='图面识读（可改）' if known else '待确认'
  if not known and '/' in cand:cand,alts=cand.split('/',1)
  if not known and '／' in cand:cand,alts=cand.split('／',1)
  md.append(f'| {a["number"]} | {a["id"]} | {cand} | {alts} | {basis} | {status} | {a["number"]} |')
 md.append('')
questions=[
 ('K01','医院街两个白色区域',(1200,850,1590,1855),[35,36,37,38,39,40,41,42], 'S035、S040分别是庭院／挑空空间，还是可使用的室内大厅？','倾向庭院／挑空，但图内未写名称，不能仅凭留白定性；确认后统一按庭院口径排除面积。请分别填写S035、S040用途。'),
 ('K02','中心供应主要工作区',(140,535,885,880),[1,9,10,12,13,16,17,18,19,24,27], 'S009、S001、S017三个主要工作区是否依次相通？它们与南侧通道S027分别是否直接相通？','S009左侧有清晰门连接S016；S001与S017之间隔着设备带S012，图示流向不能证明人员可直接穿行。暂不补这三个区之间的人员边，只保留已看清门的连接。可同时说明三个大区名称。'),
 ('K03','MR主要检查区的人员入口',(440,1225,735,1525),[44,46,47,48,55,58,59,60,61,69], 'MR检查室S046、S048是否直接向北侧患者通道S044开门，还是经控制室S047进入？','旧稿已记S046／S047／S048↔S044，但本图MR北侧开口不够清楚。这三条旧边保留为草稿待核，未给它们编造门位；请确认患者进入两个MR检查室的实际连接。')]
md+=['## 关键空间属性与连通核对','','以下只问会改变主要功能区可达性或面积口径的问题。每题可填写“同意”或实际空间关系；自动判断不视为用户确认。','']
for k,title,box,ids,question,judgment in questions:
 items=[dict(id=f'S{n:03d}') for n in ids];name=k+'_连通局部.png';crop(box,items,O/name,'space')
 raw=O/(k+'_无标记原图.png');im.crop(box).resize((round((box[2]-box[0])*2.4),round((box[3]-box[1])*2.4))).save(raw)
 md+=['### '+k+'｜'+title,'','![房内为S编号数字部分]('+relpath(O/name)+')','','[同范围无标记原图]('+relpath(raw)+')','','**问题：**'+question,'','**我的判断：**'+judgment,'','**我的确认／备注：**待填写','']
md+=['## 连通复核范围与后续','','东侧门诊24处门凹口已逐项定位；急诊修正两条端点不符的旧边，并补充主房间入口。影像已补本轮可辨的工作人员侧门和主接口；MR的K03仍待确认。**尚未宣称全图连通性完成**：其他影像室双侧旧边、南排小间及外廊与商业接口将在空间名称／属性明确后继续逐条核实，不能把保留旧边理解为本轮已验证。','','本轮不细究管井、小辅助间内部路线和柜台后的零碎小门；无可辨门位的连续区域可只记概念access。商业S105—S108朝南侧外廊，暂不凭共墙连接影像工作人员通道S103；未补外廊节点及商铺人员边。服务柜台继续只记service，不由此生成通行红点。','','所有图片、固定映射、变更记录与四文件备份位于样本外的持久“临时核对”目录；原图未修改。正式校验仍会因104个unknown返回未完成状态。']
(P/'标注说明.md').write_text('\n'.join(md)+'\n')
print('groups',len(groups),'rows',len(r),'unknown',sum(s['type']=='unknown' for s in d['spaces']))
