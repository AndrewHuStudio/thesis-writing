from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageStat
from shapely.geometry import Polygon,box,Point
import json,os,sys,shutil
base=Path('/Users/hushili/Documents/研究-论文写作/大论文/p-平面标注与数据处理');root=base/'标注试样/29_内蒙古自治区国际蒙医医院扩建项目';w=base/'临时核对/29_内蒙古自治区国际蒙医医院扩建项目';run=Path((w/'当前续作目录.txt').read_text().strip());d=json.loads((root/'annotation.json').read_text());state=json.loads((w/'review_state.json').read_text());by={s['id']:s for s in d['spaces']};source=Image.open(root/d['image']['file']).transpose(Image.Transpose.ROTATE_90).convert('RGB');font='/System/Library/Fonts/STHeiti Medium.ttc'
allpoints=[Point(p['position_px'][1],2444-p['position_px'][0]) for r in d['relations'] for p in r.get('openings',[])]
boxes={'K04':[1880,1310,2160,1660]}
manifest=[]
for item in state['connectivity_items']:
 if item['status']!='pending':continue
 rid=item['review_id'];b=boxes.get(rid,item['box_reading']);scale=3;im=source.crop(b).resize(((b[2]-b[0])*scale,(b[3]-b[1])*scale));out=Image.new('RGB',(im.width,im.height+90),'white');out.paste(im,(0,90));dr=ImageDraw.Draw(out)
 dr.text((16,12),f'29号｜{rid} 连通核对',font=ImageFont.truetype(font,32),fill='#12324f');dr.text((16,52),'房内数字对应S编号；按本题问题确认主要连接即可。',font=ImageFont.truetype(font,23),fill='#475569');shown=[]
 for sid in item['related_spaces']:
  p=Polygon([(y,2444-x) for x,y in by[sid]['polygon_px']]);clipped=p.intersection(box(*b));assert not clipped.is_empty
  for q in [p]:
   pts=[((x-b[0])*scale,90+(y-b[1])*scale) for x,y in q.exterior.coords];dr.line(pts,fill='#2563eb',width=3)
  anchor=clipped.representative_point();candidates=[]
  minx,miny,maxx,maxy=clipped.bounds
  for ix in range(1,16):
   for iy in range(1,16):
    x=minx+(maxx-minx)*ix/16;y=miny+(maxy-miny)*iy/16;q=Point(x,y);badge=box(x-10,y-7,x+10,y+7)
    if not clipped.covers(badge) or any(q.distance(op)<19 for op in allpoints):continue
    gray=source.crop((int(x-10),int(y-7),int(x+10),int(y+7))).convert('L');st=ImageStat.Stat(gray);score=st.stddev[0]+q.distance(anchor)*.03
    candidates.append((score,x,y))
  assert candidates, (rid,sid,'No badge fits')
  _,x,y=min(candidates);xx=(x-b[0])*scale;yy=90+(y-b[1])*scale;label=sid[1:];f=ImageFont.truetype(font,31);bw=dr.textbbox((0,0),label,font=f)[2]+10
  dr.rounded_rectangle((xx-bw/2,yy-20,xx+bw/2,yy+23),radius=4,fill='white',outline='#1d4ed8',width=3);dr.text((xx-bw/2+5,yy-19),label,font=f,fill='#1d4ed8');shown.append({'space_id':sid,'reading_position':[x,y]})
 name=f'{rid}_连通核对.png';out.save(run/name);item['figure']=str((run/name).resolve());item['badge_positions']=shown;manifest.append({'review_id':rid,'file':name,'spaces':shown,'size':out.size})
# Archive the exact editable document before replacing synced questions with only pending connectivity questions.
sys.path.insert(0,'/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts');from review_workflow import archive_markdown
archive_markdown(root/'标注说明.md',w/'review_state.json',(root/'标注说明.md').read_text())
lines=['# 29号｜内蒙古自治区国际蒙医医院扩建项目','','名称及合并已同步，K01“直接相通”已同步。当前只需核对以下5组主要连通问题；可直接填“我的确认／备注”，或在聊天按K号回复。','','数字为稳定S编号；无需填写门位或施工细节。','']
for item in state['connectivity_items']:
 if item['status']!='pending':continue
 rid=item['review_id'];p=os.path.relpath(item['figure'],root);lines += [f'### {rid}｜主要连通核对','',f'![{rid}连通核对，数字对应S编号]({p})','',f'**问题：**{item["question"]}','',f'**我的判断：**{item["judgment"]}','','**我的确认／备注：**待填写','']
(root/'标注说明.md').write_text('\n'.join(lines)+'\n');(w/'review_state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n');(run/'连通核对图清单.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
for file in ['/tmp/sync29_names.py','/tmp/connect29.py','/tmp/refine29_connect.py','/tmp/review29_figures.py','/tmp/draw29_working.py']:shutil.copy2(file,run/Path(file).name)
print({'pending_figures':len(manifest),'badges':sum(len(x['spaces']) for x in manifest),'archive_preserved':True})
