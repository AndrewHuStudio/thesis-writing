"""Verify staged evidence, then atomically sync only the authorized sample files."""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import markdown
from shapely.geometry import Point, Polygon

from 连通工具 import WORK, BASE, SKILL, annotation, sid
from 出图与说明 import CHROME, NAMES, relative


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def formal(path,output):
    result=subprocess.run([sys.executable,str(SKILL/'scripts/annotation_tools.py'),
                           'validate',str(path),'--check-dir'],capture_output=True,text=True)
    output.write_text(result.stdout+'\n'+result.stderr)
    assert result.returncode==0,(result.returncode,result.stdout,result.stderr)
    value=json.loads(result.stdout)
    assert value['valid'] and value['names_complete'] and not value['errors']
    return value


def verify(name,publish=False):
    out=WORK/name
    project=BASE/'标注试样'/name
    stage=out/'待核验成果'
    data=json.loads((stage/'annotation.json').read_text())
    before=json.loads((out/'修改前备份/annotation.json').read_text())
    evidence=json.loads((out/'复核记录.json').read_text())
    rows=json.loads((out/'用户填写解析.json').read_text())
    hashes=json.loads((out/'修改前文件校验.json').read_text())
    for filename,h in hashes.items():
        assert digest(out/'修改前备份'/filename)==h
        assert digest(project/filename)==h, 'Live user file changed during review: '+filename
    sp={s['id']:s for s in data['spaces']}
    old_ids={s['id']for s in before['spaces']}
    assert set(sp)==old_ids-({'S009','S014'}if name.startswith('09')else set())
    assert len(rows)==(182 if name.startswith('09')else 135)
    for row in rows:
        answer=row['answer'].strip().strip('*')
        if row['sid'] in ['S009','S014'] and name.startswith('09'):
            assert sp['S008']['name']=='CT'
            continue
        if row['sid']=='S159' and name.startswith('09'):answer='儿科大厅'
        if '露天采光庭院' in answer:answer=answer.split(' ')[0]
        assert sp[row['sid']]['name']==answer,(row,sp[row['sid']])
    assert digest(project/data['image']['file'])==digest(stage/data['image']['file'])
    result=formal(stage/'annotation.json',out/'正式校验_待核验成果.json')
    manual={o['id']:o for o in evidence['manual_openings']}
    opening_count=0
    for rel in data['relations']:
        for o in rel.get('openings',[]):
            opening_count+=1
            record=manual[o['id']]
            assert set(record['pair'])=={rel['source'],rel['target']}
            distances=[Polygon(sp[key]['polygon_px']).distance(Point(o['position_px']))
                       for key in [rel['source'],rel['target']]]
            assert max(distances)<=12,(o,rel,distances)
    assert len(manual)==opening_count
    root=ET.parse(stage/'标注.svg').getroot()
    ns='{http://www.w3.org/2000/svg}'
    for space in data['spaces']:
        group=root.find(f'.//{ns}g[@id="{space["id"]}"]')
        assert group is not None
        assert group.get('data-space-name')==space['name']
        visible=''.join(e.text or ''for e in group.iter(ns+'text'))
        assert space['id']in visible and space['name']in visible,(space['id'],visible)
        assert '〔'+annotation.TYPE_NAMES[space['type']]+'〕'in visible
    text=(stage/'标注说明.md').read_text()
    links=re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',text)
    for link in links:
        assert (project/link).exists(),link
    archive=(out/'房名原始填写_可预览.md').read_text()
    for link in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',archive):
        assert (out/link).exists(),link
    q=evidence['questions']
    assert len(q)==(0 if name.startswith('09')else 2)
    assert text.count('**我的确认／备注：**')==len(q)
    if name.startswith('10'):
        def has(a,b):
            return any(v['type']=='access' and {v['source'],v['target']}=={sid(a),sid(b)}for v in data['relations'])
        for a,b in [(n,86)for n in range(74,84)]+[(n,106)for n in range(101,105)]+[(122,123),(215,213)]:
            assert not has(a,b),(a,b)
        assert all(s['type']=='courtyard' and 'area_ratio'not in s for s in data['spaces']if s['id']in ['S027','S048','S107','S126','S149','S178'])
        assert sp['S222']['type']=='hall' and 'area_ratio'in sp['S222']
    for code in WORK.glob('*.py'):
        assert len(code.read_text().splitlines())<600,code
    if publish:
        for filename in ['annotation.json','标注.svg','标注说明.md']:
            temp=project/('.'+filename+'.同步中')
            shutil.copy2(stage/filename,temp)
            os.replace(temp,project/filename)
        result=formal(project/'annotation.json',out/'正式校验_已同步.json')
        assert len(list(project.iterdir()))==4
        assert digest(project/data['image']['file'])==hashes[data['image']['file']]
        for filename in ['annotation.json','标注.svg','标注说明.md']:
            assert digest(project/filename)==digest(stage/filename)
    report={'project':name,'published':publish,'valid':result['valid'],'names_complete':result['names_complete'],
            'spaces':len(sp),'relations':len(data['relations']),'openings':opening_count,
            'key_questions':len(q),'confirmed_rows_preserved':len(rows),'source_bytes_unchanged':True,
            'svg_visible_names_and_categories_match':True,'opening_pairs_and_near_boundary_check':True,
            'all_md_images_and_links_exist':True,'conceptual_connectivity_complete':not q}
    (out/('最终交付检查.json'if publish else '同步前检查.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False),flush=True)


def render_md():
    name=NAMES[1]
    project=BASE/'标注试样'/name
    out=WORK/name
    text=(out/'待核验成果/标注说明.md').read_text()
    matches=list(re.finditer(r'^### L\d+.+$',text,re.M))
    for i,match in enumerate(matches):
        end=matches[i+1].start()if i+1<len(matches)else text.index('## 本轮判断与精度',match.end())
        block=text[match.start():end]
        block=re.sub(r'\]\(([^)]+)\)',lambda m:']('+(project/m.group(1)).resolve().as_uri()+')',block)
        html='<!doctype html><meta charset="utf-8"><style>body{font:18px/1.65 -apple-system,"PingFang SC",sans-serif;max-width:1080px;margin:24px auto;color:#172033}img{display:block;max-width:100%;height:auto}h3{margin:8px 0 14px}a{color:#0369a1}</style>'
        html+=markdown.markdown(block)
        path=out/f'MD实际预览_L{i+1:02}.html';path.write_text(html)
        shot=path.with_suffix('.png')
        result=subprocess.run([CHROME,'--headless','--disable-gpu','--no-first-run','--no-default-browser-check',
                               '--hide-scrollbars','--allow-file-access-from-files',
                               '--user-data-dir=/tmp/connection-md-'+str(i),
                               '--window-size=1280,1600','--screenshot='+str(shot),path.as_uri()],capture_output=True,text=True)
        assert result.returncode==0 and shot.exists(),result.stderr


if __name__=='__main__':
    publish='--publish'in sys.argv
    if not publish:render_md()
    # Preflight both files before publishing either one.
    for name in NAMES:verify(name,False)
    if publish:
        for name in NAMES:verify(name,True)
