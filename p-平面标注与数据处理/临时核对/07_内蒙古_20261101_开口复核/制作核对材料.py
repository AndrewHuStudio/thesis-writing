from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from shapely.geometry import Polygon,LineString
import json,collections,re,hashlib
w=Path(__file__).resolve().parent;stage=w/'待核验成果';d=json.loads((stage/'annotation.json').read_text());ss={s['id']:s for s in d['spaces']};im=Image.open(stage/d['image']['file']).convert('RGB');fontpath='/System/Library/Fonts/STHeiti Medium.ttc';font=ImageFont.truetype(fontpath,22);small=ImageFont.truetype(fontpath,19);title=ImageFont.truetype(fontpath,34)
# 本轮编号独立于已封存的名称核对01—269；分批回答后不重排。
q=[
(['S008','S010'],'儿科急诊北侧两小间','两间南侧边界未辨出可靠人员门。请确认各自是否开向急诊大厅，或经相邻房间进入。','L',270),
(['S057','S072'],'妇产急诊保安／男更','现有底图未辨清门口。请分别说明通向哪一侧走廊或相邻空间；不能仅按共墙推定。','R',350),
(['S105'],'输液交通核入口','楼梯本体清楚，与候诊区 S106 的人员入口未辨清。请确认直接连接节点或门的位置。','L',930),
(['S139'],'药房电梯核入口','电梯井图形不代表整个后场任意互通。请确认该整体交通核是否从 S130 后场通道进入。','R',875),
(['S159','S163'],'产科交通核／穿刺室','S159 的出入口未辨清；S163 是否经 S161 更衣刷手进入，还是直接开向门诊通道？旧 S163—S162 边已移至待核记录。','R',1060),
(['S285'],'影像准备间入口','S285 左侧未辨出可靠门洞；请确认开向 S271、S286，或经相邻后场房间进入。原推测边保存在外部。','L',1465),
(['S294'],'影像准备间入口','该间边界可见，但人员入口未辨清。请确认通向 S271、S291 或相邻后场房间。','L',1600),
(['S301'],'影像准备间入口','房间轮廓已按原图横墙调整；未辨出可靠门口。请确认与 S297、S271 或 S296 的实际人员联系。','L',1735),
(['S312'],'影像准备间入口','该间与扫描室之间未见清晰门。请确认是否开向 S304、S271 或相邻后场房间。','L',1870),
(['S322'],'影像检查室入口','S317、S318的门已定位；仍不能由此推出 S322 与其互通。请确认 S322 实际开向通道或哪个相邻房间。','L',2005),
(['S323'],'男浴内部入口','与 S326 女更衣室、S316 治疗室的隔墙关系不能证明通行。请按原图说明真实相连空间。','L',2110),
(['S325'],'影像后场治疗室入口','S320—S321 的门已定位；S325 未辨出可靠入口。请确认是否接 S271、S320 或 S321。','L',2215),
(['S336'],'空调机房入口','下排机房的人员入口未辨清，不能取房间上边中点补门。请指出实际开门边及相连通道。','L',2320),

]
colors=['#c2410c','#7c3aed','#0369a1','#047857','#be185d','#a21caf','#a21caf','#a21caf','#a21caf','#a21caf','#a21caf','#a21caf','#a21caf','#7c3aed']
W,H=im.size;side=690;top=135;canvas=Image.new('RGB',(W+side*2,H+top+70),'#f8fafc');canvas.paste(im,(side,top));dr=ImageDraw.Draw(canvas);dr.text((side,20),'07号｜连通性集中核对 01—13',font=title,fill='#0f172a');dr.text((side,72),'完整原图未裁切；彩框保留原 S 编号。请回复：01=各房间连向……（可分批）',font=small,fill='#334155')
lines=[];mapping=[]
def textwrap(txt,n=23):return [txt[i:i+n] for i in range(0,len(txt),n)]
for i,(ids,caption,question,sidekey,ly) in enumerate(q,1):
 color=colors[i-1];polys=[Polygon(ss[s]['polygon_px']) for s in ids];bounds=[p.bounds for p in polys]
 # 引线指向同组靠侧的空间框；同组其它空间各有同号标记。
 chosen=min(bounds,key=lambda b:b[0]) if sidekey=='L' else max(bounds,key=lambda b:b[2]);chosen=bounds[0] if i==10 else chosen;ax=(chosen[0] if sidekey=='L' else chosen[2]);ay=(chosen[1]+15) if i==10 else (chosen[1]+chosen[3])/2
 for sid,b in zip(ids,bounds):
  x1,y1,x2,y2=b;dr.rectangle((side+x1,top+y1,side+x2,top+y2),outline=color,width=4);dr.rectangle((side+x1,top+y1-25,side+x1+112,top+y1),fill='white',outline=color,width=2);dr.text((side+x1+3,top+y1-25),f'{i:02} {sid}',font=small,fill=color)
 lx=25 if sidekey=='L' else side+W+30;right=lx+635;labelY=top+ly-40
 dr.rounded_rectangle((lx,labelY,right,labelY+89),radius=8,fill='white',outline=color,width=2)
 dr.text((lx+12,labelY+7),f'{i:02}｜{caption}',font=font,fill=color);dr.text((lx+12,labelY+37),' / '.join(ids),font=small,fill='#334155');dr.text((lx+12,labelY+62),'入口／通向待确认，详见说明表',font=small,fill='#475569')
 start=(right,top+ly) if sidekey=='L' else (lx,top+ly)
 # 同侧单调扇形引线；各片区保持图面上下顺序。
 elbow=(side+1480,top+ay) if sidekey=='L' and i>=6 else (side-10,top+ay) if sidekey=='L' else (side+W+10,top+ay)
 pts=[start,elbow,(side+ax,top+ay)];dr.line(pts,fill=color,width=2);dr.ellipse((side+ax-5,top+ay-5,side+ax+5,top+ay+5),fill=color);lines.append(LineString(pts))
 # 每组另附局部，仅补充总图。
 b=(max(0,min(t[0] for t in bounds)-75),max(0,min(t[1] for t in bounds)-65),min(W,max(t[2] for t in bounds)+75),min(H,max(t[3] for t in bounds)+65));crop=im.crop(tuple(map(int,b))).resize((int((b[2]-b[0])*3),int((b[3]-b[1])*3)));cd=ImageDraw.Draw(crop)
 for sid,t in zip(ids,bounds):
  cd.rectangle(((t[0]-b[0])*3,(t[1]-b[1])*3,(t[2]-b[0])*3,(t[3]-b[1])*3),outline=color,width=4);cd.text(((t[0]-b[0])*3+4,(t[1]-b[1])*3+4),f'{i:02} {sid} {ss[sid]["name"]}',font=font,fill=color,stroke_width=2,stroke_fill='white')
 crop.save(w/f'连通核对{i:02}_局部.png');mapping.append(dict(number=f'{i:02}',spaces=ids,caption=caption,question=question))
