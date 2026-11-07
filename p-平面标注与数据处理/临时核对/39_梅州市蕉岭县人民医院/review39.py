from pathlib import Path
import json,math,random
from PIL import Image,ImageDraw,ImageFont,ImageStat
from shapely.geometry import Polygon,LineString,box
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]/'标注试样'/'39_梅州市蕉岭县人民医院'
D=json.loads((ROOT/'annotation.json').read_text());state=json.loads((OUT/'review_state.json').read_text())
spaces={s['id']:s for s in D['spaces']}
M=json.loads((OUT/'review_mapping.json').read_text())
for m in M:
 m['polygon']=[(y,2424-x) for x,y in spaces[m['id']]['polygon_px']]
 m['confidence']='低'
SRC=Image.open(OUT/'原图转正.png').convert('RGB')
FONT='/System/Library/Fonts/STHeiti Medium.ttc'
COL={'A':'#0f766e','B':'#7c3aed','C':'#c2410c','D':'#0369a1','E':'#a21caf','F':'#166534'}
def f(sz):return ImageFont.truetype(FONT,sz)
def badge_point(poly):
 # 在轮廓内放号，优先选留白，避开原文字和门洞。
 minx,miny,maxx,maxy=poly.bounds;c=[]
 for tx in (.18,.35,.5,.65,.82):
  for ty in (.18,.35,.5,.65,.82):
   x=minx+(maxx-minx)*tx;y=miny+(maxy-miny)*ty
   if poly.covers(box(x-13,y-10,x+13,y+10)):
    gr=SRC.crop((int(x-13),int(y-10),int(x+13),int(y+10))).convert('L')
    ink=255-ImageStat.Stat(gr).mean[0];c.append((ink+abs(tx-.5)*3+abs(ty-.5)*3,x,y))
 if not c:
  p=poly.representative_point();return(p.x,p.y)
 return min(c)[1:]
def marked(bounds,items,path,related=()):
 x0,y0,x1,y1=bounds;scale=2
 im=SRC.crop(bounds).resize((int((x1-x0)*scale),int((y1-y0)*scale)))
 d=ImageDraw.Draw(im)
 for s in related:
  poly=Polygon([(y,2424-x) for x,y in s['polygon_px']]);pt=poly.representative_point()
  if x0<pt.x<x1 and y0<pt.y<y1:
   xx=(pt.x-x0)*scale;yy=(pt.y-y0)*scale
   d.rounded_rectangle((xx-25,yy-19,xx+25,yy+19),radius=5,fill='white',outline='#334155',width=2)
   d.text((xx,yy),s['id'][1:],font=f(24),anchor='mm',fill='#334155')
 for m in items:
  col=COL[m['group']];poly=Polygon(m['polygon']);pts=[((x-x0)*scale,(y-y0)*scale) for x,y in m['polygon']]
  d.line(pts+[pts[0]],fill=col,width=3)
  x,y=badge_point(poly);xx=(x-x0)*scale;yy=(y-y0)*scale
  d.rounded_rectangle((xx-24,yy-18,xx+24,yy+18),radius=5,fill=col,outline='white',width=2)
  d.text((xx,yy),m['review'],font=f(25),anchor='mm',fill='white')
 im.save(path)
