from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from shapely.geometry import Polygon,Point,box
import json,math,os
R=Path(__file__).resolve().parent;P=R.parent.parent/'标注试样'/R.name
D=json.loads((P/'annotation.json').read_text());Q=json.loads((R/'固定核对映射.json').read_text());S={s['id']:s for s in D['spaces']};im=Image.open(P/D['image']['file']).convert('RGB')
fontpath='/System/Library/Fonts/Supplemental/Arial Unicode.ttf';colors=['#9b2778','#1c6eae','#b05b08','#087b6b']
state=json.loads((R/'review_state.json').read_text());state['connectivity_items']=[{'review_id':'K01','source':'S038','target':'S002','status':'pending','reason':'楼梯整体轮廓可辨，但朝医疗街或输液侧的出入口在原图中不清楚；暂保留原 R015 等待核对'}, {'review_id':'K02','source':'S077','target':'S065','status':'not_required','reason':'助手放大图自主复核：S077下侧为连续墙，清晰侧门经S081通向S065；已同步S077-S081-S065，关键通行组织明确，退出提问，不记为用户确认不连接'}]
state['checks']['connectivity_reviewed']=True
state['details_not_required']={'spaces':['S090','S093'],'reason':'原图文字缺失或辅助小间内部出入口不清，本轮保留空间，证据不足的内部连接不推补；未记录不等于不连接。'}
(R/'review_state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
openpts=[Point(o['position_px']) for rel in D['relations'] for o in rel.get('openings',[])]
def crop_mark(name,bounds,labels):
 b=tuple(map(int,bounds));scale=3
 crop=im.crop(b).rotate(90,expand=True).resize(((b[3]-b[1])*scale,(b[2]-b[0])*scale));draw=ImageDraw.Draw(crop)
 font=ImageFont.truetype(fontpath,30)
 for sn,label,color in labels:
  poly=Polygon(S[sn]['polygon_px']).intersection(box(*b))
  if poly.is_empty or poly.area<30:continue
  if poly.geom_type!='Polygon':poly=max(poly.geoms,key=lambda q:q.area)
  coords=[((y-b[1])*scale,(b[2]-x)*scale) for x,y in poly.exterior.coords];draw.line(coords+[coords[0]],fill=color,width=3)
  rp=Polygon(coords);bb=draw.textbbox((0,0),label,font=font);ww=bb[2]-bb[0]+12;hh=40;xx1,yy1,xx2,yy2=rp.bounds
  candidates=[(xx1+ww/2+5,yy1+hh/2+5),(xx2-ww/2-5,yy1+hh/2+5),(xx1+ww/2+5,yy2-hh/2-5),(xx2-ww/2-5,yy2-hh/2-5)]
  pt=rp.representative_point();candidates.append((pt.x,pt.y))
  for xx,yy in candidates:
   badge=box(xx-ww/2,yy-hh/2,xx+ww/2,yy+hh/2)
   if not rp.covers(badge):continue
   orig=Point(b[2]-yy/scale,b[1]+xx/scale)
   if any(orig.distance(p)<12 for p in openpts):continue
   break
  else:
   # 搜索内部位置；文字必须在对应空间内。
   for xx in range(math.ceil(xx1+ww/2),math.floor(xx2-ww/2),6):
    for yy in range(math.ceil(yy1+hh/2),math.floor(yy2-hh/2),6):
     if rp.covers(box(xx-ww/2,yy-hh/2,xx+ww/2,yy+hh/2)):break
    else:continue
    break
   else:raise ValueError(('badge cannot fit',sn,label,b))
  draw.rounded_rectangle((xx-ww/2,yy-hh/2,xx+ww/2,yy+hh/2),radius=5,fill='white',outline=color,width=2)
  draw.text((xx-(bb[2]-bb[0])/2,yy-18),label,font=font,fill=color)
 crop.save(R/(name+'.png'))
 return name+'.png'
rel=os.path.relpath(R,P)
body=['# 38号梅州市蕉岭县中医医院｜首层标注草稿','', '<!-- annotation:summary:start -->','<!-- annotation:summary:end -->','', '本轮补齐急诊公共走道，纠正医技等旧关系并补入可辨门洞。S023为旧差集产生的1.49像素边界条，已按边界归并入相邻S024／S025，退役号不复用；其余S编号和全部名称核对号沿用，原图未改。名称和下列关键关系尚未全部确认，当前为草稿。','', '## 连通性核对','', '图内数字为 S 编号后三位。只需填写判断，不必确定精确门位。','']
kdefs=[('K01',(575,490,950,890),[38,2,39,27], 'S038 楼梯是否直接连向医疗街 S002？若实际经输液室 S039 或急诊公共区 S027 进入，请写相连的 S 号。','现有 R015 暂保留；这处楼梯的外侧门向分辨率不足，需核对主要通行方向。'),('K02',(1625,690,1845,875),[78,77,65,81], 'S077 是否有门或无门开口通向公共通道 S065？','S078 与 S077 间的双扇门清楚；S077 下侧边界看似有墙。本轮已将原来跨过 S077 的关系改为 S078↔S077，暂未补 S077↔S065。')]
for rid,b,nums,question,judgement in kdefs[:1]:
 file=crop_mark(rid+'_连通局部',b,[(f'S{n:03d}',f'{n:03d}','#005f8a') for n in nums])
 clean=im.crop(b).rotate(90,expand=True);clean.resize((clean.width*3,clean.height*3)).save(R/(rid+'_无标记原图.png'))
 body += [f'### {rid}',f'![{rid}连通局部]({rel}/{file})','',f'[查看同范围无标记原图]({rel}/{rid}_无标记原图.png)','',f'**问题：**{question}',f'**我的判断：**{judgement}','**我的确认／备注：**待填写','']
body += ['## 名称核对','', '原固定核对号 01—116 保持不变。可修改“预估名称（可改）”，再将确认栏改为“已确认”；也可直接填写实际名称，或在聊天中按 `01=名称` 回复。候选均未写入 JSON。','',f'![38号完整核对总图]({rel}/38_高清核对总图.png)','',f'[打开总图原尺寸]({rel}/38_高清核对总图.png)','']
idx=0
for group,title in [(1,'急诊与输液'),(2,'发热、儿童发热与肠道门诊'),(0,'大厅、药房与公共配套'),(3,'医技区')]:
 arr=[q for q in Q if q['group']==group]
 for start in range(0,len(arr),6):
  block=arr[start:start+6];idx+=1
  polys=[Polygon(q['polygon_px']) for q in block];xmin=min(p.bounds[0] for p in polys);ymin=min(p.bounds[1] for p in polys);xmax=max(p.bounds[2] for p in polys);ymax=max(p.bounds[3] for p in polys)
  b=(max(0,math.floor(xmin-22)),max(0,math.floor(ymin-22)),min(im.width,math.ceil(xmax+22)),min(im.height,math.ceil(ymax+22)))
  name=f'名称_{block[0]["number"]}-{block[-1]["number"]}'
  file=crop_mark(name,b,[(q['id'],q['number'],colors[group]) for q in block])
  body += [f'### {block[0]["number"]}—{block[-1]["number"]}｜{title}',f'![{name}]({rel}/{file})','', '| 核对号 | S编号 | 预估名称（可改） | 备选名称 | 依据与把握 | 我的确认／备注 | 核对号（重复） |','| --- | --- | --- | --- | --- | --- | --- |']
  for q in block:
   candidates=q['candidate'].split(' / ');cand=candidates[0];alternate='／'.join(candidates[1:]) or '—'
   basis=q['basis']+'；把握：'+q['confidence']
   if len(candidates)>1:basis+='。候选共用该依据，现图不能区分'
   body.append(f'| {q["number"]} | {q["id"]} | {cand} | {alternate} | {basis} | 待确认 | {q["number"]} |')
  body.append('')
(P/'标注说明.md').write_text('\n'.join(body)+'\n')
print('local groups',idx,'name rows',len(Q),'K questions',1)
