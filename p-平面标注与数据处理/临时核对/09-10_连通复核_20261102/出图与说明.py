"""Publishable review documents and visual QA, without replacing live samples."""
from pathlib import Path
from collections import Counter
import importlib.util
import json
import math
import os
import re
import subprocess
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon, box

from 连通工具 import WORK, BASE, sid

FONT='/System/Library/Fonts/STHeiti Medium.ttc'
CHROME='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
NAMES=['09_深圳大学学府医院','10_石家庄第一医院新建赵卜口院区']
prev=WORK.parent/'09-10_名称局部核对_20261102/制作名称局部核对.py'
spec=importlib.util.spec_from_file_location('name_panels',prev)
helpers=importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)


def font(size):
    return ImageFont.truetype(FONT,size)


def relative(path,base):
    return os.path.relpath(path,base)


def archive_answers(out,project):
    raw=(out/'修改前备份/标注说明.md').read_text()
    def rebase(match):
        link=match.group(1)
        if '://' in link or link.startswith('#'):return match.group(0)
        return ']('+relative((project/link).resolve(),out)+')'
    preview=re.sub(r'\]\(([^)]+)\)',rebase,raw)
    (out/'房名原始填写_可预览.md').write_text('# 本轮房名同步前的用户填写记录\n\n原文及填写完整保留；仅为使存档图片可打开而调整链接位置。当前名称和关系以正式样本为准。\n\n'+preview)


