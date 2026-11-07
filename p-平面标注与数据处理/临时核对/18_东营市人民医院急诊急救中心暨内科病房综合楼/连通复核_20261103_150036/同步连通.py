from pathlib import Path
import collections
import importlib.util
import json
import re
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon, Point

from 连通判读 import LOCATED, CONCEPT, REMOVED, ADDITIONS, NAME_TYPES

WORK=Path(__file__).resolve().parent
ROOT=WORK.parents[3]
SAMPLE=ROOT/'p-平面标注与数据处理/标注试样'/WORK.parent.name
SKILL=Path('/Users/hushili/.codex/skills/outpatient-plan-annotation')
spec=importlib.util.spec_from_file_location('annotation_tools',SKILL/'scripts/annotation_tools.py')
at=importlib.util.module_from_spec(spec)
spec.loader.exec_module(at)
NS='http://www.w3.org/2000/svg'


def read_rows(md):
    rows=[]
    for line in md.splitlines():
        cells=[s.strip() for s in line.strip('|').split('|')]
        if len(cells)==7 and re.fullmatch(r'\d{2}',cells[0]):rows.append(cells)
    assert len(rows)==50
    assert [r[0] for r in rows]==[f'{n:02}' for n in range(1,51)]
    assert all(r[0]==r[6] and r[5] not in ('','待确认','待定') for r in rows)
    return rows


def make_question_image():
    original=Image.open(SAMPLE/data['image']['file'])
    box=(145,920,760,1360)
    im=original.crop(box).resize(((box[2]-box[0])*3,(box[3]-box[1])*3))
    dr=ImageDraw.Draw(im)
    for sid,color in [('S027','#d97706'),('S028','#0f766e'),('S029','#0f766e')]:
        p=spaces[sid]['polygon_px'];pts=[((x-box[0])*3,(y-box[1])*3) for x,y in p]
        dr.line(pts+[pts[0]],fill=color,width=4)
    font='/Library/Fonts/Arial Unicode.ttf'
    for text,pos in [('K01 / S027',(500,975)),('原图“病员更衣”局部',(230,1080))]:
        x=(pos[0]-box[0])*3;y=(pos[1]-box[1])*3
        bounds=dr.textbbox((x,y),text,font=ImageFont.truetype(font,28))
        dr.rectangle((bounds[0]-7,bounds[1]-5,bounds[2]+7,bounds[3]+5),fill='white')
        dr.text((x,y),text,font=ImageFont.truetype(font,28),fill='#b45309')
    im.save(WORK/'K01_病员更衣范围.jpg',quality=96)


