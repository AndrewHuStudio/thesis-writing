from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from shapely.geometry import Polygon,Point,LineString
import json,os,re,hashlib,collections
base=Path('/Users/hushili/Documents/研究-论文写作/大论文/p-平面标注与数据处理');root=base/'标注试样/29_内蒙古自治区国际蒙医医院扩建项目';w=base/'临时核对/29_内蒙古自治区国际蒙医医院扩建项目/20261105_空间与连通补充'
d=json.loads((root/'annotation.json').read_text());records=json.loads((w/'review-data.json').read_text());mapping=json.loads((w/'review-mapping.json').read_text());by={x['id']:x for x in d['spaces']}
# Explicitly reviewed continuous hall divisions, not inferred room doors.
pairs=[('S004','S007'),('S004','S008'),('S007','S012'),('S007','S016'),('S008','S009'),('S008','S012'),('S008','S015'),('S008','S016'),('S009','S014'),('S012','S016'),('S014','S015'),('S014','S016'),('S014','S017'),('S015','S016'),('S120','S200')]
existing={tuple(sorted((r['source'],r['target']))) for r in d['relations'] if r['type']=='access'};n=max(int(r['id'][1:]) for r in d['relations'] if r['id'].startswith('R'));added=[]
for a,b in pairs:
 if tuple(sorted((a,b))) in existing:continue
 n+=1;r=dict(id=f'R{n:03d}',source=a,target=b,type='access');d['relations'].append(r);added.append(r)