def draw_question(q,out,polys,data):
    source=Image.open(out/'工作坐标原图.png').convert('RGB')
    b=q['crop']
    zoom=4
    raw=source.crop(b)
    raw.save(out/(q['number']+'_无标记原图.png'))
    img=Image.new('RGB',(max(1200,raw.width*zoom+64),raw.height*zoom+245),'#f8fafc')
    d=ImageDraw.Draw(img)
    d.text((30,18),q['number']+'｜'+q['title'],font=font(34),fill='#0f172a')
    d.text((30,70),'橙框：本题目标；青框：相关通道／空间。编号沿用正式S编号。',font=font(25),fill='#475569')
    offset=((img.width-raw.width*zoom)//2,115)
    img.paste(raw.resize((raw.width*zoom,raw.height*zoom),Image.Resampling.LANCZOS),offset)
    crop_poly=box(*b)
    gray=source.convert('L')
    sp={s['id']:s for s in data['spaces']}
    labels=[]
    for number in q['context']+q['targets']:
        key=sid(number)
        polygon=Polygon(polys[key]).intersection(crop_poly)
        if polygon.is_empty or polygon.geom_type!='Polygon':continue
        color='#c2410c' if number in q['targets'] else '#0e7490'
        points=[(offset[0]+(x-b[0])*zoom,offset[1]+(y-b[1])*zoom)for x,y in polygon.exterior.coords]
        d.line(points,fill=color,width=4 if number in q['targets'] else 2,joint='curve')
        f=font(27)
        bw=d.textlength(key,font=f)+14
        bh=37
        x,y,fits=helpers.badge_position(polygon,gray,bw/zoom,bh/zoom)
        if fits:
            px=offset[0]+(x-b[0])*zoom
            py=offset[1]+(y-b[1])*zoom
            d.rounded_rectangle((px-bw/2,py-bh/2,px+bw/2,py+bh/2),radius=4,fill='white',outline=color,width=2)
            d.text((px,py),key,font=f,fill=color,anchor='mm')
        if number in q['targets']:labels.append(key+' '+sp[key]['name'])
    line='；'.join(labels)
    for i in range(0,len(line),45):
        d.text((30,raw.height*zoom+145+(i//45)*34),line[i:i+45],font=font(25),fill='#9a3412')
    img.save(out/(q['number']+'_局部.png'),optimize=True)


def draw_overview(out,questions,polys,data):
    source=Image.open(out/'修改前备份'/data['image']['file']).convert('RGB')
    side,top=780,140
    canvas=Image.new('RGB',(source.width+side*2,source.height+top+70),'#f8fafc')
    canvas.paste(source,(side,top))
    draw=ImageDraw.Draw(canvas)
    draw.text((40,20),'10号｜仅2组关键连通疑点；总图用于定位，局部图与问题在说明中',font=font(42),fill='#0f172a')
    draw.text((40,80),'其他清楚的门洞已记录红点；服务窗口和共墙不等于人员相通。',font=font(29),fill='#475569')
    for q in questions:
        color='#b45309' if q['number']=='L01' else '#7e22ce'
        pts=[]
        for number in q['targets']:
            poly=Polygon(polys[sid(number)])
            source_points=[(x*2444/1367,y*3260/1824)for x,y in poly.exterior.coords]
            shifted=[(side+x,top+y)for x,y in source_points]
            draw.line(shifted,fill=color,width=5,joint='curve')
            pts.extend(source_points)
        if q['number']=='L01':
            ax=max(x for x,y in pts);ay=sum(y for x,y in pts)/len(pts)
            lx=side+source.width+30
            line=[(side+ax,top+ay),(side+source.width+10,top+ay),(lx,top+ay)]
        else:
            ax=min(x for x,y in pts);ay=sum(y for x,y in pts)/len(pts)
            lx=25
            line=[(side+ax,top+ay),(side-10,top+ay),(side-25,top+ay)]
        draw.line(line,fill=color,width=3)
        ly=top+ay-60
        draw.rounded_rectangle((lx,ly,lx+720,ly+120),radius=8,fill='white',outline=color,width=3)
        draw.text((lx+15,ly+12),q['number']+'｜'+q['title'],font=font(31),fill=color)
        draw.text((lx+15,ly+65),'请在同一标注说明的局部图旁填写',font=font(28),fill='#475569')
    canvas.save(out/'连通性关键疑点总图.png',optimize=True)
    canvas.thumbnail((1500,1500))
    canvas.save(out/'连通性关键疑点总图_预览.jpg',quality=93)


def documents(name):
    project=BASE/'标注试样'/name
    out=WORK/name
    stage=out/'待核验成果'
    data=json.loads((stage/'annotation.json').read_text())
    review=json.loads((out/'复核记录.json').read_text())
    archive_answers(out,project)
    counts=Counter(r['type']for r in data['relations'])
    located=sum(bool(r.get('openings'))for r in data['relations']if r['type']=='access')
    ops=[o for r in data['relations']for o in r.get('openings',[])]
    prefix='../../临时核对/'+WORK.name+'/'+name+'/'
    title=name.split('_',1)[1]
    lines=[f'# {name[:2]}｜{title}：房名同步与连通性复核','',
           '**房间名称：**本轮用户填写已同步到JSON与SVG，无未确认功能。', '',
           f'**标注规模：**{len(data["spaces"])}个空间／区域；{len(data["relations"])}条关系，其中人员可达{counts["access"]}条、服务联系{counts["service"]}条、建筑入口{counts["entrance"]}条。','',
           f'**门洞与开口：**{len(ops)}个红点，对应{located}条人员可达关系；其中门洞{sum(o["kind"]=="door" for o in ops)}个、无门开口{sum(o["kind"]=="open_passage" for o in ops)}个。另有{counts["access"]-located}条未定位的概念连接，不据此补造门位。','',
           f'[查看具名及红点标注](标注.svg) · [原图]({data["image"]["file"]}) · [保留的房名填写原件]({prefix}房名原始填写_可预览.md)','']
    if name.startswith('09'):
        lines += ['**当前状态：**本轮概念级连通复核已完成，无需追加关键确认问题。此结论限于本张图的主要通行组织，不表示穷尽了内部小间和交通核内所有门。','',
                  '**名称确认中特殊处理：**按你对名称核对09的说明，将S008、S009、S014合并为S008“CT”，其余S编号不重排；S159按你说明的“和儿科大厅连同”记为儿科大厅连续分区，未把这句话作为房名写入。用户原始填写仍完整保留。','',
                  '**本轮范围：**影像、急诊、药房及后场、体检、儿科、西南诊疗、医疗街和整体交通核。临床诊室排按可辨双侧门记录；首间墙体连续处撤下无门依据的另一侧旧边。','',
                  '**图面阅读：**局部复核采用顺时针旋转90°的工作图；正式JSON及SVG仍采用原图坐标。','']
    else:
        lines += ['**当前状态：**房名已确认；连通性尚余下方2组关键疑点。结构和名称校验通过，不代表这2组路线已经确认。','',
                  '**庭院与大厅：**S027、S048、S107、S126、S149、S178按你填写的露天采光庭院处理，不计室内面积；S222按“门诊共享大厅”纳入室内面积，补入其主入口及与既有入口大厅的连续关系。','',
                  '## 只需确认以下2组主要连接','',
                  '可以直接在每题“我的确认／备注”填“同意”，或写实际连接；不要求你确定门的具体位置。若一组中存在例外，只指出例外即可。','',
                  f'[打开完整原图上的疑点定位总图]({prefix}连通性关键疑点总图.png)','',
                  f'![10号两组连通疑点定位总图]({prefix}连通性关键疑点总图_预览.jpg)','']
        polys=json.loads((out/'工作坐标多边形.json').read_text())
        for q in review['questions']:
            draw_question(q,out,polys,data)
            lines += [f'### {q["number"]}｜{q["title"]}','',
                      f'![{q["number"]}：{q["title"]}]({prefix}{q["number"]}_局部.png)','',
                      f'[放大本图]({prefix}{q["number"]}_局部.png) · [同范围无标记原图]({prefix}{q["number"]}_无标记原图.png)','',
                      '**问题：**'+q['question'],'','**我的判断：**'+q['judgment'],'',
                      '**我的确认／备注：**待填写（同意，或写实际相连空间／S编号）','']
        draw_overview(out,review['questions'],polys,data)
    lines += ['## 本轮判断与精度','',
              '清晰门洞和无门开口按原图定位，SVG红点与JSON逐一对应。区域连续、半开放工作区和整体交通核可保留无门位的概念access；服务窗口单列service，共墙不自动建立人员通行。','',
              '**本轮不细究：**管井、检修与小设备间内部路线、交通核内部小门、柜台背侧的细碎分片，以及组合卫生间内部隔间。未记录关系不作为“不相通”的确认，也不作为训练负例。','',
              '**布局推断清单：**以下为助手结合本图通行组织作出的概念判断，均未冒充用户确认；无可定位门洞时不绘红点。','',
              '| 空间对 | 依据与处理 |','| --- | --- |']
    seen=set()
    for v in review['layout_inferences']:
        pair=tuple(sorted(v['pair']))
        if pair in seen:continue
        seen.add(pair)
        lines.append('| '+'—'.join(v['pair'])+' | '+v['reason']+' |')
    lines += ['', '**轮廓和旧边调整：**'+'；'.join(review['notes']), '',
              '**核验：**正式`validate --check-dir`、名称类别与红点对应检查，以及全图／密集局部目检。校验仅证明结构、几何和文件一致性，不能替代原图语义判读。','']
    (stage/'标注说明.md').write_text('\n'.join(lines))


def render_qa(name):
    out=WORK/name
    stage=out/'待核验成果'
    data=json.loads((stage/'annotation.json').read_text())
    root=ET.parse(stage/'标注.svg').getroot()
    width=math.ceil(float(root.get('width')))
    height=math.ceil(float(root.get('height')))
    shot=out/'SVG实际渲染.png'
    args=[CHROME,'--headless','--disable-gpu','--no-first-run','--no-default-browser-check',
          '--hide-scrollbars','--user-data-dir=/tmp/connection-review-'+name[:2],
          f'--window-size={width},{height}','--screenshot='+str(shot),(stage/'标注.svg').as_uri()]
    p=subprocess.run(args,capture_output=True,text=True)
    if p.returncode:raise RuntimeError(p.stderr[-1600:])
    rendered=Image.open(shot).convert('RGB')
    preview=rendered.copy();preview.thumbnail((1350,1350))
    preview.save(out/'SVG全图预览.jpg',quality=93)
    head=max(65,min(125,data['image']['width']*.05))
    plan=rendered.crop((0,round(head),data['image']['width'],round(head)+data['image']['height']))
    if name.startswith('09'):plan=plan.transpose(Image.Transpose.ROTATE_270)
    plan=plan.resize((2734,3648),Image.Resampling.LANCZOS)
    regions={
        '09':[('影像',(170,405,758,735)),('急诊',(855,405,1295,884)),('药房',(177,734,735,993)),
              ('体检',(177,992,735,1137)),('儿科大厅',(915,980,1295,1145)),
              ('西南',(285,1135,758,1385)),('儿科',(900,1137,1210,1385))],
        '10':[('急诊',(175,315,500,678)),('影像',(730,315,1175,680)),('西中',(175,780,500,1145)),
              ('药房',(730,690,1175,995)),('西南',(170,1135,740,1385)),('大厅',(730,987,1175,1335))]
    }
    thumbs=[]
    for label,b in regions[name[:2]]:
        crop=plan.crop(tuple(v*2 for v in b))
        crop.save(out/f'SVG局部_{label}.png')
        crop.thumbnail((680,680))
        card=Image.new('RGB',(700,730),'#f8fafc')
        ImageDraw.Draw(card).text((15,8),name[:2]+' '+label,font=font(26),fill='#0f172a')
        card.paste(crop,(10,45));thumbs.append(card)
    sheet=Image.new('RGB',(2100,730*math.ceil(len(thumbs)/3)),'#e2e8f0')
    for i,thumb in enumerate(thumbs):sheet.paste(thumb,((i%3)*700,(i//3)*730))
    sheet.save(out/'SVG密集局部总览.jpg',quality=94)


if __name__=='__main__':
    for name in NAMES:
        documents(name)
        render_qa(name)
        print(name,'documents and actual SVG rendered',flush=True)