if __name__=='__main__':
    for name in ['annotation.json','标注.svg','标注说明.md']:
        assert (SAMPLE/name).read_bytes()==(WORK/'修改前备份'/name).read_bytes(),f'{name} changed since backup'
    md=(SAMPLE/'标注说明.md').read_text();rows=read_rows(md)
    data=json.loads((SAMPLE/'annotation.json').read_text())
    old=json.loads((SAMPLE/'annotation.json').read_text())
    spaces={s['id']:s for s in data['spaces']}
    name_audit=[]
    for number,sid,candidate,alternative,basis,answer,right in rows:
        s=spaces[sid]
        name_audit.append({'number':number,'id':sid,'before_name':s['name'],'before_type':s['type'],'user_answer':answer,'after_type':NAME_TYPES[number]})
        s['name']=answer;s['type']=NAME_TYPES[number]
    spaces['S129']['name']='办公门厅电梯组'
    spaces['S132']['name']='办公入口门斗'
    for sid in ['S127','S128','S129','S130','S131','S132']:spaces[sid]['scope']='public_service'
    for sid in ['S117','S118']:spaces[sid]['type']='office'
    # All original S numbers and room boundaries remain; user retained 33/34.
    assert [(s['id'],s['polygon_px'],s.get('area_ratio')) for s in data['spaces']]==[(s['id'],s['polygon_px'],s.get('area_ratio')) for s in old['spaces']]
    assert not(set(LOCATED)&set(CONCEPT))
    original_access={r['id'] for r in data['relations'] if r['type']=='access'}
    assert original_access<=set(LOCATED)|set(CONCEPT)|set(REMOVED)
    next_r=max(int(r['id'][1:]) for r in data['relations'] if r['id'].startswith('R'))+1
    data['relations']=[r for r in data['relations'] if r['id'] not in REMOVED]
    by_id={r['id']:r for r in data['relations']}
    evidence=[]
    for rid,basis in CONCEPT.items():
        evidence.append({'id':rid,'source':by_id[rid]['source'],'target':by_id[rid]['target'],'basis':basis,'position':'未定位概念关系'})
    for source,target,points,basis in ADDITIONS:
        assert not any(r['type']=='access' and {r['source'],r['target']}=={source,target} for r in data['relations'])
        rid=f'R{next_r:03}';next_r+=1
        relation={'id':rid,'source':source,'target':target,'type':'access'}
        data['relations'].append(relation);by_id[rid]=relation
        if points:LOCATED[rid]=points
        else:CONCEPT[rid]=basis
        evidence.append({'id':rid,'source':source,'target':target,'basis':basis,'position':'图面开口' if points else '未定位概念关系'})
    by_id['E005']['name']='办公门厅南侧入口'
    opening_count=0
    for relation in data['relations']:
        rid=relation['id']
        if rid not in LOCATED:continue
        relation['openings']=[]
        for x,y,kind in LOCATED[rid]:
            opening_count+=1
            relation['openings'].append({'id':f'P{opening_count:03}','kind':'door' if kind=='d' else 'open_passage','position_px':[x,y]})
    # Diagnostic distances expose misassigned interfaces; never generate a point.
    far=[]
    for relation in data['relations']:
        for o in relation.get('openings',[]):
            for sid in [relation['source'],relation['target']]:
                distance=Polygon(spaces[sid]['polygon_px']).boundary.distance(Point(*o['position_px']))
                if distance>8:far.append({'opening':o['id'],'relation':relation['id'],'space':sid,'distance':distance})
    assert not far,far
    path=SAMPLE/'annotation.json'
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    at.render(data,path,SAMPLE/'标注.svg')
    svg=ET.parse(SAMPLE/'标注.svg');root=svg.getroot()
    direct_text=root.findall('{'+NS+'}text')
    direct_text[0].text='18号东营市人民医院 · 一层空间与连通标注'
    direct_text[1].text='50项填写已同步；3处功能类别未定，1处空间范围待核'
    # Preserve confirmed generic names visibly when only their class is unknown.
    for sid in ['S023','S081','S082']:
        group=root.find(f'.//{{{NS}}}g[@id="{sid}"]')
        for e in list(group):
            if e.tag in {'{'+NS+'}rect','{'+NS+'}text'}:group.remove(e)
        x,y=Polygon(spaces[sid]['polygon_px']).representative_point().coords[0]
        lines=[sid,spaces[sid]['name'],'〔用途未确认〕'];font=9
        width=max(at.visual_width(s,font) for s in lines)+8;height=len(lines)*11+5
        left=x-width/2;top=y-height/2
        group.append(at.element('rect',{'x':left,'y':top,'width':width,'height':height,'fill':'#fff7df','stroke':'#d97706','stroke-width':'.8'}))
        for i,line in enumerate(lines):group.append(at.txt(left+4,top+11+i*11,line,9,'#b45309',True))
    svg.write(SAMPLE/'标注.svg',encoding='unicode')
    at.summary(data,WORK/'本轮概览.md')
    overview=(WORK/'本轮概览.md').read_text()
    overview=overview.replace('# 平面标注概览','# '+SAMPLE.name+'｜空间与连通复核',1)
    overview=re.sub(r'未完成：3 个空间名称尚未确认。','50项填写已同步。S023“健康”、S081／S082“独立小室”尚无足够信息归入具体功能类别，仍保留unknown。',overview,1)
    overview=re.sub(r'\*\*名称待确认：\*\*[^\n]+','**用途类别未定：**S023 健康；S081、S082 独立小室。这些名称按用户填写保留，不以猜测类别消除unknown。',overview)
    relative=Path('../../临时核对')/WORK.parent.name/WORK.name
    op=[o for r in data['relations'] for o in r.get('openings',[])]
    located=sum(bool(r.get('openings')) for r in data['relations'])
    concepts=[(r['id'],r['source'],r['target'],CONCEPT[r['id']]) for r in data['relations'] if r['type']=='access' and not r.get('openings')]
    sections=[overview,'',
        '**当前精度与范围：**仅18号本图；保留133个稳定S编号、全部既有轮廓和面积比例。用户明确33／S081与34／S082是独立小室，故不合并。S079西侧下行坡道不补造通向室内的连接；其室内／半室外面积口径沿用旧草稿，仍未复核。',
        '', '**名称同步：**按最新“我的确认／备注”逐项落实50项，包括控制室、收费挂号、贵宾接待、办公门厅等修正；仅“健康”和两间“独立小室”缺少功能分类信息。原填写完整保留在本文后半部，旧预估和旧依据不再作为最终名称。',
        '', '## 连通性复核结果','',
        f'已逐区回看原图及5张局部照片，记录{len(op)}个可定位开口，涉及{located}条access；另有{len(concepts)}条未定位概念连接。门洞与无门开口分开保存；P编号全图唯一。服务窗口、相邻和共墙均不自动当人员通行。',
        '', '**主要修正：**补齐CT经控制室进入、注射区与输液室、登记接待与候诊区、出入院办理柜台西端人员门、西侧更衣值班块、东南值班房北门、办公门厅电梯组等连接。S128值班房北门实际接S126配电室，纠正旧S128—S127直连。',
        '', '**入口与交通核：**保留6个有图面依据的建筑入口；原E007对应S125的室内门厅，南侧外墙连续，因此删除该外入口，S125保留并与S123及S124相连。S115与S116之间未见直接开口，删除R105；楼梯经S114与S113相连。不同建筑入口不通过室外总节点互连。',
        '', '**布局推断：**柜台S122东端工作侧与S123厅内概念相接，保留service并另记无门位access；没有从窗口生成P点。其他未定位关系依据见下表。',
        '', '| 关系 | 空间对 | 未定位依据 |','| --- | --- | --- |']
    for rid,a,b,basis in concepts:sections.append(f'| {rid} | {a}—{b} | {basis} |')
    sections += ['', '**本轮不细究的内部细节：**各交通核内部楼梯／电梯路线、成组更衣淋浴内部小间、S081／S082未标用途的内部设施、西侧坡道与图外接口。未记关系不表示不可通行，也不作为负样本；没有为连成单一网络补造通道。',
        '', '## 待确认的范围问题 K01','',f'![K01：病员更衣及高压氧舱范围]({relative}/K01_病员更衣范围.jpg)',
        '', '**问题：**核对12／S027的“病员更衣”是指当前整个带高压氧舱的大房，还是仅左下角更衣区？',
        '', '**我的判断：**现轮廓包含舱体，图上“病员更衣”文字位于左下局部。已按你的填写保留名称，暂不擅自拆分或改变S027边界；名称确认与范围确认分开。',
        '', '**我的确认／备注：**待填写（整个S027沿用此名；或仅左下角，需拆分范围）。',
        '', '**主要通路疑点：**本轮没有新增需要用户判断的主要连接问题；K01是空间范围问题。上述3处用途类别未定不阻止保存本轮有证据的连通信息，但整图仍不能宣告正式完成。',
        '', '## 红点复核图','',f'![全图门洞与连通红点]({relative}/SVG全图红点.png)','']
    for title,file in [('北侧药剂及交通核','北侧'),('西侧高压氧片区','高压氧'),('输液区及连续单间','输液'),('急诊西侧支持','急诊西'),('急诊检查与抢救','急诊东'),('南侧诊室与检验','南排'),('东南住院服务及交通核','东南'),('办公与公共入口','入口')]:
        sections += [f'### {title}','',f'![{title}门洞红点]({relative}/SVG局部_{file}.png)','']
    history=md[md.index('### 01-03'):]
    history=history.replace('### 47-50｜急诊门厅及西南小间','### 47-50｜办公门厅及西南小间')
    history=history.replace('**范围问题：**&#x33;3与34之间是否只有轴线、没有实体隔墙？请在对应确认栏说明是否将32—34合并，或写出实际空间范围。','**范围处理：**用户已填写33、34均为“独立小室”，本轮保留S081、S082及原有分界，不合并。用途仍未说明。')
    sections += ['## 已填写的房间核对记录','',
        '以下保留你的50项原填写、核对号、S编号和照片链接。旧预估、旧依据与旧图绿橙状态仅供追溯，本轮最终名称以“我的确认／备注”为准，均已按上文分类同步；不需要重新填写整表。','',history]
    final_md='\n'.join(sections)+'\n'
    assert read_rows(final_md)==rows
    (SAMPLE/'标注说明.md').write_text(final_md)
    make_question_image()
    (WORK/'名称填写同步记录.json').write_text(json.dumps(name_audit,ensure_ascii=False,indent=2)+'\n')
    (WORK/'关系增量及依据.json').write_text(json.dumps({'removed':REMOVED,'retained_concept':CONCEPT,'additions':evidence},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'spaces':len(spaces),'relations':len(data['relations']),'openings':len(op),'located_access':located,'concept_access':len(concepts),'unknown':sum(s['type']=='unknown' for s in data['spaces'])},ensure_ascii=False))
