"""Formal and preservation checks, then install the reviewed three-file update."""
from pathlib import Path
from hashlib import sha256
import json,sys,re,shutil,xml.etree.ElementTree as ET
from shapely.geometry import Polygon,Point
OUT=Path(__file__).resolve().parent;BASE=OUT.parents[1]
PROJECT=BASE/'标注试样/16_浙江大学医学院邵逸夫医院下沙院区'
BACKUP=Path((OUT/'本轮备份路径.txt').read_text());STAGE=OUT/'待核验成果'
sys.path.insert(0,str(BASE/'临时核对/09-10_连通复核_20261102'))
from 连通工具 import annotation
A=json.loads((STAGE/'annotation.json').read_text());OLD=json.loads((BACKUP/'annotation.json').read_text())
def hashfile(p):return sha256(p.read_bytes()).hexdigest()
def rows(t):return [l for l in t.splitlines() if re.match(r'^\|\s*\d+\s*\|\s*S\d+\s*\|',l)]
for n in ['annotation.json','标注.svg','标注说明.md']:
 assert hashfile(PROJECT/n)==hashfile(BACKUP/n),'Live file changed; preserve current edits: '+n
assert rows((BACKUP/'标注说明.md').read_text())==rows((STAGE/'标注说明.md').read_text())
assert len(rows((STAGE/'标注说明.md').read_text()))==141
assert len(A['spaces'])==207 and not any(s['type']=='unknown' for s in A['spaces'])
assert {s['id'] for s in A['spaces']}==({s['id'] for s in OLD['spaces']}-{'S038','S125','S181','S182'})|{'S211'}
ss={s['id']:s for s in A['spaces']};assert ss['S037']['name']=='贵重药品' and ss['S124']['name']=='挂号收费'
assert all(not (r['source']=='S185' or r['target']=='S185') for r in A['relations'])
assert not any(r['type']=='access' and {r['source'],r['target']} in [{'S172','S159'},{'S206','S197'},{'S196','S197'},{'S072','S061'}] for r in A['relations'])
ns='{http://www.w3.org/2000/svg}';tree=ET.parse(STAGE/'标注.svg')
for s in A['spaces']:
 group=tree.find('.//'+ns+'g[@id="'+s['id']+'"]');text=''.join(t.text or '' for t in group.iter(ns+'text'))
 assert s['id'] in text and s['name'] in text and annotation.TYPE_NAMES[s['type']] in text,s['id']
for ref in re.findall(r'!\[[^\]]*\]\(([^)]+)\)',(STAGE/'标注说明.md').read_text()):assert (PROJECT/ref).resolve().is_file(),ref
assert hashfile(PROJECT/A['image']['file'])=='5ac85bf3fad75cdb757a34ee25269a7bda4edd0bddacc7e59c62975efdd4f08c'
assert hashfile(PROJECT/A['image']['file'])==hashfile(STAGE/A['image']['file'])
result,code=annotation.check(A,STAGE/'annotation.json',check_dir=True);assert code==0,result
(OUT/'正式校验.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
for p in OUT.glob('*.py'):assert len(p.read_text().splitlines())<=599,p
for n in ['annotation.json','标注.svg','标注说明.md']:shutil.copy2(STAGE/n,PROJECT/n)
result,code=annotation.check(A,PROJECT/'annotation.json',check_dir=True);assert code==0,result
assert len(list(PROJECT.iterdir()))==4
report=dict(formal=result,user_rows_preserved=141,unknown_names=0,spaces=207,access=230,service=9,entrances=16,
opening_points=193,critical_questions=['K01','K02'],all_connectivity_complete=False,source_image_unchanged=True,
removed_space_ids=['S038','S125','S181','S182'],new_corridor_id='S211',only_project16_changed=True)
(OUT/'交付核验.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
