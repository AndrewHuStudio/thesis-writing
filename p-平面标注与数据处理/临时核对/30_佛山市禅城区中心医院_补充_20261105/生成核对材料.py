from pathlib import Path
import json,re,os
from PIL import Image,ImageDraw,ImageFont
from shapely.geometry import Polygon,Point,LineString
T=Path(__file__).parent;R=T.parent.parent/'标注试样/30_佛山市禅城区中心医院'
data=json.loads((R/'annotation.json').read_text());qs=json.loads((T/'固定核对映射.json').read_text())
# Reuse the historical overview layout, preserving its original numbering and geometry.
s=(T/'历史取证/旧核对_只读.py').read_text().split('# Three spatial zoom sheets')[0]
s=s.replace("T=Path('/tmp/outpatient30-review');R=Path('/Users/hushili/Documents/研究-论文写作/大论文/p-写作过程/标注试样/30_佛山市禅城区中心医院')",'T=Path(__file__).parent;R=T.parent.parent/\'标注试样/30_佛山市禅城区中心医院\'')
s=s.replace("T/'review-map.json'","T/'固定核对映射.json'").replace('33项待确认','31项待确认').replace('len(qs)==33','len(qs)==31').replace("len({q['number'] for q in qs})==33","len({q['number'] for q in qs})==31")
exec(compile(s,str(T/'历史总图排版'), 'exec'))
base=Image.open(R/data['image']['file']).convert('RGB')
FONT='/System/Library/Fonts/STHeiti Medium.ttc'
def ft(n):return ImageFont.truetype(FONT,n)
# Small neighboring bands keep text legible beside each answer table.
groups=[('01_北排与影像北侧',list(range(1,8)),(1180,340,2150,605)),('02_公共服务北段',[8,10,15],(565,495,925,990)),('03_医护中排',[9,12,13,14],(1710,495,2150,835)),('04_DSA中心与影像中段',[11,18],(1320,630,1745,1045)),('05_出入院手续',[16,17,19,20,21,25],(790,800,1100,1340)),('06_放射南侧',[22,23,24,26,27],(1190,1080,1880,1295)),('07_庭院与平台',[28,29,30],(1180,1260,1845,1510)),('08_输液支持',[31],(1190,1490,1510,1760))]
meta=[]
for name,nums,crop in groups:
 l,t,r,b=crop;scale=3
 im=base.crop(crop).resize(((r-l)*scale,(b-t)*scale));dr=ImageDraw.Draw(im);badges=[]
 selected=[q for q in qs if int(q['number']) in nums]
 for q in selected:
  p=Polygon(q['polygon_px']);pts=[((x-l)*scale,(y-t)*scale) for x,y in q['polygon_px']];dr.line(pts+[pts[0]],fill='#005ab5',width=5)
  # Small interior badge near the corner leaves the printed room name exposed.
  a,c,e,f=p.bounds;x=a+min(18,(e-a)/2);y=c+min(18,(f-c)/2)
  if not p.contains(Point(x,y)):x,y=p.representative_point().coords[0]
  xx=(x-l)*scale;yy=(y-t)*scale
  badges.append((yy,im.width-xx,q['number']))
 # Rotation improves the source text's reading direction; original files and coordinates stay unchanged.
 im=im.rotate(90,expand=True);dr=ImageDraw.Draw(im)
 for xx,yy,num in badges:
  dr.rounded_rectangle((xx-27,yy-23,xx+27,yy+23),radius=5,fill='white',outline='#005ab5',width=3)
  dr.text((xx,yy),num,font=ft(37),fill='#005ab5',anchor='mm')
 head=Image.new('RGB',(im.width,im.height+95),'white');head.paste(im,(0,95));hd=ImageDraw.Draw(head)
 hd.text((20,15),name+'｜核对 '+','.join(q['number'] for q in selected),font=ft(28),fill='#18314c')
 hd.text((20,53),'本页已转正；编号与总图一致，原图未修改。',font=ft(24),fill='#586878')
 head.save(T/(name+'.png'))
 meta.append((name,selected))
(T/'局部分组.json').write_text(json.dumps([{'file':n+'.png','numbers':[q['number'] for q in ss]} for n,ss in meta],ensure_ascii=False,indent=2))
# All numbered target rooms have one and only one local illustration.
assert sorted(n for _,ss in meta for n in [int(q['number']) for q in ss])==list(range(1,32))
# Evidence crops for the main passage review use stable S IDs inside each relevant space.
for name,crop,ids in [('K01_庭院通廊',(1180,1190,1845,1530),['S063','S070','S071','S072','S073','S074','S075']),('K02_输液支持',(1190,1490,1745,1770),['S075','S083','S084','S085','S088'])]:
 l,t,r,b=crop;im=base.crop(crop).resize(((r-l)*3,(b-t)*3));dr=ImageDraw.Draw(im);badges=[]
 for sid in ids:
  sp=next(s for s in data['spaces'] if s['id']==sid);p=Polygon(sp['polygon_px']);a,c,e,f=p.bounds
  x=a+min(22,(e-a)/2);y=c+min(22,(f-c)/2)
  if not p.contains(Point(x,y)):x,y=p.representative_point().coords[0]
  x=(x-l)*3;y=(y-t)*3
  badges.append((y,im.width-x,sid))
 im=im.rotate(90,expand=True);dr=ImageDraw.Draw(im)
 for x,y,sid in badges:
  dr.rounded_rectangle((x-38,y-22,x+38,y+22),radius=4,fill='white',outline='#ac2450',width=3)
  dr.text((x,y),sid,font=ft(26),fill='#ac2450',anchor='mm')
 im.save(T/(name+'.png'))
