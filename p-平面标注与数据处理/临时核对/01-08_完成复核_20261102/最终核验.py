"""正式CLI校验、用户原文可查看归档、SVG实际渲染及交付统计。"""
from pathlib import Path
from collections import Counter
import hashlib
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw
import pymupdf

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
TOOL=Path('/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts/annotation_tools.py')
NS='{http://www.w3.org/2000/svg}'
LINK=re.compile(r'(!?\[[^\]]*\])\((?:<([^>]+)>|([^\)]+))\)')


def dump(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def rebase_archive(p,work):
    original=work/'同步前备份/标注说明.md'
    text=original.read_text()
    def replace(m):
        target=m.group(2) or m.group(3)
        if target.startswith(('http:','https:','#')):return m.group(0)
        path=(p/target).resolve()
        return m.group(1)+'(<'+Path(os.path.relpath(path,work)).as_posix()+'>)'
    rebased=LINK.sub(replace,text)
    (work/'用户填写与局部图.md').write_text(rebased)
    final=p/'标注说明.md'
    text=final.read_text()
    old=Path(os.path.relpath(original,p)).as_posix()
    new=Path(os.path.relpath(work/'用户填写与局部图.md',p)).as_posix()
    text=text.replace(old,new)
    text=text.replace('绿化不参与。','绿化及露天／挑空中庭不参与。')
    final.write_text(text)


def links_exist(path):
    missing=[]
    for m in LINK.finditer(path.read_text()):
        target=m.group(2) or m.group(3)
        if not target.startswith(('http:','https:','#')) and not (path.parent/target).exists():
            missing.append(target)
    return missing


def labels_match(p,data):
    root=ET.parse(p/'标注.svg').getroot()
    nodes={e.get('id'):e for e in root.iter() if e.get('id')}
    missing=[]
    for s in data['spaces']:
        node=nodes.get(s['id'])
        texts=[] if node is None else [e.text or '' for e in node.iter(NS+'text')]
        visible=re.sub(r'\s+','',''.join(texts))
        if re.sub(r'\s+','',s['name']) not in visible or s['id'] not in visible:
            missing.append(s['id'])
    return missing


REGIONS={
    '01':[(300,650,1200,1200)],
    '02':[(300,1300,1150,2050)],
    '03':[(1100,700,1950,1450)],
    '04':[(1500,1650,2300,2450)],
    '05':[(1860,1025,2190,1420),(790,1850,1260,2180)],
    '06':[(3040,1990,3290,2260),(1650,1830,2300,2340)],
    '07':[(2450,820,2760,1030),(1840,1980,2220,2180),(1040,820,1240,1010)],
    '08':[(1260,1120,1660,1320),(1450,1450,1690,1700),(1860,1930,2080,2200)],
}


def render(p,data,work):
    doc=pymupdf.open(p/'标注.svg')
    page=doc[0]
    scale=min(1500/page.rect.width,1800/page.rect.height)
    page.get_pixmap(matrix=pymupdf.Matrix(scale,scale),alpha=False).save(work/'最终SVG_全图.png')
    # 03号原SVG已旋转；其局部坐标直接采用当前SVG画布坐标。
    num=p.name[:2]
    header=0 if num=='03' else max(65,min(125,data['image']['width']*.05))
    for i,(x1,y1,x2,y2) in enumerate(REGIONS[num],1):
        clip=pymupdf.Rect(x1,y1+header,x2,y2+header)
        page.get_pixmap(matrix=pymupdf.Matrix(2,2),clip=clip,alpha=False).save(work/f'最终SVG_局部{i}.png')


def semantic_checks(n,data):
    pairs={frozenset([r['source'],r['target']]) for r in data['relations'] if r['type']=='access'}
    required={
        '05':[(13,9),(41,42),(41,52),(24,20),(25,20),(28,31)],
        '06':[(65,63),(65,64),(111,120),(120,109),(57,58)],
        '07':[(105,411),(411,391),(159,412),(412,396),(163,161),
              (285,286),(294,291),(301,297),(312,304),(325,321),(322,273)],
        '08':[(74,178),(153,171),(171,162),(190,191),(213,208),(208,195),(211,322)],
    }
    excluded={'05':[(1,6),(42,52),(28,24),(121,72)],'06':[(111,109)],
              '07':[(105,106),(163,162)],'08':[(139,149),(213,195)]}
    for a,b in required.get(n,[]):assert frozenset([f'S{a:03}',f'S{b:03}']) in pairs,(n,a,b)
    for a,b in excluded.get(n,[]):assert frozenset([f'S{a:03}',f'S{b:03}']) not in pairs,(n,a,b)
    if n=='06':
        assert not ({'S060','S062'} & {s['id'] for s in data['spaces']})
        assert next(s for s in data['spaces'] if s['id']=='S120')['name']=='换鞋间'
    if n=='08':assert any(r['type']=='entrance' and r['target']=='S065' for r in data['relations'])


def main():
    reports=[]
    for p in sorted((ROOT/'标注试样').glob('0[1-8]_*')):
        n=p.name[:2]
        work=HERE/p.name
        work.mkdir(exist_ok=True)
        if n in {'05','06','07','08'}:rebase_archive(p,work)
        data=json.loads((p/'annotation.json').read_text())
        result=subprocess.run([sys.executable,str(TOOL),'validate',str(p/'annotation.json'),'--check-dir'],capture_output=True,text=True)
        assert result.returncode==0,(p.name,result.stdout,result.stderr)
        formal=json.loads(result.stdout)
        missing=labels_match(p,data)
        assert not missing,(p.name,missing)
        broken=links_exist(p/'标注说明.md')
        if n in {'05','06','07','08'}:broken+=links_exist(work/'用户填写与局部图.md')
        assert not broken,(p.name,broken)
        semantic_checks(n,data)
        render(p,data,work)
        openings=[o for r in data['relations'] for o in r.get('openings',[])]
        counts=Counter(r['type'] for r in data['relations'])
        report=dict(number=n,project=p.name,formal_validate=formal,exit_code=result.returncode,
                    spaces=len(data['spaces']),relations=len(data['relations']),openings=len(openings),
                    relations_by_type=dict(counts),opening_kinds=dict(Counter(o['kind'] for o in openings)),
                    concept_access=sum(r['type']=='access' and not r.get('openings') for r in data['relations']),
                    missing_visible_labels=missing,broken_links=broken,
                    source_sha256=hashlib.sha256((p/data['image']['file']).read_bytes()).hexdigest(),
                    visual_review='pending')
        dump(work/'正式核验.json',report)
        reports.append(report)
        print(n,report['spaces'],report['relations'],report['openings'],'PASS',flush=True)
    dump(HERE/'01-08_核验汇总.json',reports)
    for start in [0,4]:
        canvas=Image.new('RGB',(2400,1800),'white')
        draw=ImageDraw.Draw(canvas)
        for j,r in enumerate(reports[start:start+4]):
            im=Image.open(HERE/r['project']/'最终SVG_全图.png')
            im.thumbnail((595,1750))
            canvas.paste(im,(j*600,35))
            draw.text((j*600+10,5),r['number'],fill='black')
        canvas.save(HERE/f'全图目检_{start+1:02d}-{start+4:02d}.jpg')


if __name__=='__main__':main()
