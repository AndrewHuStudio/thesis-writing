from pathlib import Path
import json,collections,math
from PIL import Image,ImageDraw,ImageFont
from shapely.geometry import LineString
out=Path(__file__).parent;stage=out/'待核验成果';d=json.loads((stage/'annotation.json').read_text());ss={s['id']:s for s in d['spaces']};types=json.loads(Path('/Users/hushili/.codex/skills/outpatient-plan-annotation/references/space-types.json').read_text())
# 已看清的区域连续、半墙及节点切分；剩余无门位旧 access 一律列入待核。
concept_ids=set('R029 R035 R037 R045 R060 R071 R078 R079 R099 R106 R107 R108 R110 R111 R112 R113 R114 R120 R123 R143 R144 R152 R157 R158 R159 R164 R165 R179 R181 R194 R195 R196 R198 R203 R205 R208 R209 R210 R211 R215 R228 R230 R232 R236 R237 R238 R239 R240 R263 R289 R290 R291 R294 R295 R298 R310 R313 R315 R316 R318 R319 R323 R324 R325 R337'.split())
known_pairs={tuple(sorted(p)) for p in [('S187','S344'),('S001','S031'),('S107','S113'),('S187','S207'),('S329','S337'),('S317','S319')]}
groups=[
('01','北侧病房楼', (1090,45,1590,295),'right',[(1590,180),(1740,180)],'R306', ['S304','S305','S313','S314'], '配餐、医保／新农合／出入院前沿已按服务联系记录。请确认工作人员从哪侧进入 S304、S305，以及设备间 S313、消防控制／保安监控 S314 的入口；不要把窗口当通行。'),
('02','中心供应', (640,155,1035,390),'left',[(640,260),(180,260),(-15,260)],'R134', ['S121','S124','S141'], '保留已有洁污分区名称。请确认 S121 辅料室、S124 小通道、S141 洁具间与周边的直接连通，以及去污区 S120 与交通核 S125 的人员入口；器械传递界面不能代替人员门。'),
('03','MRI 上部及东侧用房',(640,400,990,568),'left',[(640,430),(620,430),(620,350),(180,350),(-15,440)],'R156 R162 R163 R175',['S150','S171'],'请核对 S161 MRI、S162 机房实际朝哪侧开门，S150 医生办公入口、S171 小通道入口及其与 S172 库房的关系。可见门已补点，其余旧边保留待核。'),
('04','MRI／CT 患者侧',(640,568,990,655),'left',[(640,610),(600,610),(600,360),(180,360),(-15,600)],'R170 R180 R182',['S177','S178','S180'],'请确认 S177 打印出片、S178 过渡间、S180 接待间的人员入口，以及等候区与处置 S176 的关系；护士站半墙仅保留概念连通，不补虚构门位。'),
('05','南侧病房楼',(1090,585,1590,875),'right',[(1590,665),(1740,665)],'R329 R339',['S331','S336'],'请核对财务室 S331、设备间 S336 和南侧交通核 S339 的入口。理发 S341 已据北侧门连接 S329；专用品发售与超市的区域连续保留概念关系。'),
('06','普放北侧出片及更衣',(675,680,976,756),'left',[(675,720),(550,720),(550,370),(180,370),(-15,735)],'R204 R206',['S199','S200'],'请核对 S191 打印出片是否直接通北侧 S188，以及 S199 更衣与 S200 打印出片工作人员从哪侧进入。DR 的清晰门在南侧，已连接 S190。'),
('07','普放南侧小房间',(675,781,976,864),'right',[(976,830),(1040,830),(1040,900),(1650,900),(1740,900)],'R190 R191 R192 R213 R214 R217 R218 R219 R223',[],'请确认三个既有胃肠空间 S214—S216 的门向及相互关系、S205 会诊示教、S206 储藏室、S209 主任与 S210／S211 卫生间的入口。旧东侧 access 暂存待核，不能当已确认边训练。'),
('08','医技南端支持房',(535,864,758,977),'left',[(535,900),(520,900),(520,385),(180,385),(-15,890)],'R115 R227', ['S219','S220','S224'], '请核对空调机房 S224 的主要人员入口、值班 S219／库房 S220 与新补 S344 小通道的路径，以及西侧交通核 S115 的入口。两处可见机房侧门已分别记录，未跨房直连远处通道。'),
('09','门诊手术及西侧交通核',(277,919,434,969),'left',[(277,944),(180,944),(-15,980)],'R084 R085',['S029','S076'],'请确认清洁治疗 S085—手术间 S079、清洁治疗 S083—手术间 S082 是否确有内部人员门；不能因功能配套直接认定相通；西侧交通核 S029、S076 的内侧／外侧入口图面含混，不补定位点，请一并确认。'),
('10','急诊西侧卫生及收费',(835,996,940,1110),'left',[(835,1050),(780,1050),(780,1080),(180,1080),(-15,1130)],'', ['S256','S257','S258','S259','S260','S261','S262','S265','S266','S267'], '请确认 S256 盥洗间、S257 B超、S258／S260 卫生间、S261／S262 前室和 S259 小通道的直接路径，并补充收费工作区 S265—S267 的员工入口。已确认名称继续保留。'),
('11','急诊北侧及挂号',(976,925,1208,1126),'right',[(1208,1100),(1740,1100)],'R257', ['S253','S290'], '请另核 120 指挥中心旁 S290 卫生间的门向，现有边界与门扇线索不足以可靠定位。挂号收费 S253 面向大厅的界面仅按 service。请确认其工作人员入口；诊室儿科、心电、外科、内科与石膏的清晰门已按实际上下相邻空间记录。'),
('12','急救南端及保安',(807,1155,1200,1295),'right',[(1200,1230),(1740,1230)],'R270 R271 R276 R277 R278',['S279','S281','S282'], '请核对 EICU 西侧交通核入口、南端护士／办公／卫生间的入口及 S283 小通道是否成立，并确认保安 S286 的人员入口。抢救室与 EICU 的两处清晰开口已合并在同一关系内。'),
('13','药房南沿与交通核',(408,1225,487,1300),'left',[(408,1240),(180,1240),(-15,1300)],'R102 R342 R345',['S343'], '沿用“过道 S091、洁具间 S343”的人工修正。请核对药房南通道与交通核 S105 的入口、S091 与 S105 是否有门，以及洁具间 S343 的门向；共墙不改作人员通行。')]
# 明确列入核对组的关系，编号本轮固定，不随分批回答重排。
rgroup={rid:g[0] for g in groups for rid in g[5].split()};pending=[];concept=[]
for r in d['relations']:
 if r['type']!='access' or r.get('openings'):continue
 if r['id'] in concept_ids or tuple(sorted((r['source'],r['target']))) in known_pairs:concept.append(r)
 else:
  if r['id'] not in rgroup:raise RuntimeError('未分组待核关系 '+r['id'])
  pending.append(r)
