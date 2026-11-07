from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from shapely.geometry import Polygon,Point,box
import json,math,os,hashlib
from collections import Counter,deque

RUN=Path(__file__).resolve().parent;R=RUN.parent;P=R.parent.parent/'标注试样'/R.name
D=json.loads((P/'annotation.json').read_text());ST=json.loads((R/'review_state.json').read_text());S={s['id']:s for s in D['spaces']}
fontpath='/System/Library/Fonts/Supplemental/Arial Unicode.ttf'
font=ImageFont.truetype(fontpath,29);small=ImageFont.truetype(fontpath,21);badgefont=ImageFont.truetype(fontpath,26)
im=Image.open(P/D['image']['file']).convert('RGB');b=(270,100,1880,2160)
base=im.crop(b).rotate(90,expand=True);out=Image.new('RGB',(base.width+500,base.height+150),'white');out.paste(base,(0,80));draw=ImageDraw.Draw(out)
def transform(x,y):return y-b[1],b[2]-x+80
for s in D['spaces']:
 pts=[transform(x,y) for x,y in s['polygon_px']];draw.line(pts+[pts[0]],fill='#b7bec8',width=1)
for region in ST['regions']:
 for part in region['polygons_px']:
  pts=[transform(x,y) for x,y in part];draw.line(pts+[pts[0]],fill=region['color'],width=5)
 # 将区域号放在片区内的可见位置；具体名称在右侧对应，不覆盖小房间。
 anchor_space={1:1,2:10,3:14,4:27,5:39,6:2,7:103,8:126,9:65,10:66,11:82}[region['legend_number']]
 pt=Polygon(S[f'S{anchor_space:03d}']['polygon_px']).representative_point();x,y=transform(pt.x,pt.y)
 label=region['id'];bb=draw.textbbox((0,0),label,font=badgefont);ww=bb[2]-bb[0]+14;hh=40
 draw.rounded_rectangle((x-ww/2,y-hh/2,x+ww/2,y+hh/2),radius=5,fill='white',outline=region['color'],width=2)
 draw.text((x-(bb[2]-bb[0])/2,y-17),label,font=badgefont,fill=region['color'])
 idx=region['legend_number'];lx=base.width+28;ly=105+(idx-1)*91
 draw.line((lx,ly+18,lx+42,ly+18),fill=region['color'],width=6)
 draw.text((lx+54,ly),f'{region["id"]}  {region["name"]}',font=font,fill=region['color'])
 draw.text((lx+54,ly+40),f'原图图例 {idx} · {len(region["member_space_ids"])} 个成员单元',font=small,fill='#58677a')
draw.text((20,18),'38号｜区域外轮廓概览＋逐空间粗轮廓',font=ImageFont.truetype(fontpath,34),fill='#17324d')
draw.text((base.width+28,1220),'区域外框不重复计面积。',font=small,fill='#58677a')
draw.text((base.width+28,1260),'原图缺名保留 unknown。',font=small,fill='#58677a')
draw.text((base.width+28,1300),'灰线为原房间／通道轮廓。',font=small,fill='#58677a')
draw.text((20,out.height-48),'区域边界为图例与布局组织的概念近似；房间边界、已知门洞和S编号保存在正式SVG／JSON。',font=small,fill='#52677b')
out.save(RUN/'区域轮廓概览.png');out.resize((1536,round(out.height*1536/out.width))).save(RUN/'区域轮廓概览_预览.png')

# 新增单元局部：稳定S号与真实门点同图显示。
for label,b in [('S153_感染门诊旁小间',(1635,230,1740,325)),('S154_急诊中央两小间',(480,725,600,800))]:
 crop=im.crop(b).rotate(90,expand=True);scale=5;crop=crop.resize((crop.width*scale,crop.height*scale));cd=ImageDraw.Draw(crop)
 focus=['S153','S059','S060'] if label.startswith('S153') else ['S154','S046','S044']
 for sn in focus:
  poly=Polygon(S[sn]['polygon_px']).intersection(box(*b))
  if poly.is_empty:continue
  if poly.geom_type!='Polygon':poly=max(poly.geoms,key=lambda p:p.area)
  pts=[((y-b[1])*scale,(b[2]-x)*scale) for x,y in poly.exterior.coords];cd.line(pts+[pts[0]],fill='#0369a1',width=4)
  p=Polygon(pts);x0,y0,x1,y1=p.bounds;x=x0+8;y=y0+7
  cd.rectangle((x,y,x+83,y+39),fill='white',outline='#0369a1',width=2);cd.text((x+4,y+2),sn,font=badgefont,fill='#0369a1')
 for rel in D['relations']:
  for opening in rel.get('openings',[]):
   x,y=opening['position_px']
   if b[0]<x<b[2] and b[1]<y<b[3]:
    xx=(y-b[1])*scale;yy=(b[2]-x)*scale
    cd.ellipse((xx-7,yy-7,xx+7,yy+7),fill='#dc2626',outline='white')
 crop.save(RUN/(label+'.png'))

