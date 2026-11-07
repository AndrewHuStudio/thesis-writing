from pathlib import Path
from collections import Counter
import xml.etree.ElementTree as ET
import json, re, shutil, hashlib

ROOT = Path('/Users/hushili/Documents/研究-论文写作/大论文')
SAMPLE = ROOT/'p-平面标注与数据处理/标注试样/13_天津市中心妇产科医院迁址新建工程'
WORK = Path(Path('/tmp/plan13-workpath').read_text())
STAGE = WORK/'待核验成果'
NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('',NS)
ET.register_namespace('xlink','http://www.w3.org/1999/xlink')
tree = ET.parse(STAGE/'标注.svg')
root = tree.getroot()
groups = [e for e in root.iter() if e.get('data-opening-id')]
obstacles = []
for e in root.iter('{'+NS+'}rect'):
    if all(e.get(k) for k in ['x','y','width','height']):
        x,y,w,h = [float(e.get(k)) for k in ['x','y','width','height']]
        obstacles.append((x-1,y-1,x+w+1,y+h+1))
points = [(float(g.find('{'+NS+'}circle').get('cx')),float(g.find('{'+NS+'}circle').get('cy'))) for g in groups]
placed = []
def overlap(a,b):
    return max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
for g,(x,y) in zip(groups,points):
    t = g.find('{'+NS+'}text')
    width,height = 23,11
    candidates = []
    for dy in [-15,5,-27,17,-39,29]:
        for dx in [6,-29,-12,18,-41]:
            b = (x+dx,y+dy,x+dx+width,y+dy+height)
            if b[0]<0 or b[1]<0:continue
            point_hits = sum(b[0]-4<px<b[2]+4 and b[1]-4<py<b[3]+4 for px,py in points)
            score = sum(overlap(b,o) for o in obstacles)*2+sum(overlap(b,o) for o in placed)*50+point_hits*10000+abs(dx)*.05+abs(dy)*.06
            candidates.append((score,b))
    _,b = min(candidates)
    placed.append(b)
    bg = ET.Element('{'+NS+'}rect',{'x':str(b[0]),'y':str(b[1]),'width':str(width),'height':str(height),'rx':'1.4','fill':'white','fill-opacity':'.94'})
    g.insert(list(g).index(t),bg)
    t.set('x',str(b[0]+2));t.set('y',str(b[1]+8.4))
    t.set('font-size','8');t.set('fill','#b91c1c');t.set('stroke','none')
    t.attrib.pop('stroke-width',None);t.attrib.pop('paint-order',None)
tree.write(STAGE/'标注.svg',encoding='utf-8',xml_declaration=True)

j = json.loads((STAGE/'annotation.json').read_text())
c = Counter(r['type'] for r in j['relations'])
op = [o for r in j['relations'] for o in r.get('openings',[])]
located = sum(bool(r.get('openings')) for r in j['relations'])
prefix = '../../临时核对/13_天津市中心妇产科医院迁址新建工程/'+WORK.name
md = (SAMPLE/'标注说明.md').read_text()
md = md.replace('门洞与主要连通尚待复核，整图仍为草稿。','本轮已完成概念层级的主要连通复核并恢复清晰门洞红点；两项暂缓名称仍使整图保持草稿。')
md = md.replace('原01—66核对号、S编号、轮廓、面积、层级及scope保持稳定。','名称同步时保留原01—66核对号、S编号、轮廓、面积、层级及scope；本次连通续作的局部轮廓修订另见下节。')
start = md.index('**完成边界：**');end = md.index('\n\n',start)
md = md[:start]+'**名称同步阶段边界：**前轮已完成19项明确名称同步；当时为202个空间、164条关系、0个开口定位点。以下“门洞与主要连通复核”记录本次续作后的实际状态；历史填写和名称同步记录继续保留。'+md[end:]
start = md.index('**本轮校验：**');end = md.index('\n\n',start)
md = md[:start]+'**名称同步阶段校验：**前轮名称同步的结构检查无错误，仍有S137、S138两项暂缓名称；当时只核对名称显示。本次连通关系、局部轮廓和门洞显示的校验结果见下节。'+md[end:]