(out/'本轮核对映射.json').write_text(json.dumps({'groups':[{'number':g[0],'title':g[1],'bbox_upright_reference':g[2],'relation_ids':g[5].split(),'extra_space_ids':g[6],'question':g[7]} for g in groups],'pending_access_ids':[r['id'] for r in pending],'concept_access_ids':[r['id'] for r in concept]},ensure_ascii=False,indent=2)+'\n')
# 核对图全幅保留原图（只做显示转正），彩框/边栏/引线是外部叠加层。
scale=3672/1725;sy=3064/1440;left=650;top=150;canvas=Image.new('RGB',(4972,3364),'white');base=Image.open(out/'原图转正.png').convert('RGB');canvas.paste(base,(left,top));dr=ImageDraw.Draw(canvas)
fontpath='/System/Library/Fonts/Supplemental/Arial Unicode.ttf';font=ImageFont.truetype(fontpath,27);small=ImageFont.truetype(fontpath,23);large=ImageFont.truetype(fontpath,36)
dr.text((45,25),'03 晋中市第一人民医院｜13 组连通疑点核对总图',font=large,fill='#18314c');dr.text((45,80),'按片区自上而下核对；框选范围与同号问题一一对应。已确认名称保留，红点不在本图重复显示。',font=font,fill='#4b5563')
colors=['#a21caf','#d97706','#2563eb','#0891b2','#7c3aed','#15803d','#c026d3','#b45309','#0f766e','#dc2626','#4338ca','#be185d','#4d7c0f'];routes=[]
def pix(x,y):return left+x*scale,top+y*sy
for g,color in zip(groups,colors):
 num,title,bb,side,route,rr,extra,question=g;x0,y0,x1,y1=bb;dr.rectangle((*pix(x0,y0),*pix(x1,y1)),outline=color,width=5)
 px,py=pix(x0+3,y0+3);dr.rectangle((px,py,px+62,py+43),fill='white',outline=color,width=2);dr.text((px+5,py),num,font=large,fill=color)
 pts=[pix(x,y) for x,y in route];dr.line(pts,fill=color,width=3);dr.ellipse((pts[0][0]-5,pts[0][1]-5,pts[0][0]+5,pts[0][1]+5),fill=color);routes.append((num,LineString(route)))
 ty=pts[-1][1];lx=35 if side=='left' else 4370;bw=560;bh=120;dr.rounded_rectangle((lx,ty-bh/2,lx+bw,ty+bh/2),radius=8,fill='white',outline=color,width=3);dr.text((lx+16,ty-45),num+'｜'+title,font=font,fill=color);dr.text((lx+16,ty+1),'门向／直接连通待确认',font=small,fill='#334155')
 # 补充局部只作辅助：完整片区、保留同号，不重新编号。
 pad=8;crop=(round(max(0,x0-pad)*scale),round(max(0,y0-pad)*sy),round(min(1725,x1+pad)*scale),round(min(1440,y1+pad)*sy));base.crop(crop).save(out/f'{num}_核对局部.png')
