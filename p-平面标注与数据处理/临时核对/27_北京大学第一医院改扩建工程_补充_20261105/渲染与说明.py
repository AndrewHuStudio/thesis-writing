from pathlib import Path
import importlib.util,json,copy,xml.etree.ElementTree as ET,os,re
import pymupdf
B=Path(__file__).resolve().parent;ROOT=B.parent.parent/'标注试样/27_北京大学第一医院改扩建工程'
sp=importlib.util.spec_from_file_location('at','/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts/annotation_tools.py');at=importlib.util.module_from_spec(sp);sp.loader.exec_module(at)
d=json.loads((ROOT/'annotation.json').read_text());u=copy.deepcopy(d);W=d['image']['width'];H=d['image']['height'];u['image'].update(width=H,height=W)
for s in u['spaces']:s['polygon_px']=[[y,W-1-x] for x,y in s['polygon_px']]
for r in u['relations']:
 if 'position_px' in r:r['position_px']=[r['position_px'][1],W-1-r['position_px'][0]]
 for o in r.get('openings',[]):o['position_px']=[o['position_px'][1],W-1-o['position_px'][0]]
at.render(u,ROOT/'annotation.json',ROOT/'标注.svg')
ns='{http://www.w3.org/2000/svg}';tree=ET.parse(ROOT/'标注.svg');rt=tree.getroot();im=rt.find('.//'+ns+'image');im.set('width',str(W));im.set('height',str(H));im.set('transform',f'matrix(0 -1 1 0 0 {W-1})')
# 圆点保留原图坐标属性，以显式旋转变换转正；文字标签在转正坐标中正常阅读。
for r in d['relations']:
 for o in r.get('openings',[]):
  og=rt.find('.//'+ns+'g[@data-opening-id="'+o['id']+'"]');circle=og.find(ns+'circle');circle.set('cx',str(o['position_px'][0]));circle.set('cy',str(o['position_px'][1]));circle.set('transform',f'matrix(0 -1 1 0 0 {W-1})')
  # 白色细描边在部分SVG渲染器中遮满字形，改为白底红字。
  label=og.find(ns+'text')
  for key in ['stroke','stroke-width','paint-order']:label.attrib.pop(key,None)
  label.set('font-size','8');x=float(label.get('x'));y=float(label.get('y'))
  rect=at.element('rect',{'x':x-1,'y':y-8,'width':24,'height':10,'fill':'white','fill-opacity':'.9','rx':1})
  og.insert(list(og).index(label),rect)
rt.findall(ns+'text')[0].text='27 北京大学第一医院改扩建工程｜一层空间与连通草稿'
for eid,bx,by in [('E004',2495,450),('E006',2235,465)]:
 eg=rt.find('.//'+ns+'g[@id="'+eid+'"]');rect=eg.find(ns+'rect');label=eg.find(ns+'text');line=eg.find(ns+'line')
 rect.set('x',str(bx));rect.set('y',str(by));label.set('x',str(bx+7));label.set('y',str(by+18));line.set('x2',str(bx+float(rect.get('width'))/2));line.set('y2',str(by+float(rect.get('height'))/2))