adj={sn:set() for sn in S}
for r in D['relations']:
 if r['type']=='access':adj[r['source']].add(r['target']);adj[r['target']].add(r['source'])
def reached(starts):
 seen=set(starts);q=deque(starts)
 while q:
  for b in adj[q.popleft()]:
   if b not in seen:seen.add(b);q.append(b)
 return seen
main=reached([r['target'] for r in D['relations'] if r['id']=='E01']);all_=reached([r['target'] for r in D['relations'] if r['type']=='entrance'])
stat={'spaces':len(S),'unknown':sum(s['type']=='unknown' for s in S.values()),
 'relations':dict(Counter(r['type'] for r in D['relations'])),
 'openings':sum(len(r.get('openings',[])) for r in D['relations']),
 'access_with_openings':sum(bool(r.get('openings')) for r in D['relations']),
 'main_reachable':len(main),'all_entrances_reachable':len(all_),
 'path_evidence_missing':sorted(set(S)-all_),'regions':len(ST['regions'])}
(RUN/'范围与可达统计.json').write_text(json.dumps(stat,ensure_ascii=False,indent=2)+'\n')
# 旧名称固定号不重排；新增空间仅续号。
Q=json.loads((RUN/'修改前备份/固定核对映射.json').read_text())
for q in Q:q['polygon_px']=S[q['id']]['polygon_px']
for n,sn,group in [(117,'S153',2),(118,'S154',1)]:
 Q.append({'number':str(n),'id':sn,'candidate':'无可靠候选','basis':'原图独立围合及门可辨；具体功能缺字','confidence':'低','group':group,'polygon_px':S[sn]['polygon_px']})
(R/'固定核对映射.json').write_text(json.dumps(Q,ensure_ascii=False,indent=2)+'\n')
rel=os.path.relpath(RUN,P)
body=['# 38号梅州市蕉岭县中医医院｜区域级粗轮廓与主要连通','',
 '<!-- annotation:summary:start -->','<!-- annotation:summary:end -->','',
 f'**区域概览：**11个图例区域保留粗外轮廓，内部可辨空间逐个保留S编号；区域叠加不重复计面积。{stat["unknown"]}个单元具体房名缺失，继续保留unknown，无需逐项猜名。','',
 f'![区域外轮廓概览]({rel}/区域轮廓概览.png)','',
 f'[打开概览原尺寸]({rel}/区域轮廓概览.png)','',
 '## 本轮补充','',
 '- 新增S153：感染门诊公共通道旁的独立围合小间，从S059中扣出；原图用途未标。',
 '- 新增S154：急诊中央S046中的独立小间，按可见隔墙拆出，S046保留较大原单元；两间均保留unknown。',
 '- 新增3条可达关系及P147—P149三处可见门洞；儿童发热片区的内部单元按图例10校正所属范围。',
 '- 其余S/R/P/E编号沿用。原S023、R025、E10退役号不复用；旧核对号01—116保留，新增单元续117、118。','',
 f'![S153局部]({rel}/S153_感染门诊旁小间.png)','',
 f'![S046与S154局部]({rel}/S154_急诊中央两小间.png)','',
 '## 主要连通与信息缺失','',
 '- 门诊大厅S001、候药大厅S010和医疗街S002衔接；急诊、输液经各自公共通道接入医疗街。',
 '- 放射影像公共通道S103、功能检测公共通道S126分别接医技横向通道S100；内部房间按实际可辨门洞连接。',
 '- 发热入口按S078→S077→S081→S065记录；儿童发热与肠道门诊保持各自入口及公共区。',
 '- 原K01：S038小门方向未画清，保留面向医疗街S002的概念联系R015，记为布局推断而非用户确认；S002与输液S039已有清晰连接，精确楼梯门向不改变本轮主要交通组织，不再必答。原K02已按可见侧门解决。',
 f'- 主入口经现有access可达{len(main)}个单元，计入各独立外门后可达{len(all_)}个。其余{len(S)-len(all_)}个单元入口证据不足，保留未知，不表示不通，也不作负例。','',
 '区域边界为概念近似，不能当作实测科室面积。医技外缘及公共配套中归属未明的单元保留现有scope，未强行归入图例科室；完整房名语义仍缺失，未来模型补名需另行检验。','']
(P/'标注说明.md').write_text('\n'.join(body))
print(json.dumps(stat,ensure_ascii=False,indent=2))