cross=[]
for i,(a,la) in enumerate(routes):
 for b,lb in routes[i+1:]:
  if la.intersects(lb):cross.append((a,b))
# 同一西侧门诊问题的两处交通核另附同号小框，保持稳定 S 编号。
for sid in ['S029','S076']:
 pts=[(q[1]/scale,(3064-q[0])/sy) for q in ss[sid]['polygon_px']];xs,ys=zip(*pts);x0,y0,x1,y1=min(xs),min(ys),max(xs),max(ys);dr.rectangle((*pix(x0,y0),*pix(x1,y1)),outline=colors[8],width=5);px,py=pix(x0-8,y0-18);dr.text((px,py),'09 '+sid,font=small,fill=colors[8],stroke_width=2,stroke_fill='white')
canvas.save(out/'连通疑点_完整原图核对总图.png');preview=canvas.copy();preview.thumbnail((2200,1600));preview.save(out/'连通疑点_总图预览.png')
print('pending',len(pending),'concept without coordinates',len(concept),'leader intersections',cross)
if cross:raise RuntimeError('引线交叉，请修改')
rels=collections.Counter(r['type'] for r in d['relations']);types_n=collections.Counter(s['type'] for s in d['spaces']);openings=[o for r in d['relations'] for o in r.get('openings',[])];located=sum(bool(r.get('openings')) for r in d['relations']);unlocated=len(concept)+len(pending);removed=json.loads((out/'移除旧关系.json').read_text());oldmd=(out/'修改前备份'/'标注说明.md').read_text();oldparas=[p for p in oldmd.split('\n\n') if p.startswith('**本轮采用的概念名称：**') or p.startswith('**范围：**')]
relmap={r['id']:r for r in d['relations']};lines=['# 晋中市第一人民医院迁建项目｜一层标注与连通核对','', '**状态：名称已齐，连通关系补充稿；仍有 13 组疑点待确认，尚不称全图语义复核完成。** 原有 342 个独立空间全部保留，本轮新增漏标的医技通道 S344，现为 343 个空间／区域。同名房间不合并。','',*oldparas,'','**底图与坐标：**沿用具名高清原图，3064×3672 像素，原图字节不变。JSON 的边界、入口和开口坐标均对应未旋转的该原图；从旧 1440×1725 坐标逐轴同比例换算。SVG 仅转正显示，文字保持正向。旧 source.jpg 已移至本轮外部备份。','',f'**连接与开口：**{len(d["relations"])} 条关系：人员可达 {rels["access"]}、服务联系 {rels["service"]}、共墙 {rels["shared_wall"]}、建筑入口 {rels["entrance"]}。{len(openings)} 个实心红点，均为清晰门洞，对应 {located} 条 access；同一空间对的多个门并入同一关系。另有 {unlocated} 条无定位 access，其中 {len(concept)} 条为区域连续、半墙或节点切分的概念连通，{len(pending)} 条为保留的待核旧边。当前未为不清晰的无门开口编造坐标。','', '**待核旧边的使用边界：**下表明确列出的旧 access 仍待确认，不是本轮核实的连通真值；建模前应据表排除／屏蔽，未记录关系也不当负例。窗口仅记 service；共墙仅记 shared_wall。','', '**本轮补充：**修正 59 条跨房、角点接触或门向不符的旧 access（逐项备份于外部核对目录）；3 条柜台界面改为 service；补录清晰门位和缺失关系。原有 S001、S146／S147、S164、S207／S212、S317、S326、S337 的局部轮廓随本院图面修正，S344 补足医技南端漏标小通道。MRI、CT、DR 等明确影像空间归入 imaging；手术间归入 operating_room；会议室归入 conference；三处已明确不计室内面积的内院改用 courtyard／open_space。','', '**标准标签：**JSON 的 name 保留具体名称，type 使用共享代码；SVG 显示“S编号＋具体名称＋〔标准功能类别〕”。三处内院不参与面积归一化，室内 area_ratio 合计为 1；不保存平方米或像素面积。','', '**入口：**'+'、'.join(r['id']+' '+r['name'] for r in d['relations'] if r['type']=='entrance')+'。','', '**类型与数量：**'+'、'.join(f'{types[t]} {n}' for t,n in types_n.items())+'。','', '**成果：**[具名原图](./03_晋中市第一人民医院迁建项目_原图.jpg)、[标注.svg](./标注.svg)、[annotation.json](./annotation.json)。','', '## 13 组固定编号核对','', '读取顺序为片区自上而下，相邻问题集中；本轮 01—13 与片区、S 编号对应固定，分批回复后不重排。可直接填写本表“我的确认／备注”，或聊天回复 `01=……，02=……`。请说明“哪些 S 编号直接相通、从哪一侧进入”；无法辨认的项可继续保留待确认。','', '![完整原图连通疑点核对总图](../../临时核对/03_晋中市第一人民医院_开口补充_20261101/连通疑点_完整原图核对总图.png)','', '[打开高清总图](../../临时核对/03_晋中市第一人民医院_开口补充_20261101/连通疑点_完整原图核对总图.png)','', '| 核对号 | 连续片区与相关 S 编号 | 保留待核的旧关系 | 图面依据及需确认内容 | 我的确认／备注 | 核对号（重复） |','| --- | --- | --- | --- | --- | --- |']
for g in groups:
 num,title,bb,side,route,rr,extra,question=g;ids=set(extra)
 for rid in rr.split():
  if rid in relmap:ids.update([relmap[rid]['source'],relmap[rid]['target']])
 lines.append('| '+ ' | '.join([num,title+'；'+'、'.join(sorted(ids)),rr or '缺失路径待补，未预造连接',question+' 把握：低，待确认。','待确认',num])+' |')
