from pathlib import Path
import sys,subprocess,json,hashlib,collections,xml.etree.ElementTree as ET
from shapely.geometry import Polygon
from PIL import Image
ROOT=Path('/Users/hushili/Documents/研究-论文写作/大论文');OUT=ROOT/'p-写作过程/标注试样/08_青岛西海岸医疗中心';TMP=ROOT/'p-写作过程/临时核对/08_青岛西海岸医疗中心_20261029';J=OUT/'annotation.json';T='/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts/annotation_tools.py'
for cmd,rest in [('normalize',[]),('render',['--output',str(OUT/'标注.svg')]),('summary',['--output',str(OUT/'标注说明.md')])]:
 r=subprocess.run([sys.executable,T,cmd,str(J),*rest],capture_output=True,text=True);(TMP/(cmd+'.log')).write_text(r.stdout+r.stderr);assert r.returncode==0,(cmd,r.stdout,r.stderr)
D=json.loads(J.read_text());K=json.loads((TMP/'key_to_id.json').read_text());R=json.loads((TMP/'核对对应.json').read_text())
md=OUT/'标注说明.md';text=md.read_text();text+='''

**本图范围：**仅 08 号这张平面；包括北部大空间与出入院服务、东北部服务／输液候选区、西侧医技、儿科、急诊以及中央公共交通。西南片区的具体科别尚未确定，暂用独立范围 `southwest_clinical`，不并入已确定的普通门诊科别。

**草稿精度：**按图面墙线与功能范围作概念级轮廓；细小墙体、门扇和交通核内部路径不作施工级描绘。SVG 中黄色区域保持“名称未确认”；候选用途、依据、把握程度及核对号只存于临时核对材料，不作为核心事实标签。

**面积暂定条件：**北侧绿色斜线范围及四个白色庭院／上空范围尚未确认室外、屋面或挑空属性，目前作为 unknown 暂参与草稿归一化；不能将当前比例理解为已核定的室内构成。确认室外或挑空后，再按 Skill 排除并重新归一化。图上明确的绿化已排除。

**关系边界：**仅记录图上可见开口／连续通道及明确柜台联系；相邻房间不自动相连。尚未逐一核实的房门连接继续缺省，缺失关系不表示不可达。名称确认后仍需复查与用途相关的通行关系。
'''
text+='\n**属性待确认的范围：**'+ '、'.join(K[k] for k in ['n_roof','c_uppercourt','c_white','c_eastcourt','e_white'])+'。\n'
text+='\n**核对材料：**位于同级工作区的 `p-写作过程/临时核对/08_青岛西海岸医疗中心_20261029`；按固定核对号 01—210 支持分批确认。\n';md.write_text(text)
checks={}
for name,flags,expected in [('正式校验',['--check-dir'],2),('草稿结构校验',['--allow-incomplete','--check-dir'],0)]:
 r=subprocess.run([sys.executable,T,'validate',str(J),*flags],capture_output=True,text=True);q=json.loads(r.stdout);q['exit_code']=r.returncode;(TMP/(name+'.json')).write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n');assert r.returncode==expected,(name,r.stdout,r.stderr);checks[name]={k:v for k,v in q.items() if k!='pending_name_ids'}
root=ET.parse(OUT/'标注.svg').getroot();ns={'s':'http://www.w3.org/2000/svg'};groups={g.get('id'):g for g in root.findall('.//s:g',ns)}
for s in D['spaces']:
 g=groups[s['id']];visible=''.join(t.text or '' for t in g.findall('s:text',ns));assert s['id'] in visible,s['id'];assert ('名称未确认' if s['type']=='unknown' else s['name']) in visible,(s['id'],visible)
P={s['id']:Polygon(s['polygon_px']) for s in D['spaces']}
for r in D['relations']:
 if r['type']=='access':assert P[r['source']].distance(P[r['target']])<=5,(r['id'],'unrepresented gap')
source=OUT/D['image']['file'];original=ROOT/'i-医院门诊平面'/D['image']['file'];digest=hashlib.sha256(source.read_bytes()).hexdigest();assert digest==hashlib.sha256(original.read_bytes()).hexdigest(),'source differs from original library copy'
assert len(list(OUT.iterdir()))==4
assert len(R)==210 and len({q['sid'] for q in R})==210
assert {q['sid'] for q in R}=={s['id'] for s in D['spaces'] if s['type']=='unknown'}
from PIL import Image
reviewcheck=json.loads((TMP/'核对图校验.json').read_text());assert reviewcheck['numbers_continuous'] and all(q['crossings']==0 and q['anchor_errors']==0 for q in reviewcheck['reports'])
summary={'spaces':len(D['spaces']),'pending':len(R),'relation_counts':dict(collections.Counter(r['type'] for r in D['relations'])),'area_ratio_sum':sum(s.get('area_ratio',0) for s in D['spaces']),'source_sha256':digest,'source_matches_library':True,'svg_visible_labels':len(D['spaces']),'four_files':[p.name for p in OUT.iterdir()],'overview_size':Image.open(TMP/'核对总图_高清.png').size,'checks':checks}
(TMP/'交付核验.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');print(json.dumps(summary,ensure_ascii=False,indent=2))
# Actual SVG render, including CJK, for full + dense visual inspection.
import pymupdf
p=pymupdf.open(OUT/'标注.svg')[0];p.get_pixmap().save(TMP/'标注_完整.png');im=Image.open(TMP/'标注_完整.png');im.resize((1190,1717)).save(TMP/'标注_完整预览.png');im.crop((340,2295,1030,2855)).resize((1380,1120)).save(TMP/'标注_密集南部.png');im.crop((1140,1260,2120,2010)).save(TMP/'标注_密集儿科.png')