cross=[]
for i,a in enumerate(lines):
 for j,b in enumerate(lines[i+1:],i+1):
  if a.crosses(b) or a.overlaps(b):cross.append([i+1,j+1])
canvas.save(w/'连通核对总图_01-13.png');preview=canvas.copy();preview.thumbnail((1850,1100));preview.save(w/'连通核对总图_预览.png');(w/'连通核对映射_工作.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2));print('LEADER_CROSSINGS',cross)
# 保留历史名称确认记录和原说明中的用户决定，只更新统计、状态及当前核对部分。
base=(w/'修改前备份'/'标注说明.md').read_text();counts=collections.Counter(r['type'] for r in d['relations']);opened=[r for r in d['relations'] if r.get('openings')];n=sum(len(r['openings']) for r in opened);unlocated=counts['access']-len(opened)
base=base.replace('本张图已完成名称确认与正式四文件校验（2026-10-31），无未确认功能。','本图名称已全部确认；2026-11-01补充门洞与连通性。当前仍有13组人员入口／门向待确认，本轮连通性补充尚未全部完成。')
base=re.sub(r'\*\*连接关系：\*\*[^\n]+',f'**连接关系：**{len(d["relations"])} 条，人员可达 {counts["access"]} 条、服务联系 {counts["service"]} 条、共墙 {counts["shared_wall"]} 条、入口连接 {counts["entrance"]} 条。',base)
base=base.replace('**范围与精度：**本次完成仅限07号','**范围与精度：**本次处理仅限07号')
section=f'''\n\n**本轮开口补充：**{n}个实心红点（P001—P{n:03}），均为可辨门洞，对应{len(opened)}条人员可达关系；同一空间对多个门合并在同一关系下。另有{unlocated}条无定位的概念通行，主要为走廊／大厅连续分区、半墙服务区及整体交通核边界，不伪造具体门位。本轮未将无实体分隔的分区线或交通核内部门计作室内跨空间开口。\n\n**本轮轮廓与关系调整：**保留全部409个S编号及已确认名称。补齐S129、S130、S143、S276后场走廊漏段；对CT扫描及后场部分横墙轮廓按原图校正，并同步修整相邻通道、重新归一化406个室内区域。S318准备间可辨门已补入，S370整体交通核与S347连续前区仅保存概念联系。三处露天／挑空中庭、既有合并／拆分与删除结果保持原口径。明确门向的旧边改接实际节点；7条门向未证实的旧推测边保存在外部[待核旧关系记录](../../临时核对/07_内蒙古_20261101_开口复核/待核旧关系.md)，不作为当前通行事实。窗口只记service，已辨共墙另记shared_wall。\n\n**本轮校验边界：**正式`validate --check-dir`用于结构、几何、归一化及JSON／SVG红点一致性；通过不代表下列入口问题已解决。名称确认和连通性待确认分别记录。原图及历史用户填写均保留。\n\n## 连通性集中核对（本轮固定01—13）\n\n这里的01—13是本轮连通核对号，与历史名称核对01—269分开。按片区阅读：儿科急诊、妇产急诊、输液、药房、产科、影像及围产保健；影像片区自上而下。可在确认栏填写实际相连S编号、开门边或“仅概念相通、无具体门位”，也可聊天回复`01=……，02=……`。不清楚可保留待确认；已有名称无需重新确认。\n\n[打开完整高清核对总图](../../临时核对/07_内蒙古_20261101_开口复核/连通核对总图_01-13.png) · [查看具名标注](标注.svg) · [原图]({d['image']['file']})\n\n![完整原图连通性核对总图](../../临时核对/07_内蒙古_20261101_开口复核/连通核对总图_01-13.png)\n\n| 核对号 | S编号及已确认名称 | 待确认内容及依据 | 我的确认／备注 | 核对号（重复） |\n| --- | --- | --- | --- | --- |\n'''
for row in mapping:
 num=row['number'];names='；'.join(s+' '+ss[s]['name'] for s in row['spaces']);section+=f'| {num} | {names} | {row["question"]} [局部](../../临时核对/07_内蒙古_20261101_开口复核/连通核对{num}_局部.png) | 待确认 | {num} |\n'
(stage/'标注说明.md').write_text(base+section)
pending=json.loads((w/'待核旧关系_工作.json').read_text());(w/'待核旧关系.md').write_text('# 07号本轮待核旧推测关系\n\n以下旧边尚无可靠门洞依据，暂存于此，未经确认不回写为access；不是已确认的空间删除或合并。原四文件及用户填写备份均保留。\n\n| 原关系号 | 空间对 | 状态 |\n| --- | --- | --- |\n'+''.join(f'| {r["id"]} | {r["source"]} — {r["target"]} | 待确认门向 |\n' for r in pending))
print('COUNTS',counts,'OPENINGS',n,'LOCATED',len(opened),'CONCEPTUAL',unlocated)