lines+=['','## 同号局部及待核边明细','', '局部图仅补充阅读；总图保留全部空间相对关系。以下每条旧边只出现一次，确认前不作为已复核连接。','']
for g in groups:
 num,title,bb,side,route,rr,extra,question=g;lines += [f'### {num}｜{title}','',f'[同号局部](../../临时核对/03_晋中市第一人民医院_开口补充_20261101/{num}_核对局部.png)','']
 for rid in rr.split():
  r=relmap[rid];lines.append(f'- {rid}：{r["source"]} {ss[r["source"]]["name"]} ↔ {r["target"]} {ss[r["target"]]["name"]}；门位／直接通行待核。')
 if not rr:lines += ['- 本片区存在未记录的房间级通行路径，待用户确认后新增；不从相邻或共墙生成 access。']
 lines += ['']
lines+=['## 保留的人工内容与精度说明','', '此前已采用的 21 项概念功能名称全部保留。43 号收费处、56 号过道、左侧洁具间及上方取药服务范围的既有修正保留；完整修改前 MD 与全部旧文件位于外部备份，未覆盖用户历史材料。交通核和 EICU 仍按概念节点记录；不保存门宽、门扇形式、门禁权限或内部精确路线。','', '## 核验','', '结构、几何、共享类别、面积归一化和 SVG／JSON 开口对应检查通过；名称已齐。正式 `validate --check-dir` 的最终输出另存于外部核对目录。全图及门诊、中心供应、医技、急诊、病房楼密集局部已进行视觉检查。结构通过不能替代上列 13 组连通语义确认。','']
(stage/'标注说明.md').write_text('\n'.join(lines))
print('counts',dict(rels),'openings',len(openings),'located relations',located,'groups',len(groups))