# Keep the existing narrative and add an editable section once.
old=(R/'标注说明.md').read_text().split('\n## 本轮空间名称与范围核对')[0]
md=(T/'本轮概览.md').read_text().replace('# 平面标注概览','# 30_佛山市禅城区中心医院｜一层标注草稿')+'\n'+old[old.index('**本图范围：**'):]
md=md.replace('S070（水景）、S071（弧形平台）和 S073（庭院）仍待确认具体用途及室内外属性，目前作为 unknown 暂计入归一化分母。若确认是露天或挑空庭院，将调整为 courtyard／open_space 并移出室内面积分母；最终比例以确认后的归一化结果为准。','S070（水景）、S071（弧形平台）和 S073（景观区域）仍待确认用途，目前保持 unknown，暂计入归一化分母。确认为庭院、内庭院或挑空后，统一采用 courtyard／open_space 并移出室内面积分母，不取决于是否有顶盖或可步入；最终比例以确认后的归一化结果为准。')
rel=lambda f:os.path.relpath(T/f,R)
lines=['','## 本轮空间名称与范围核对','', '沿用原核对号01—31和S编号；可以分批填写，不重新编号。可修改“预估名称（可改）”后把确认栏填为“已确认”，或直接在确认栏写实际名称；也可聊天回复 `01=名称`。候选均未写入核心JSON。','',f'![30号完整名称核对总图]({rel("30_名称核对总图.png")})','',f'[打开高清总图]({rel("30_名称核对总图.png")})｜[原图]({data["image"]["file"]})｜[现有标注SVG](标注.svg)','']
for name,ss in meta:
 lines += ['### '+name,'',f'![{name}局部图]({rel(name+".png")})','','| 核对号 | S编号 | 预估名称（可改） | 备选名称 | 依据与把握 | 我的确认／备注 | 核对号（重复） |','| --- | --- | --- | --- | --- | --- | --- |']
 for q in ss:
  cs=q['candidates'].split('／');pred=cs[0];alt='／'.join(cs[1:]) or '暂无可靠备选'
  basis=q['basis']+'；'+('各候选共用上述依据，现有证据不能区分。' if len(cs)>1 else '')+'把握：'+q['confidence']+'。'
  lines += [f"| {q['number']} | {q['id']} | {pred} | {alt} | {basis} | 待确认 | {q['number']} |"]
 lines+=['']
lines+=['## 连通性补充记录','','本轮按原图纠正直接连接，并定位74个清晰门洞；均已写入JSON并在SVG画红点。现有121条关系：人员可达110条、服务联系6条、入口5条。其中74条access有定位，36条为未定位概念连接。','','- 影像检查室S008、S010、S026、S029通过独立病人更衣室S018、S019、S027、S028进入候诊通道，不把间接通行当作检查室直通走道；对应检查室与控制通道连接继续保留。','- 输液支持区撤回原S083—S084—S085内部串联。S083、S084各自连接S075大厅和S088交通核，S085面向大厅的柜台为service；S075与S088之间没有跨越两间小房的直接边。','- S061残厕的门向医疗街S016，已修正旧有直连S059的关系。S040交通核与S053之间未见独立直通门，撤回该旧边。','- 庭院段采用布局推断：S063—S073—S072—S075形成可达链。S063通向景观区域的门可定位；庭院内部步道、台阶不再拆小间，S073—S072仅保留概念连接，不编门位。庭院最终名称和面积类别等待28—30号确认。','','**本轮不细究的内部细节：**卫生间、交通核和庭院功能块内部不进一步拆小间；柜台窗口不作为人员门洞。未定位概念关系不等于不连通，未记录关系也不作为不可达的负例。','','### C01｜既有房名S084复核','',f'![输液支持房间S083—S085与相邻大厅、交通核]({rel("K02_输液支持.png")})','','**问题：**S084原来记录为“处置室”，放大后字形疑似“配药室”，是否改为配药室？','**我的判断：**倾向“配药室”；与31号S083分开确认，不替换或重排原名称核对号。当前JSON仍保留原名处置室，类别treatment，待明确答复后再修改。','**我的确认／备注：**待填写（配药室／保留处置室／实际名称）','']
(R/'标注说明.md').write_text(md+'\n'.join(lines))
print('generated overview, eight local sheets, connectivity evidence and editable MD')
