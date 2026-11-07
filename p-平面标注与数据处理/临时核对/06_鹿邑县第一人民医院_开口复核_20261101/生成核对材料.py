from pathlib import Path
import json,base64,html,collections,hashlib
from xml.etree.ElementTree import Element,SubElement,ElementTree
P=Path(__file__).resolve().parent;stage=P/'待核验成果';d=json.loads((stage/'annotation.json').read_text());old=json.loads((P/'修改前备份/annotation.json').read_text());ss={s['id']:s for s in d['spaces']}
project=P.parent.parent/'标注试样/06_鹿邑县第一人民医院整体迁建项目';src=project/d['image']['file'];raw=base64.b64encode(src.read_bytes()).decode()
NS='http://www.w3.org/2000/svg'
def el(parent,name,attrs={},text=None):
 e=SubElement(parent,name,{k:str(v) for k,v in attrs.items()});e.text=text;return e
def tx(root,x,y,lines,size=24,color='#18314c'):
 t=el(root,'text',{'x':x,'y':y,'font-size':size,'font-family':'Arial, PingFang SC, sans-serif','fill':color})
 for i,line in enumerate(lines):el(t,'tspan',{'x':x,'dy':0 if i==0 else size*1.5},line)
 return t
root=Element('svg',{'xmlns':NS,'width':'5944','height':'5850','viewBox':'0 0 5944 5850'})
el(root,'rect',{'width':5944,'height':5850,'fill':'#f5f7fa'})
tx(root,40,65,['06 鹿邑县第一人民医院｜新增连通待确认 L08—L10'],38)
tx(root,40,120,['L01—L07沿用原核对总图与原表；本图只补充3处新疑点。引线仅定位，不表示人员通行。'],25,'#b45309')
ox,oy=950,200
el(root,'image',{'x':ox,'y':oy,'width':4044,'height':5586,'href':'data:image/jpeg;base64,'+raw})
tx(root,40,300,['名称状态：已完成','连通状态：仍待核','原S编号、原名称及填写保留'],27)
tx(root,40,540,['回复格式：','L08=通向S编号／无门','L09=可穿行／不可穿行','L10=入口方向及所通S编号'],25)
items=[('L08',['S050 男更：人员入口','北侧是否通S044？','若经其他房间进入，请写S编号。'],[(2848,1194),(2910,1194),(2910,1290),(2848,1290)],(2865,1196),1100,'#c2410c'),('L09',['S057／S058 休闲区间分隔','两区能否直接穿行？','可穿行时请指出开口位置或形式。'],[(2023,1695),(2048,1695),(2048,1835),(2023,1835)],(2035,1765),1700,'#0f766e'),('L10',['S276 值班诊室：人员入口','入口朝S262、S270或其他空间？','目前不按邻接补入确定access。'],ss['S276']['polygon_px'],(2686,3955),3900,'#7c3aed')]
for ident,lines,poly,(x,y),ly,col in items:
 el(root,'polygon',{'points':' '.join(f'{a+ox},{b+oy}' for a,b in poly),'fill':col,'fill-opacity':'.1','stroke':col,'stroke-width':5})
 el(root,'rect',{'x':x+ox-45,'y':y+oy-36,'width':90,'height':38,'rx':4,'fill':'white','stroke':col,'stroke-width':3});tx(root,x+ox-37,y+oy-8,[ident],26,col)
 target=(x+ox,y+oy);labelx=5075;labely=ly+oy
 el(root,'polyline',{'points':f'{target[0]},{target[1]} 5020,{target[1]} {labelx},{labely+60}','stroke':col,'stroke-width':3,'fill':'none'})
 el(root,'rect',{'x':labelx,'y':labely,'width':820,'height':190,'rx':8,'fill':'white','stroke':col,'stroke-width':3})
 tx(root,labelx+20,labely+40,[ident+'｜'+lines[0]]+lines[1:],26,col)
ElementTree(root).write(P/'新增连通核对总图_L08-L10.svg',encoding='unicode')
# 只对本图新增疑点生成局部；原L01-L07材料保持原样。
for ident,_,poly,(x,y),ly,col in items:
 mnx=min(a for a,b in poly);mny=min(b for a,b in poly);mxx=max(a for a,b in poly);mxy=max(b for a,b in poly)
 left=max(0,mnx-130);top=max(0,mny-130);w=mxx-left+130;h=mxy-top+130
 r=Element('svg',{'xmlns':NS,'width':str(w*2),'height':str((h+65)*2),'viewBox':f'{left} {top-65} {w} {h+65}'})
 el(r,'rect',{'x':left,'y':top-65,'width':w,'height':h+65,'fill':'white'});tx(r,left+8,top-35,[ident+'｜原图定位；彩框不是通行口'],17,col)
 el(r,'image',{'x':0,'y':0,'width':4044,'height':5586,'href':'data:image/jpeg;base64,'+raw})
 el(r,'polygon',{'points':' '.join(f'{a},{b}' for a,b in poly),'fill':col,'fill-opacity':'.08','stroke':col,'stroke-width':2})
 im=r.find('image');background=r.find('rect');r.remove(im);r.remove(background);r.insert(0,background);r.insert(1,im);el(r,'rect',{'x':left,'y':top-65,'width':w,'height':65,'fill':'white'});title=r.find('text');r.remove(title);r.append(title)
 ElementTree(r).write(P/(ident+'_局部.svg'),encoding='unicode')