rt.find(ns+'g').append(at.txt(120,1780,'下方裁切平面不纳入本次标注。',24,'#64748b',True))
tree.write(ROOT/'标注.svg',encoding='unicode')
at.summary(d,B/'本轮概览.md')
summary=(B/'本轮概览.md').read_text().replace('# 平面标注概览','# 27 北京大学第一医院改扩建工程｜空间与连通补充草稿')
old=(B/'续作前备份/标注说明.md').read_text();scope=old.split('**本次范围：**',1)[1].split('未完成：',1)[0]
summary=summary.replace('\n\n未完成：','\n\n**本次范围：**'+scope+'未完成：',1)
rel=lambda name:os.path.relpath(B/name,ROOT)
parts=[summary,'\n## 本轮复核与剩余范围\n',
'已沿用55个稳定S编号，恢复首次发布的01—24核对号。名称尚未确认的24项继续为 `unknown`；候选只供填写，不写入核心JSON。普通数字1—6按本图图例记录为挂号大厅、取药大厅、挂号收费、药房、信息中心、办公。圈⑤仍待确认。',
'本轮补入 R054（S027—S037）、R055（S027—S032药房北门）、R056（S024—S026西侧门）；S026另一扇门仍经 R035 连东翼走道。更正 R019 为 S005—S007、R046 为 S054—S053，R010 为挂号收费 S014—办公 S019。西南楼梯通过 S018 与办公区连通，撤下缺乏直接门洞依据的 R015。',
'主网络边界复核：S022补入西北楼梯南侧接近区；S024/S027交界移至东翼可见分隔门，仍保留原S编号并重新归一化室内面积。E005更正为直接连接东南前室S054；E004保留东北楼梯出口，新增E006连接东北走道S027的外门。',
'**布局推断／区域连续：**R013（S018—S019）依据楼梯南侧公共带向标6办公区域连续；R024、R028为大厅与整体交通核的概念联系；R027为两个大厅之间的连续开放区。这些关系无虚构门位，也不表示用户已确认。',
'**本轮不细究的内部细节：**S031、S034、S045、S050、S052等小间／竖井的内部检修路径与未辨清门位；目前缺乏可靠通行依据者不强行补边。S015属于会影响主要可达网络的独立长条空间，另列K02。未记录的关系不作为不相通或训练负例。',
'药房长界面没有充分的窗口服务证据，暂不添加 `service`。E002/E003旧坐标实际落在南侧门斗两侧门上，先撤下错误的外部接口，编号保留；南侧外部接口按K01确认后再恢复。',
'\n## 名称核对：在本文件直接填写\n',
'保持原核对号和S编号。可修改“预估名称（可改）”并在“我的确认／备注”填“已确认”；接受预估时只填“已确认”即可，也可直接写实际名称。无可靠候选的项可自由填写。可分批回答，例如 `01=办公，02=清洁间`。未填写不视为确认。',
'![27号完整核对总图]('+rel('27_完整核对总图.png')+')',
'[打开原图](27_北京大学第一医院改扩建工程_原图.jpg)｜[查看空间与红点SVG](标注.svg)']
mapping=json.loads((B/'固定核对映射.json').read_text())
groups=[('01','西北办公旁独立间',[1]),('02-04','西北卫生间与楼梯南侧',[2,3,4]),('05-07','西侧交通核旁与收费区西北',[5,6,7]),('08-09','西侧长条区与西南支持区',[8,9]),('10-13','东北办公与楼梯周边',[10,11,12,13]),('14-16','药房旁小间及东翼办公',[14,15,16]),('17-18','东侧信息中心旁小间',[17,18]),('19-24','东南圈⑤与支持空间',[19,20,21,22,23,24])]
for name,title,nums in groups:
 parts += [f'\n### {name}｜{title}\n',f'![{name}：{title}]('+rel(f'名称_{name}_局部.png')+')',f'[无标记原图对照]('+rel(f'名称_{name}_无标记.png')+')',
 '| 核对号 | S编号 | 预估名称（可改） | 备选名称 | 依据与把握 | 我的确认／备注 | 核对号（重复） |',
 '| --- | --- | --- | --- | --- | --- | --- |']
 for n in nums:
  m=mapping[n-1];parts.append('| '+' | '.join([m['check'],m['id'],m['candidate'],m['alternative'],m['basis']+' 把握：'+m['confidence']+'。','待确认',m['check']])+' |')
parts += ['\n## 关键连通疑点：只确认以下两项\n',
'下列两项需要确认，因为当前图像仍允许不同的主要可达解释；先保留判断和局部图，不把预填判断视为你的确认。',
'\n### K01｜南侧S025的外部接口\n',
'![K01：南侧S025与两个大厅]('+rel('K01_南侧入口范围.png')+')',
'[无标记原图对照]('+rel('K01_无标记.png')+')',
'**问题：**S025是否是南侧入口空间，由南侧室外进入，再通过两侧门分别通向取药大厅S022、挂号大厅S024？',
'**我的判断：**倾向这一解释；两侧门与大厅的位置明确，南侧最外边线更像入口台阶／雨篷界线。待确认后将一个南侧外部接口接入S025，不再把两侧内部门重复当成两个外部入口。',
'**我的确认／备注：**待填写（可填“同意”，或说明S025实际范围及从室外先进入哪个空间；不要求具体门位）',
'\n### K02｜西侧长条空间S015的唯一入口\n',
'![K02：西侧S015与相邻走道]('+rel('K02_西侧狭长空间入口.png')+')',
'[无标记原图对照]('+rel('K02_无标记.png')+')',
'**问题：**S015直接通向S018西南走道、S013／S014，还是另有出入口？',
'**我的判断：**旧草稿记录S015—S018，但放大后长条区东侧分隔线基本连续；S018下端双门可能只是走道自身门组，不能据此确认穿入S015。暂撤下R014，等确认直接相连空间。',
'**我的确认／备注：**待填写（写S015直接相通的空间名称／S编号；若它不应作为室内独立空间，也请说明范围）',
'\n## 当前完成状态\n',
'原图及旧JSON/SVG/MD已备份于正式样本目录外。当前仍为草稿：24项名称、K01南侧外部接口和K02西侧长条区入口尚未确认。草稿结构校验通过不等于正式打标完成。核对图、映射、备份及本轮记录均存于持久临时核对目录；正式样本目录仍仅含原图、JSON、SVG、MD四文件。']
text='\n\n'.join(parts)+'\n'
text=re.sub(r'\|\n\n(?=\|)','|\n',text)
text=re.sub(r'\n{3,}','\n\n',text)
(ROOT/'标注说明.md').write_text(text)
doc=pymupdf.open(ROOT/'标注.svg');page=doc[0]
for name,clip,scale in [('全图',None,1),('西翼',pymupdf.Rect(100,630,1120,1540),2),('东翼',pymupdf.Rect(2020,620,2700,1550),2)]:
 page.get_pixmap(matrix=pymupdf.Matrix(scale,scale),clip=clip,alpha=False).save(B/f'SVG_{name}_检查.png')
print('rendered SVG and editable MD')