section = f'''## 门洞与主要连通复核（2026-11-03 续作）

**本轮结果：**逐片核对放射科、药房支持、急诊、门诊各段、医院街、大厅、交通核与7个入口。当前为202个空间、{len(j['relations'])}条关系：{c['access']}条人员可达、3条服务联系、7条入口连接。定位{len(op)}个红点（{sum(o['kind']=='door' for o in op)}个门洞、1个无门开口），对应{located}条人员可达关系；另22条为无门位定位的概念连通。P编号仅用于门洞／开口，E编号继续用于建筑入口。

**变更范围：**新增49条有图面依据的人员可达关系，修正9条既有关系的直接相连空间，撤除R035、R048、R140三条重复或跨过中间空间／实墙的关系。既有R、S编号不重排，新增关系从R158续编。E001污物出口的直接相连空间改为S004交通核，经R017进入主走道；其余入口保留。为使通道支段和门口所在单元对应，修订12个既有空间的局部轮廓并重新归一化室内相对面积；未新增房间、未修改名称／类别／层级／scope。

**关键修正及依据：**

| 片区 | 同步到annotation.json的实际连接 | 图面依据 |
| --- | --- | --- |
| 放射科 | CT前区—S006—S011；补控制室、暗室、设备间与横走道的门；值班室S030改接S034 | 可辨门扇及连续横通道；CT前区连续连接作为布局推断，不虚构门位 |
| 药房北侧 | 输液药房S055、空调机房S054、门诊接待S063直接接医院街S042；S045经S047接S046 | 三处门分别开向医院街；病案存放东门开向阅览室，而非北侧走道 |
| 药房内部 | 补S046—S061、S046—S068；S060、S065接S061内通道；保留取药服务联系 | 中药房北侧双扇门清楚；西药房与西侧内部通道连续；服务窗口不产生通行点 |
| 急诊 | S129抢救厅—S139—S140—S131；补S125电梯厅—医院街与注射室南门 | 三段通道之间及抢救厅南门均有可辨开口；不跨中间过道直连 |
| 门诊西段 | VIP诊室经VIP服务厅接候诊厅；留观／更衣／脱衣接S096；绒毛取材室经留观进出 | 图面门扇与局部走道组织；PCR前区归入既有候诊通道，不扩展为各检验室互通 |
| 门诊中东段 | 中部楼梯S171接医院街；产前教育S189保留医院街出入口，取消穿过南墙直达S195的关系 | 楼梯西侧有开口；产前教育与新生儿候诊厅之间为连续墙线 |

**概念连通与布局推断：**大厅／医院街／候诊厅的连续片区、药房西侧内部通道、CT南侧前区及整体交通核按图面连续组织保留可达关系；不能定位独立门洞的地方不画红点。S165与S164只表示卫生间组前室和内部单元的概念连接，S077只记录电梯组整体朝向医院街，不逐个虚构电梯门位。这些判断由本轮图面复核得出，不写成用户已确认。

**本轮不细究的内部细节：**S069、S071、S073、S074、S092、S110、S161的精确进出路径，以及暂缓名称的S137、S138，未补证据不足的通行关系；不以共墙、柜台、家具或服务窗推导人员可达。它们未进入当前主可达分量不表示物理上不能通行，也不能作为负样本。局部卫生间、设备小间和检验支持小间内部路线不逐项提问。

**主要连通结论：**所有既有大厅／通道、交通核、半墙服务区和功能块均能沿已记录的人员可达关系接入医院街所在主分量；这只是漏连检查，语义判断仍以逐片原图复核为依据。本轮目标层级无新增关键连通待确认问题。S137、S138继续按用户备注暂缓名称，整图不宣称名称齐全或最终打标完成。

**核验：**正式`validate --check-dir`检查结构、非重叠轮廓、面积归一化及SVG红点与JSON的编号／坐标／空间对对应；`valid=true`、`errors=[]`，`names_complete=false`仍仅为S137、S138（退出码2）。已检查最新SVG全图及七片密集局部，P标签采用红字白底显示；原图哈希、200个既定名称及原66项填写保持一致。

[本轮修改前备份]({prefix}/修改前备份/标注说明.md) · [连通修订依据]({prefix}/连通修订依据.json) · [打开更新后全图]({prefix}/连通更新_全图.png)

### 放射科：门洞与横向走道

![放射科北段门洞及编号]({prefix}/A_标注.png)

![放射科南段门洞及编号]({prefix}/B_标注.png)

### 药房支持与急诊：真实进出方向

![药房支持区门洞及编号]({prefix}/C_标注.png)

![急诊及交通核门洞和通道连接]({prefix}/D_标注.png)

### 门诊西段、中段及东段

![门诊西段门洞及取材检验前区]({prefix}/E_标注.png)

![门诊中段及中部楼梯接口]({prefix}/F_标注.png)

![门诊东段及康复治疗中心接口]({prefix}/G_标注.png)

'''
md = md.replace('## 原66项固定核对表',section+'## 原66项固定核对表',1)
md = md.replace('整张图仍为标注草稿，门洞定位及主要连通关系尚待复核。','整张图因两项暂缓名称仍为标注草稿；本轮门洞定位及主要连通复核结果见前节。')
md = re.sub(r'\*\*连接关系：\*\*[^\n]+',f'**连接关系：**{len(j["relations"])}条，人员可达{c["access"]}条、服务联系3条、入口连接7条；{len(op)}个已定位开口对应{located}条人员可达关系，22条概念连通无定位红点。',md)
md = md.replace('整图尚未完成门洞与连通复核。','本轮主要连通及清晰门洞已复核，名称仍按用户备注暂缓。')
md = md.replace('当前尚无门洞近似定位点；后续应回看原图记录清晰门洞／开口。',f'本轮已从原图定位{len(op)}个清晰门洞／开口并同步SVG红点；概念连接和服务窗口不虚构门位。')
md = md.replace('本轮仅同步明确填写的名称及类别，门洞定位、连通语义及整图最终核验仍未完成。','本轮续作已同步主要连通关系和清晰门洞并完成结构与视觉检查；两项暂缓名称仍保留unknown，整图维持草稿状态。')
# Historical user entries must remain byte-identical even while prose is updated.
def answer_rows(text):
    return [line for line in text.splitlines() if re.match(r'\|\s*\d{2}\s*\|\s*S\d{3}\s*\|',line)]
assert answer_rows(md)==answer_rows((SAMPLE/'标注说明.md').read_text())
assert len(answer_rows(md))==66
(STAGE/'标注说明.md').write_text(md)
shutil.copy2('/tmp/continue_plan13.py',WORK/'连通增量.py')
shutil.copy2('/tmp/finalize_plan13.py',WORK/'生成标注与说明.py')
print(json.dumps({'openings':len(op),'located_access':located,'relations':dict(c),'preserved_answer_rows':66,'label_boxes':len(placed)},ensure_ascii=False))
