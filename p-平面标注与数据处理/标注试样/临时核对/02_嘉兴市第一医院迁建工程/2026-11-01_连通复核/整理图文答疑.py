from pathlib import Path
import json,re,hashlib,shutil,math
from PIL import Image,ImageDraw,ImageFont
from shapely.geometry import Polygon,box,LineString
out=Path(__file__).parent;p=out.parents[2]/'02_嘉兴市第一医院迁建工程';mdpath=p/'标注说明.md';oldmd=mdpath.read_text();shutil.copy2(mdpath,out/'标注说明_改为逐项图文答疑前.md')
protected={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in p.iterdir() if f.is_file() and f.name!='标注说明.md'}
d=json.loads((p/'annotation.json').read_text());spaces={s['id']:s for s in d['spaces']};qs=json.loads((out/'核对映射.json').read_text());rows={}
header=None
for l in oldmd.splitlines():
 if l.startswith('| 核对号 |'):header=[v.strip() for v in l.strip().strip('|').split('|')]
 elif header and l.startswith('| '):
  vals=[v.strip() for v in l.strip().strip('|').split('|')]
  if len(vals)==len(header) and re.fullmatch(r'\d{2}',vals[0]):rows[vals[0]]=dict(zip(header,vals))
assert set(rows)=={f'{i:02}' for i in range(1,17)}
fontfile='/System/Library/Fonts/Supplemental/Songti.ttc';small=ImageFont.truetype(fontfile,24);titlefont=ImageFont.truetype(fontfile,32);idfont=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',22);orig=Image.open(p/d['image']['file']).convert('RGB')
for q in qs:
 n=q['number'];x0,y0,x1,y1=q['box'];pad=75;bb=(max(0,x0-pad),max(0,y0-pad),min(orig.width,x1+pad),min(orig.height,y1+pad));refids=set(re.findall(r'S\d{3}',q['spaces']+' '+q['question']+' '+q['evidence']));subjects=set(re.findall(r'S\d{3}',q['spaces']));cropbox=box(*bb);shown=[]
 for sid in sorted(refids):
  g=Polygon(spaces[sid]['polygon_px']).intersection(cropbox)
  if not g.is_empty and g.area>15:shown.append((sid,g))
 # Full original excerpt is preserved; coloured overlays only add outlines and S identifiers.
 scale=max(2,min(4,1650/(bb[2]-bb[0])));cw=round((bb[2]-bb[0])*scale);ch=round((bb[3]-bb[1])*scale);legend_rows=math.ceil(len(shown)/2);W=max(cw,1100);head=90;foot=55+legend_rows*40;can=Image.new('RGB',(W,head+ch+foot),'white');ox=(W-cw)//2;can.paste(orig.crop(bb).resize((cw,ch)),(ox,head));dr=ImageDraw.Draw(can);dr.text((16,12),f'{n}｜{q["title"]}',font=titlefont,fill='#1e293b');dr.text((16,52),'橙框：本项待核空间；蓝框：问题中提到的对照空间。名称沿用当前标注。',font=small,fill='#475569');used=[]
 for sid,g in sorted(shown,key=lambda z:(z[0] not in subjects,z[0])):
  col='#d97706' if sid in subjects else '#2563eb';geoms=list(g.geoms) if hasattr(g,'geoms') else [g]
  for poly in geoms:
   if poly.geom_type!='Polygon':continue
   pts=[(ox+(x-bb[0])*scale,head+(y-bb[1])*scale) for x,y in poly.exterior.coords];dr.line(pts,fill=col,width=4)
  pt=g.representative_point();ax=ox+(pt.x-bb[0])*scale;ay=head+(pt.y-bb[1])*scale;w=65;h=27;candidates=[]
  for dy in [0,-32,32,-64,64]:
   for dx in [0,-70,70,-140,140]:
    xx=min(max(ox+2,ax-w/2+dx),ox+cw-w-2);yy=min(max(head+2,ay-h/2+dy),head+ch-h-2);r=box(xx,yy,xx+w,yy+h);overlap=sum(r.intersection(z).area for z in used);candidates.append((overlap*100+abs(dx)+abs(dy),xx,yy,r))
  _,xx,yy,r=min(candidates,key=lambda z:z[0]);used.append(r)
  if abs((xx+w/2)-ax)+abs((yy+h/2)-ay)>25:dr.line((ax,ay,xx+w/2,yy+h/2),fill=col,width=2)
  dr.rounded_rectangle((xx,yy,xx+w,yy+h),radius=3,fill='white',outline=col,width=2);dr.text((xx+3,yy+1),sid,font=idfont,fill=col)
 for i,(sid,g) in enumerate(shown):
  txt=sid+' '+spaces[sid]['name'];col='#d97706' if sid in subjects else '#2563eb';x=16+(i%2)*(W//2);y=head+ch+15+(i//2)*40;dr.text((x,y),txt,font=small,fill=col)
 can.save(out/f'答疑{n}_标记截图.png')
# Existing overview and case-specific notes are retained below the working question sections.
start=oldmd.index('**核对方式：**');overview=oldmd[oldmd.index('**标注规模：**'):start].rstrip();formal=oldmd[oldmd.index('**正式校验结果'):].strip();prefix='../临时核对/'+p.name+'/'+out.name
intro='''# 嘉兴市第一医院｜看图答疑与标注说明

当前为复核草稿：16 项需要确认。既有空间编号与原名称保留，尚未依据候选或空白回答修改数据。

**怎么填写：**依次看下面的标记截图和问题，直接修改每张截图下面表格中的“我的确认／备注”。可以填实际名称、连接的 S 编号或自然语言说明；不清楚就写“不清楚”。09、10 也可以直接修改“预估名称（可改）”，再在确认栏写“已确认”。可以分批填写。填完后在聊天里告诉我“已填写标注说明”，我会重新读取本文件，再同步更新 JSON、SVG 和本说明；未回答的项继续待确认。

橙框表示本项待核空间，蓝框表示问题中提到的对照空间；截图底部列有编号和现有名称。原图不改动。最右侧重复核对号不是答案栏。

## 原图定位总图

'''
text=intro+f'![16项答疑原图定位总图]({prefix}/连通疑点_原图核对总图.png)\n\n'
text+='跳转：'+' · '.join(f'[{q["number"]}](#核对{q["number"]})' for q in qs)+'\n\n'
for q in qs:
 n=q['number'];r=rows[n];answer=r['我的确认／备注'];text+=f'<a id="核对{n}"></a>\n\n## 核对 {n}｜{q["title"]}\n\n**请确认：**{q["question"]}\n\n'
 text+=f'![核对{n}标记截图]({prefix}/答疑{n}_标记截图.png)\n\n'
 text+=f'[查看未叠加空间编号的原图局部]({prefix}/核对{n}_局部.png)\n\n**目前不能确定的原因：**{q["evidence"]}\n\n'
 if n in ['09','10']:
  text+='| 核对号 | S编号 | 预估名称（可改） | 备选名称 | 依据与把握 | 我的确认／备注 | 核对号（重复） |\n| --- | --- | --- | --- | --- | --- | --- |\n'
  evidence=re.sub(r' \[局部\]\([^)]+\)','',r['依据与把握'])
  text+=f'| {n} | {r["S编号"]} | {r["预估名称（可改）"]} | {r["备选名称"]} | {evidence} | {answer} | {n} |\n\n'
 else:
  text+='| 核对号 | S编号 | 我的确认／备注 | 核对号（重复） |\n| --- | --- | --- | --- |\n'
  text+=f'| {n} | {r["S编号"]} | {answer} | {n} |\n\n'
  # Preserve any prior user edits to estimate/candidate columns even for connectivity rows.
  if r['预估名称（可改）']!='沿用既有名称' or r['备选名称']!='本项仅核对连接':text+=f'保留此前填写：预估名称＝{r["预估名称（可改）"]}；备选名称＝{r["备选名称"]}。\n\n'
text+='## 标注概览与既有说明\n\n'+overview+'\n\n'+formal+'\n';mdpath.write_text(text)
# Verify 16 embedded excerpts, all link targets and exactly one editable answer row per question.
assert len(re.findall(r'!\[核对\d{2}标记截图\]',text))==16
newanswers=[]
for line in text.splitlines():
 if re.match(r'^\| \d{2} \|',line):newanswers.append([v.strip() for v in line.strip('|').split('|')])
assert [r[0] for r in newanswers]==[f'{i:02}' for i in range(1,17)]
for vals in newanswers:assert vals[-2]==rows[vals[0]]['我的确认／备注'];assert vals[-1]==vals[0]
for m in re.finditer(r'\]\(([^)]+)\)',text):
 dest=m.group(1)
 if not dest.startswith('#'):assert (p/dest).exists(),dest
for fn,sha in protected.items():assert hashlib.sha256((p/fn).read_bytes()).hexdigest()==sha,fn
print('16 marked screenshots embedded; 16 unique answer rows; previous answers preserved; all image links valid; original/JSON/SVG unchanged.')
print(mdpath.resolve())