# 总图沿用历史排版算法及原核对顺序，单独优化引线，房内数字与引线锚点分离。
code=(OUT/'历史取证/review.py').read_text()
code=code[code.index('def iso('):code.index('reports=[make(')]
code=code.replace('range(22000)','range(12000)')
code=code.replace("for p,y in zip(pp,ys):p['ly']=max(255,min(h-140,y))","if full and side=='left':\n            for k in range(6,len(ys)):ys[k]=max(ys[k],1940+(k-6)*112)\n        for p,y in zip(pp,ys):p['ly']=max(255,min(h-140,y))")
code=code.replace("if new>len(bad) or (new==len(bad) and rng.random()<.15):", "if new>len(bad):")
code=code.replace("ax,ay=p['anchor'];rr=20", "px,py=badge_point(p['poly']);ax=margin+(px-x0)*scale;ay=top+(py-y0)*scale;rr=18")
# 狭小单元用矩形徽标并保持全在轮廓内。
code=code.replace("d.ellipse((ax-rr,ay-rr,ax+rr,ay+rr),fill=col,outline='white',width=2)","d.rounded_rectangle((ax-24,ay-18,ax+24,ay+18),radius=5,fill=col,outline='white',width=2)")
ns=dict(OUT=OUT,TMP=OUT,pending=M,src=SRC,FONT=FONT,colors=COL,names={'A':'会议片区','B':'后勤片区','C':'急诊片区','D':'影像放射','E':'超声药房','F':'入口儿科'},Image=Image,ImageDraw=ImageDraw,ImageFont=ImageFont,Polygon=Polygon,LineString=LineString,json=json,math=math,random=random,badge_point=badge_point)
exec(code,ns)
report=ns['make'](M,(0,0,3104,2424),'39_名称核对总图',2,True)
(OUT/'总图引线检查.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
im=Image.open(OUT/'39_名称核对总图.png');im.thumbnail((1800,1800));im.save(OUT/'名称总图预览.png')
groups=[
 ('01—03｜会议区北侧',1,3,(180,375,790,575)),
 ('04—06｜会议区舞台侧',4,6,(530,490,790,815)),
 ('07—11｜会议区南侧',7,11,(180,815,700,965)),
 ('12｜后勤入口旁',12,12,(755,425,1045,620)),
 ('13—14｜后勤北侧',13,14,(1285,445,1735,625)),
 ('15—17｜后勤南侧西部',15,17,(760,580,1515,740)),
 ('18—19｜后勤南侧东部',18,19,(1290,575,1735,885)),
 ('20—23｜急诊北侧',20,23,(175,925,790,1060)),
 ('24—25｜抢救配套',24,25,(270,1025,700,1155)),
 ('26｜急诊诊疗房间组',26,26,(170,1120,480,1380)),
 ('27｜急诊庭院东侧',27,27,(560,1215,790,1380)),
 ('28｜输液留观配套',28,28,(285,1340,700,1540)),
 ('29｜急诊药房东侧',29,29,(290,1535,790,1705)),
 ('30—32｜放射区南侧',30,32,(760,1110,1450,1260)),
 ('33—35｜医技东侧',33,35,(1295,1220,1450,1705)),
 ('36｜西药房东端',36,36,(1220,1535,1390,1705)),
 ('37｜候药区南侧',37,37,(750,1595,950,1710)),
 ('38｜门诊西侧小间',38,38,(305,1650,500,1800)),
 ('39｜大厅庭院转角',39,39,(735,1760,920,1945)),
]
sections=[]
for idx,(title,lo,hi,b) in enumerate(groups,1):
 items=[m for m in M if lo<=int(m['review'])<=hi];fn=f'名称_{lo:02d}-{hi:02d}.png';marked(b,items,OUT/fn)
 sections.append(dict(title=title,items=items,file=fn))
# 连通题房内显示S编号，K号只作题号。
for k,b,ids in [('K01',(1275,435,1735,775),[24,25,26,27,31,34,35,36]),('K02',(175,375,835,825),[1,2,3,4,5,6,7,8,9,19,28,40])]:
 marked(b,[],OUT/f'{k}_连通局部.png',[spaces[f'S{i:03d}'] for i in ids])
# 名称候选原话保存；不把两个仅靠片区推测的候选写成确定事实。
md=['# 39 梅州市蕉岭县人民医院｜标注草稿','',
 '本轮已补充主要连通关系与可见开口。仍有 **39项名称、2项关键连通** 待确认，尚未定稿。','',
 '沿用S001—S107及原名称核对号01—39；107为空间/功能块数，并非独立房间数。庭院、地下车库上空及绿化不计室内面积。','',
 '<!-- annotation:summary:start -->','<!-- annotation:summary:end -->','',
 '## 名称核对','',
 '按原固定核对号填写；可以修改“预估名称”，再把确认栏改为“已确认”，也可直接填写实际名称。候选均未写入JSON。','',
 '![39号完整原图名称核对总图](../../临时核对/39_梅州市蕉岭县人民医院/39_名称核对总图.png)','']
base='../../临时核对/39_梅州市蕉岭县人民医院/'
for sec in sections:
 md += ['### '+sec['title'],'',f"![{sec['title']}]({base}{sec['file']})",'',
 '| 核对号 | S编号 | 预估名称（可改） | 备选名称 | 依据与把握 | 我的确认／备注 | 核对号（重复） |',
 '| --- | --- | --- | --- | --- | --- | --- |']
 for m in sec['items']:
  candidates=m['candidates'];why=m['why']
  extra='两候选共用此图面/片区依据，未见可读房名，不能确定具体用途。'
  if m['id']=='S056':extra='原图图例有12“发热门诊”，本块未读到清晰12号，不能据图例顺序确认。'
  if '卫生间' not in candidates and not any(w in why for w in ['洁具','隔间']):extra+='候选仅供核对，不视为确认。'
  md.append(f"| {m['review']} | {m['id']} | {candidates[0]} | {'／'.join(candidates[1:])} | {why}；{extra}把握：{m['confidence']}。 | 待确认 | {m['review']} |")
 md+=['']
md+=['## 关键连通核对','']
for item in state['connectivity_items']:
 k=item['review_id'];md += ['### '+k,'',f'![{k}：房内数字为稳定S号后三位]({base}{k}_连通局部.png)','',
 '**问题：**'+item['question'],'', '**我的判断：**'+item['reason']+' 现阶段不补该连接。','',
 '**我的确认／备注：**待填写（填写“相通”、实际连接空间，或说明不相通）。','']
(ROOT/'标注说明.md').write_text('\n'.join(md)+'\n')
print('MD名称表、局部图、两项关键连通题已生成')
