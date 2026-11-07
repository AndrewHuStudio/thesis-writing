"""Apply the user's L01/L02 answers without inventing physical door locations."""
from pathlib import Path
from collections import Counter
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET

from PIL import Image
from 连通工具 import WORK, BASE, SKILL, annotation, fit_labels

NAME='10_石家庄第一医院新建赵卜口院区'
PROJECT=BASE/'标注试样'/NAME
OTHER=BASE/'标注试样/09_深圳大学学府医院'
CHROME='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def formal(path,output):
    p=subprocess.run([sys.executable,str(SKILL/'scripts/annotation_tools.py'),
                      'validate',str(path),'--check-dir'],capture_output=True,text=True)
    output.write_text(p.stdout+'\n'+p.stderr)
    assert p.returncode==0,(p.stdout,p.stderr)
    result=json.loads(p.stdout)
    assert result['valid'] and result['names_complete'] and not result['errors']
    return result


def main():
    original=(PROJECT/'标注说明.md').read_text()
    decoded=html.unescape(original)
    answers={}
    for number in ['L01','L02']:
        block=re.search(r'^### '+number+r'[^\n]*\n(.*?)(?=^### |^## |\Z)',decoded,re.M|re.S)
        assert block,number
        match=re.search(r'\*\*我的确认／备注：\*\*([^\n]+)',block.group(1))
        assert match,number
        answer=match.group(1).strip()
        assert answer.startswith('是的'),answer
        answers[number]=answer
    out=WORK/NAME/('用户确认同步_20261103_'+uuid.uuid4().hex[:8])
    backup=out/'修改前备份'
    stage=out/'待核验成果'
    backup.mkdir(parents=True)
    stage.mkdir()
    before_hash={p.name:digest(p)for p in PROJECT.iterdir()if p.is_file()}
    other_hash={p.name:digest(p)for p in OTHER.iterdir()if p.is_file()}
    for path in PROJECT.iterdir():
        if path.is_file():shutil.copy2(path,backup/path.name)
    def rebase(match):
        link=match.group(1)
        if '://'in link or link.startswith('#'):return match.group(0)
        return ']('+os.path.relpath((PROJECT/link).resolve(),out)+')'
    archive=re.sub(r'\]\(([^)]+)\)',rebase,original)
    (out/'连通填写原件_可预览.md').write_text('# 用户连通性填写原件\n\n完整保留两题原始填写，仅调整图片相对链接。\n\n'+archive)
    data=json.loads((PROJECT/'annotation.json').read_text())
    old_openings=[o for r in data['relations']for o in r.get('openings',[])]
    old_spaces=json.loads(json.dumps(data['spaces']))
    chains=[('S075','S066'),('S077','S067'),('S079','S068'),('S080','S069'),('S082','S070')]
    pairs=[pair for prep,scan in chains for pair in [('S086',prep),(prep,scan)]]
    pairs += [('S119','S123'),('S119','S125')]
    number=max(int(r['id'][1:])for r in data['relations']if r['id'].startswith('R'))+1
    added=[]
    for a,b in pairs:
        assert not any(r['type']=='access' and {r['source'],r['target']}=={a,b}for r in data['relations'])
        rel={'id':f'R{number:03}','source':a,'target':b,'type':'access'}
        number+=1
        data['relations'].append(rel)
        added.append(rel)
    assert len(added)==12
    assert data['spaces']==old_spaces
    assert [o for r in data['relations']for o in r.get('openings',[])]==old_openings
    (stage/'annotation.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    shutil.copy2(PROJECT/data['image']['file'],stage/data['image']['file'])
    annotation.render(data,stage/'annotation.json',stage/'标注.svg')
    fit_labels(stage/'标注.svg',data)
    counts=Counter(r['type']for r in data['relations'])
    located=sum(bool(r.get('openings'))for r in data['relations']if r['type']=='access')
    text=re.sub(r'^# .+$','# 10｜石家庄第一医院新建赵卜口院区：概念级标注概览',decoded,count=1,flags=re.M)
    text=re.sub(r'\*\*标注规模：\*\*[^\n]+',f'**标注规模：**{len(data["spaces"])}个空间／区域；{len(data["relations"])}条关系，其中人员可达{counts["access"]}条、服务联系{counts["service"]}条、建筑入口{counts["entrance"]}条。',text)
    text=re.sub(r'另有\d+条未定位的概念连接',f'另有{counts["access"]-located}条未定位的概念连接',text)
    text=re.sub(r'\*\*当前状态：\*\*[^\n]+','**当前状态：**名称与本轮关键连通关系均已确认；L01、L02已落实，关键待确认项为0。本张图按概念级精度完成，不表示穷尽辅助小间及交通核内部所有门。',text)
    relative='../../临时核对/'+WORK.name+'/'+NAME+'/'+out.name+'/'
    lines=['## 本轮连通确认已落实','',
           f'[查看含局部图的原始填写记录]({relative}连通填写原件_可预览.md)','',
           '### L01｜影像准备间的患者侧通路','',
           '**你的原始填写：**'+answers['L01'],'',
           '**已落实：**病人通道S086分别进入准备间，再进入对应检查室：','']
    for prep,scan in chains:lines.append(f'- S086 → {prep} → {scan}。')
    lines += ['', '### L02｜两间急诊手术室的主要入口','',
              '**你的原始填写：**'+answers['L02'],'',
              '**已落实：**S119分别连接S123、S125。','',
              '**精度：**以上新增12条经用户确认的概念access，未给出具体门位，因此不新增openings或红点；原157个门洞／开口定位完整保留。','',
              '']
    start=text.index('## 只需确认以下2组主要连接')
    end=text.index('## 本轮判断与精度',start)
    text=text[:start]+'\n'.join(lines)+text[end:]
    assert '待填写'not in text and '尚余下方2组'in decoded
    (stage/'标注说明.md').write_text(text)
    formal(stage/'annotation.json',out/'正式校验_同步前.json')
    for link in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',text):assert (PROJECT/link).exists(),link
    for link in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',archive):assert (out/link).exists(),link
    sp={s['id']:s for s in data['spaces']}
    ns='{http://www.w3.org/2000/svg}'
    root=ET.parse(stage/'标注.svg').getroot()
    for key,space in sp.items():
        group=root.find(f'.//{ns}g[@id="{key}"]')
        visible=''.join(e.text or ''for e in group.iter(ns+'text'))
        assert key in visible and space['name']in visible
    screenshot=out/'SVG实际渲染.png'
    width=int(float(root.get('width')))
    height=int(float(root.get('height'))+1)
    p=subprocess.run([CHROME,'--headless','--disable-gpu','--no-first-run','--no-default-browser-check',
                      '--hide-scrollbars','--user-data-dir=/tmp/final-connectivity-10-'+out.name[-8:],
                      f'--window-size={width},{height}','--screenshot='+str(screenshot),(stage/'标注.svg').as_uri()],capture_output=True,text=True)
    assert p.returncode==0,p.stderr[-1000:]
    image=Image.open(screenshot).convert('RGB')
    image.thumbnail((1200,1400));image.save(out/'SVG全图预览.jpg',quality=94)
    rendered=Image.open(screenshot)
    head=max(65,min(125,data['image']['width']*.05))
    for label,b in [('影像',(780,360,1120,512)),('手术室',(285,805,500,920))]:
        crop=(round(b[0]*2444/1367),round(b[1]*3260/1824+head),
              round(b[2]*2444/1367),round(b[3]*3260/1824+head))
        rendered.crop(crop).save(out/(label+'_标注目检.png'))
    (out/'确认与新增关系.json').write_text(json.dumps({'answers':answers,'added':added,'source_hashes':before_hash},ensure_ascii=False,indent=2)+'\n')
    for filename,h in before_hash.items():assert digest(PROJECT/filename)==h,filename
    for filename in ['annotation.json','标注.svg','标注说明.md']:
        temp=PROJECT/('.'+filename+'.同步中')
        shutil.copy2(stage/filename,temp)
        os.replace(temp,PROJECT/filename)
    result=formal(PROJECT/'annotation.json',out/'正式校验_同步后.json')
    other=formal(OTHER/'annotation.json',out/'09号只读复核.json')
    assert {p.name:digest(p)for p in OTHER.iterdir()if p.is_file()}==other_hash
    assert digest(PROJECT/data['image']['file'])==before_hash[data['image']['file']]
    assert len(list(PROJECT.iterdir()))==4
    report={'out':str(out),'answers':answers,'added_relations':len(added),'spaces':result['spaces'],
            'relations':result['relations'],'openings':len(old_openings),'critical_pending':0,
            'names_complete':result['names_complete'],'valid':result['valid'],'original_image_unchanged':True,
            '09_unchanged':True,'09_valid':other['valid'],'09_names_complete':other['names_complete']}
    (out/'交付检查.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False),flush=True)


if __name__=='__main__':main()
