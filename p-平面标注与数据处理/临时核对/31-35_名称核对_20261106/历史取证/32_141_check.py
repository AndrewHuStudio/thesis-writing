from pathlib import Path
import json,hashlib,xml.etree.ElementTree as ET
from collections import Counter
import pymupdf
from PIL import Image
P=Path('/Users/hushili/Documents/研究-论文写作/大论文/p-写作过程/标注试样/32_青岛大学附属医院东区病房综合楼');T=Path('/tmp/outpatient32-review')
a=json.loads((P/'annotation.json').read_text());meta=json.loads((T/'核对映射.json').read_text())
svg=P/'标注.svg';svgtext=svg.read_text().replace('门诊平面结构化标注','32号一层平面标注草稿');svg.write_text(svgtext)
r=ET.fromstring(svgtext);ns={'s':'http://www.w3.org/2000/svg'}
for s in a['spaces']:
 g=r.find(f".//s:g[@id='{s['id']}']",ns);assert g is not None
 visible=''.join(t.text or '' for t in g.findall('s:text',ns))
 assert s['id'] in visible
 assert (s['name'] if s['type']!='unknown' else '名称未确认') in visible
assert len(meta)==115
assert set(q['id'] for q in meta)==set(s['id'] for s in a['spaces'] if s['type']=='unknown')
assert [q['review'] for q in meta]==[f'{i:02d}' for i in range(1,116)]
sha=hashlib.sha256((P/a['image']['file']).read_bytes()).hexdigest()
assert sha=='bae1ea0f64925d3acb232ee6452cb63507db6eef984351c45b21f9f605365d38'
md=P/'标注说明.md';s=md.read_text();s=s.replace('# 平面标注概览','# 32 青岛大学附属医院东区病房综合楼｜一层标注草稿',1)
intro='''**楼层与范围：**图签为一层；本轮仅覆盖当前原图的本层建筑内轮廓，包括左翼小房间、右侧柜台和大厅、交通核及中央围合区域。图外轴网、比例和图例不入空间；东侧外凸的四处绿色附属矩形位于本轮室内轮廓外，未据颜色推定用途，暂不纳入室内统计。本稿不代表其他楼层或整院完成。

**功能范围：**交通核及设备井归建筑支持；走廊、大厅与可见候诊区归公共交通／服务。左翼成组大房间具有医技排布特征，底部重复小房具有门诊诊疗排布特征，均只作候选；临床、办公及柜台业务未读清的空间统一为 `unknown`、`scope: undetermined`。本图未确认住院病房，不因项目名含“病房综合楼”而套入住院用途。

**草稿精度：**183 个空间／区域不等于183间房，其中43个为连续开放大厅的几何分段，分段边界不表示隔墙。交通核按整体记录。8处绿色围合区域的用途及室内／露天／挑空属性待核，目前为 `unknown`，暂参与归一化，故面积占比仅为草稿暂算；确认露天或挑空后将按规则排除并重算。树形符号不直接证明露天。

**关系边界：**可达关系仅表达当前可见门口、开放通道与连续大厅；共墙和柜台不自动作为可达。柜台另存服务联系，不声明患者／医护权限。未记录的关系表示证据不足，不是不可达负例。入口采用图面位置和可辨用途，未读清业务名时用方位名。

**集中核对：**115项待确认，连续核对号及S编号映射、用途候选、依据与把握程度均在 `/tmp/outpatient32-review/`；可按 `01=名称，02=名称` 分批回复。本轮未完成正式名称校验；已确认答案后续保留并同步 JSON、SVG、MD。

'''
s=s.replace('未完成：115 个空间名称尚未确认。','未完成：115 个空间名称尚未确认。

'+intro,1);md.write_text(s)
doc=pymupdf.open(stream=svgtext.encode(),filetype='svg');page=doc[0]
pix=page.get_pixmap(matrix=pymupdf.Matrix(1.2,1.2),alpha=False);pix.save(T/'SVG_完整检查.png')
im=Image.open(T/'SVG_完整检查.png');im.resize((1100,round(im.height*1100/im.width))).save(T/'SVG_完整检查预览.png')
# SVG密集底部，包含可见编号和名称。
page.get_pixmap(matrix=pymupdf.Matrix(2.5,2.5),clip=pymupdf.Rect(375,2690+121.8,1040,2920+121.8),alpha=False).save(T/'SVG_密集局部检查.png')
print(json.dumps(dict(files=sorted(p.name for p in P.iterdir() if p.is_file()),source_sha256=sha,visible_labels=len(a['spaces']),unknown=len(meta),relations=Counter(r['type'] for r in a['relations']),indoor_ratio_sum=sum(s.get('area_ratio',0) for s in a['spaces'])),ensure_ascii=False,indent=2))