oldmd=(P/'修改前备份/标注说明.md').read_text();kept=oldmd[oldmd.index('## 连通关系待确认（L01—L07）'):]
generated=(stage/'标注说明.md').read_text().replace('# 平面标注概览','# 06 鹿邑县第一人民医院整体迁建项目首层标注（连通待核）',1).replace('空间名称已齐；结构与关系仍以原图及人工核对为依据。','**名称状态：已完成。连通性复核状态：未完成，L01—L10共10项待确认。** 本轮已补入可辨门洞与开口，尚未确认的连接不写成确定人员可达。')
extra='''
**名称与编号：**原289个空间的S编号、名称、类别全部保留；补入S299“影像登记东侧通道”，用于登记柜台与片库门之间的实际短通行带，未改写既有房名。JSON使用共享英文类别，SVG显示编号、具体名称和标准中文类别。

**本轮修订：**人员门与服务柜台分别记录；同一空间对的多门已合并在同一关系的`openings`内。纠正急诊值班室、影像交通核、儿科办公室等直接目标；将注射间南侧连续隔墙记为共墙，将护士站柜台侧记为服务联系。三条证据不足的既有access移至L08—L10，未作为已确认事实保留。

**概念连通：**60条人员可达关系未画定位点，主要是大厅分区连续、半墙工作区及交通核整体连接。无点不表示不相通；服务窗口、共墙和L01—L10待确认连接均不作为人员门。未记关系不自动等于不可达或训练负例。

**中庭与面积：**室内中庭B仍按既有室内口径计面积，但是否可步入继续由L02确认；露天内院A及药房北侧露天内院均为`courtyard/open_space`，不计室内面积，不作为穿越通道。

**核验边界：**正式`validate --check-dir`检查名称、类别、几何、面积和红点与JSON的一致性；不替代原图门洞语义判读。当前仍是连通待核成果，不能据结构通过宣布本图全部完成。原图字节保持不变，备份及检查图均在项目外。

[具名标注图](标注.svg) · [原图](06_鹿邑县第一人民医院整体迁建项目_原图.jpg) · [本轮关系明细](../../临时核对/06_鹿邑县第一人民医院_开口复核_20261101/关系明细.md)

'''
new='''
## 新增连通待确认（L08—L10）

以下编号续接L01—L07，不改变原01—64名称核对映射。可在确认栏填写，或在聊天中按`L08=……，L09=……，L10=……`回复。新旧10项可一次或分批确认；未回答项继续待确认。

![新增连通核对总图 L08—L10，完整原图](../../临时核对/06_鹿邑县第一人民医院_开口复核_20261101/新增连通核对总图_L08-L10.png)

| 核对号 | 空间 | 候选去向／处理 | 图面依据与待确认点 | 我的确认／备注 | 核对号（重复） |
| --- | --- | --- | --- | --- | --- |
| L08 | S050 男更 | 通S044医保／新农合后廊／经其他空间进入 | 原R043直接连S044；放大后北墙人员开口未辨清，不能以相邻视为门。请写人员实际入口及直接所通S编号。 | 待确认 | L08 |
| L09 | S057／S058 休闲区 | 两区直接可穿行／分隔不可穿行 | 原R247直接连接两区；两区之间竖向分隔线连续，是否为可开启界面未辨明。若可通，请指出开口或分隔形式。 | 待确认 | L09 |
| L10 | S276 值班诊室 | 通S262儿科诊区通道／S270男厕所侧／其他空间 | 原R212直接连S262；北、东角门线较密，无法确定开门界面及直接目标；不凭邻接补边。名称继续保留。 | 待确认 | L10 |

[L08局部](../../临时核对/06_鹿邑县第一人民医院_开口复核_20261101/L08_局部.png) · [L09局部](../../临时核对/06_鹿邑县第一人民医院_开口复核_20261101/L09_局部.png) · [L10局部](../../临时核对/06_鹿邑县第一人民医院_开口复核_20261101/L10_局部.png)
'''
(stage/'标注说明.md').write_text(generated+'\n'+extra+kept+new)
# 外部明细不是另一张需重复填写的表。
lines=['# 06号本轮人员开口与关系明细','','名称与标准类别来自本图当前JSON。疑点只在正式MD填写；本表无需填写。','','| 关系 | 空间对 | 类型 | 开口 |','| --- | --- | --- | --- |']
for r in d['relations']:
 a=r['source'];b=r['target'];label=(a+' '+ss[a]['name'] if a else '外部')+' ↔ '+b+' '+ss[b]['name'];ops='；'.join(f"{o['id']} {o['kind']} {o['position_px']}" for o in r.get('openings',[])) or ('E入口 '+str(r['position_px']) if r['type']=='entrance' else '未定位红点')
 lines.append(f"| {r['id']} | {label} | {r['type']} | {ops} |")
(P/'关系明细.md').write_text('\n'.join(lines)+'\n')
# 验证原七项的可编辑内容未被改动。
assert kept in (stage/'标注说明.md').read_text()
assert all(ss[s['id']]['name']==s['name'] and ss[s['id']]['type']==s['type'] for s in old['spaces'])
print('original names and L01-L07 tables preserved')
