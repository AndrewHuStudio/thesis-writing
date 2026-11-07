from pathlib import Path
from collections import Counter
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

from PIL import Image
from shapely.geometry import Polygon, Point
import markdown

WORK = Path(__file__).resolve().parent
PROJECT = WORK.parents[2] / 'p-平面标注与数据处理/标注试样/11_寿县县医院新区'
BACKUP = sorted(WORK.glob('修改前备份_*'))[0]
STAGE = WORK / '待核验成果'
SKILL = '/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts/annotation_tools.py'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(text):
    result = []
    for line in text.splitlines():
        cells = [html.unescape(v.strip()) for v in line.strip('|').split('|')]
        if len(cells)==8 and re.fullmatch(r'\d+',cells[0]) and re.fullmatch(r'S\d+',cells[1]):
            result.append(cells)
    return result


def validate(folder):
    result = subprocess.run([sys.executable, SKILL, 'validate', str(folder/'annotation.json'), '--check-dir'], capture_output=True, text=True, check=False)
    report = json.loads(result.stdout)
    assert report['valid'] and report['errors'] == []
    assert result.returncode == 2 and not report['names_complete']
    assert set(report['pending_name_ids']) == {'S001', 'S035'}
    return {'exit_code': result.returncode, **report}


data = json.loads((STAGE/'annotation.json').read_text())
spaces = {s['id']: s for s in data['spaces']}
original_text = (BACKUP/'标注说明.md').read_text()
current_text = (STAGE/'标注说明.md').read_text()
original_rows = rows(original_text)
assert len(original_rows) == 37 and original_rows == rows(current_text)
assert all(s['name'] and s['name'] != '名称未确认' for s in data['spaces'])
assert 'S029' not in spaces and len(spaces) == 194
for row in original_rows:
    if row[1] != 'S029':
        assert spaces[row[1]]['name'] == row[6]
source_name = data['image']['file']
assert sha(PROJECT/source_name) == sha(BACKUP/source_name) == sha(STAGE/source_name)
assert len(list(PROJECT.iterdir())) == 4
for path in WORK.glob('*.py'):
    assert len(path.read_text().splitlines()) < 600
for target in re.findall(r'\]\(([^)]+)\)', current_text):
    assert (PROJECT/target).is_file(), target
for target in re.findall(r'!\[.*?\]\(([^)]+)\)', current_text):
    with Image.open(PROJECT/target) as image:
        image.verify()

ns = {'s':'http://www.w3.org/2000/svg'}
svg = ET.parse(STAGE/'标注.svg')
for sid,space in spaces.items():
    group = svg.find('.//s:g[@id="'+sid+'"]',ns)
    assert group is not None and group.get('data-space-name') == space['name']
    visible = ''.join(t.text or '' for t in group.findall('s:text',ns))
    assert space['name'] in visible, (sid, visible)
    if space['type'] != 'unknown':
        assert '〔' in visible and '〕' in visible
point_count = 0
for relation in data['relations']:
    if relation['type'] == 'entrance':
        assert Polygon(spaces[relation['target']]['polygon_px']).boundary.distance(Point(relation['position_px'])) <= 6
    for opening in relation.get('openings',[]):
        point = Point(opening['position_px'])
        assert max(Polygon(spaces[relation[k]]['polygon_px']).boundary.distance(point) for k in ['source','target']) <= 6
        point_count += 1
assert point_count == 211
stage_report = validate(STAGE)
(WORK/'正式校验_写回前.json').write_text(json.dumps(stage_report,ensure_ascii=False,indent=2)+'\n')

# Recheck the user's file before publishing so concurrent edits are never overwritten.
assert sha(PROJECT/'标注说明.md') == sha(BACKUP/'标注说明.md'), 'The user edited the file during review; merge first.'
assert sha(PROJECT/'annotation.json') == sha(BACKUP/'annotation.json')
note = '**本轮正式校验：**已运行`validate --check-dir`：valid=true、errors=[]、退出码2；仅S001、S035因面积属性未明保留unknown，names_complete=false。194个空间、275条关系、211个开口与SVG红点的编号／坐标／空间对检查通过。K01为图面语义疑点，结构校验不替代该判断。'
old = '本轮核验包括JSON结构、多边形与面积、稳定编号、原图哈希、用户填写保留、红点和空间对一一对应及实际渲染复核。正式validate --check-dir的结果另记在本节；K01和A01/A02未解决前不宣布整图完成。'
assert old in current_text
current_text = current_text.replace(old,note)
(STAGE/'标注说明.md').write_text(current_text)
for name in ['annotation.json','标注.svg','标注说明.md']:
    shutil.copy2(STAGE/name, PROJECT/name)
final_report = validate(PROJECT)
(WORK/'正式校验_写回后.json').write_text(json.dumps(final_report,ensure_ascii=False,indent=2)+'\n')

# Render the final SVG and actual Markdown with Chrome for visual verification.
body = markdown.markdown(current_text,extensions=['tables','toc'])
preview = '<!doctype html><meta charset="utf-8"><base href="'+html.escape(PROJECT.as_uri()+'/')+'"><style>body{max-width:1000px;margin:28px auto;font:17px/1.65 -apple-system,BlinkMacSystemFont,sans-serif;color:#182b3a}img{max-width:100%;height:auto}table{border-collapse:collapse;font-size:14px}td,th{border:1px solid #ddd;padding:7px}h2,h3{margin-top:32px}a{color:#086b9b}</style>'+body
(WORK/'MD_核验预览.html').write_text(preview)
for source,output,size in [(PROJECT/'标注.svg','完整标注_Chrome.png','2444,3418'),(WORK/'MD_核验预览.html','MD_实际预览.png','1200,3600')]:
    result = subprocess.run(['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome','--headless','--disable-gpu','--hide-scrollbars','--force-device-scale-factor=1','--user-data-dir='+str(WORK/'Chrome核验配置'),'--screenshot='+str(WORK/output),'--window-size='+size,source.as_uri()], capture_output=True,text=True,timeout=40)
    assert result.returncode == 0 and (WORK/output).is_file()
image = Image.open(WORK/'完整标注_Chrome.png')
image.resize((1222,1709)).save(WORK/'完整标注_缩览.png')
head=122
for name,box in [('北部密集标注',(310,235+head,1240,690+head)),('感染门诊标注',(310,1015+head,1170,1330+head)),('影像密集标注',(1260,1020+head,2110,1490+head)),('急诊标注',(310,2340+head,1170,2920+head))]:
    crop=image.crop(box)
    crop.resize((crop.width*2,crop.height*2)).save(WORK/(name+'_QA.png'))
preview_image=Image.open(WORK/'MD_实际预览.png')
preview_image.crop((0,0,1200,1850)).save(WORK/'MD_实际预览_上部.png')
preview_image.crop((0,1850,1200,3600)).save(WORK/'MD_实际预览_下部.png')
report = {'names_synced':36, 'merged':{'S029':'S032'}, 'user_rows_preserved':37, 'source_unchanged':True, 'formal_files':sorted(p.name for p in PROJECT.iterdir()), 'spaces':194, 'relations':dict(Counter(r['type'] for r in data['relations'])), 'openings':point_count, 'concept_access':sum(r['type']=='access' and not r.get('openings') for r in data['relations']), 'key_connectivity_pending':1, 'area_pending':2, 'validation':final_report, 'final_hashes':{p.name:sha(p) for p in PROJECT.iterdir()}}
(WORK/'最终核验结果.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
shutil.rmtree(WORK/'Chrome核验配置')
(WORK/'MD_核验预览.html').unlink()
print(json.dumps(report,ensure_ascii=False,indent=2))