(root/'annotation.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
(w/'本轮补充关系.json').write_text(json.dumps(added,ensure_ascii=False,indent=2)+'\n')
font='/System/Library/Fonts/STHeiti Medium.ttc'
def f(n):return ImageFont.truetype(font,n)
source=Image.open(w/'reading.png').convert('RGB');palette=['#2563eb','#7c3aed','#0f766e','#c2410c','#be185d','#047857','#9a3412']
def mark_crop(rows,box,path,title,mode='review',context=False):
 scale=3;box=tuple(int(x) for x in box);im=source.crop(box).resize(((box[2]-box[0])*scale,(box[3]-box[1])*scale));out=Image.new('RGB',(im.width,im.height+90),'white');out.paste(im,(0,90));dr=ImageDraw.Draw(out);dr.text((16,12),title,font=f(26),fill='#12324f');dr.text((16,49),'房内数字对应填写表；原图文字不清处可保持待确认。',font=f(20),fill='#475569')
 for r in rows:
  poly=Polygon(r['reading_polygon']);color=palette[r.get('band',0)];pts=[((x-box[0])*scale,90+(y-box[1])*scale) for x,y in r['reading_polygon']];dr.line(pts+[pts[0]],fill=color,width=3)
  # Place badge in the upper empty part when possible, preserving central room text.
  label=r['review'] if mode=='review' else r['id'][1:];size=22;p=poly.representative_point();candidates=[Point(p.x,p.y-16),Point(p.x,p.y+16),Point(p.x,p.y)]
  for point in candidates:
   rect=Polygon([(point.x-7,point.y-5),(point.x+7,point.y-5),(point.x+7,point.y+5),(point.x-7,point.y+5)])
   if poly.covers(rect):p=point;break
  xx=(p.x-box[0])*scale;yy=90+(p.y-box[1])*scale;tw=dr.textbbox((0,0),label,font=f(size))[2]+10
  dr.rounded_rectangle((xx-tw/2,yy-15,xx+tw/2,yy+17),radius=3,fill='white',outline=color,width=2);dr.text((xx-tw/2+5,yy-14),label,font=f(size),fill=color)
 out.save(path)
 return out.size
# Preserve the historical numbering while splitting dense groups into readable units.
groups=[]
for band in range(7):
 for side in ['L','R']:
  run=[r for r in mapping if r['band']==band and r['side']==side]
  for start in range(0,len(run),8):
   rows=run[start:start+8]
   if not rows:continue
   polys=[Polygon(r['reading_polygon']) for r in rows];bounds=(min(p.bounds[0] for p in polys)-32,min(p.bounds[1] for p in polys)-32,max(p.bounds[2] for p in polys)+32,max(p.bounds[3] for p in polys)+32)
   name=f"局部_{rows[0]['review']}-{rows[-1]['review']}.png";mark_crop(rows,bounds,w/name,f"29号｜名称核对 {rows[0]['review']}—{rows[-1]['review']}");groups.append((rows,name))
# Network inventory does not interpret omitted relations as inaccessible.
def graph(data):
 g={s['id']:set() for s in data['spaces']}
 for r in data['relations']:
  if r['type']=='access':g[r['source']].add(r['target']);g[r['target']].add(r['source'])
 seen=set();components=[]
 for s in g:
  if s in seen:continue
  stack=[s];seen.add(s);comp=[]
  while stack:
   a=stack.pop();comp.append(a)
   for b in g[a]-seen:seen.add(b);stack.append(b)
  components.append(sorted(comp))
 return {'components':sorted(components,key=lambda c:-len(c)),'degree_zero':[s for s in g if not g[s]],'opening_count':sum(len(r.get('openings',[])) for r in data['relations'])}
before=json.loads((w/'修改前备份/annotation.json').read_text());inventory={'before':graph(before),'after':graph(d),'added_access':len(added)};(w/'连通盘点.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
connrows=[r for r in records if r['id'] in {'S004','S007','S008','S009','S012','S014','S015','S016','S017','S052'}];mark_crop(connrows,(325,1355,1475,1845),w/'L01_大厅连续分区复核.png','29号｜L01 已补充的公共大厅连续分区',mode='space')
md=(w/'修改前备份/标注说明.md').read_text();md=md.replace('**连接关系：**80 条，人员可达 73 条、入口连接 7 条。',f"**连接关系：**{len(d['relations'])} 条，人员可达 {sum(r['type']=='access' for r in d['relations'])} 条、入口连接 7 条；本轮补充{len(added)}条连续大厅概念连接。已定位门洞仍为0，门洞恢复尚未完成。")
# Correct the old area rule statement without claiming the regions' names are known.
md=md.replace('圆形绿色中心、白色中空区域及边缘绿带的室内外属性待确认，暂不按露天中庭扣除。','圆形绿色中心、白色中空区域及边缘绿带的用途仍待确认；确定为庭院／挑空后保留节点并排除室内面积，不以有无顶盖作为统计条件。')
md=md.split('**名称待确认：**')[0]
def relpath(name):return os.path.relpath(w/name,root)
md+='''## 本轮名称与范围核对\n\n136项沿用上轮固定核对号，保留S编号。候选尚未确认，不写入核心JSON。可直接修改“预估名称（可改）”，并在“我的确认／备注”填写“已确认”；也可填写实际名称，或在聊天按 `01=名称` 回复。蒙医特色名称保留原名。\n\n先确认名称、类别及功能块范围，再逐片区补充房间与主通道的连接。庭院／绿化属性只核对用途与范围，不要求判断顶盖。\n\n'''
md+=f"![29号完整名称核对总图]({relpath('29_名称核对总图.png')})\n\n"
for rows,name in groups:
 md+=f"### {rows[0]['review']}—{rows[-1]['review']}｜相邻空间核对\n\n![{rows[0]['review']}—{rows[-1]['review']}局部放大]({relpath(name)})\n\n"
 md+='| 核对号 | S编号 | 预估名称（可改） | 备选名称 | 依据与把握 | 我的确认／备注 | 核对号（重复） |\n| --- | --- | --- | --- | --- | --- | --- |\n'
 for r in rows:
  basis=r['basis'].replace('露天状态未定。','用途尚待确认。').replace('不直接按露天中庭排除面积。','确认庭院后按统一口径排除室内面积。').replace('是否室内可步入待确认。','庭院或室内休息用途待确认。').replace('不能确定是否露天。','庭院用途待确认。').replace('不能确认露天。','庭院用途待确认。')
  if len(r['cand'])>1:basis+=' 两候选共用上述依据，目前不能区分。'
  md+=f"| {r['review']} | {r['id']} | {r['cand'][0]} | {'／'.join(r['cand'][1:]) or '暂无其他可靠候选'} | {basis} 把握：{r['confidence']}。 | 待确认 | {r['review']} |\n"
 md+='\n'
md+='## 本轮连通补充与后续范围\n\n'
md+=f"本轮补充{len(added)}条连续大厅概念连接：扇形翼部连接大厅的切分线是标注分区，图面不存在对应实体隔墙；S120—S200为独立片区大厅与交通核旁通道的连续衔接。依据原图连续灰色通行区域及原分区方式判断，不作为用户确认，不编造门位。\n\n"
md+=f"![已补充的大厅连续分区，房内数字为S编号后缀]({relpath('L01_大厅连续分区复核.png')})\n\n"
md+='补充空间对：'+ '、'.join(f"{r['source']}↔{r['target']}" for r in added)+'。\n\n'
md+=f"当前人员可达图有{len(inventory['after']['components'])}个已记录分量，{len(inventory['after']['degree_zero'])}个节点尚未记录室内access；这些数量反映草稿缺边，不能解释为真实建筑不可达。当前88条概念access均无定位红点，尚未逐门复核。\n\n"
md+='后续重点为扇形翼部整体出入口、主楼检查片区、黄色片区、橙色大空间、圆形区域与主通道衔接、蓝色片区及独立橙色片区。先明确名称与范围，再自主筛选有依据的连接；仅将影响主要可达组织的剩余疑点制作K编号短问答。小辅助间内部路线本轮不细究，关系留空不表示不相通。\n\n'
md+='当前仍为未完成草稿：136项名称未确认，功能块范围待核对，关系与门洞未完成全图语义复核。\n'
(root/'标注说明.md').write_text(md)
(w/'固定核对映射.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2)+'\n')
print({'groups':len(groups),'added':len(added),'spaces':len(d['spaces']),'relations':len(d['relations']),'pending':len(mapping),'components_before':len(inventory['before']['components']),'components_after':len(inventory['after']['components']),'isolated':len(inventory['after']['degree_zero'])})
