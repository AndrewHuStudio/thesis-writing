"""本轮固定编号核对材料、概览及只读交付验证。"""
from pathlib import Path
from collections import Counter
import hashlib
import importlib.util
import json
import re
import textwrap
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon, Point, box, LineString
import pymupdf

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SKILL=Path('/Users/hushili/.codex/skills/outpatient-plan-annotation')
spec=importlib.util.spec_from_file_location('at',SKILL/'scripts/annotation_tools.py')
at=importlib.util.module_from_spec(spec)
spec.loader.exec_module(at)
FONT='/System/Library/Fonts/STHeiti Medium.ttc'
NS='{http://www.w3.org/2000/svg}'


def dump(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def relpath(path,base):
    import os
    return Path(os.path.relpath(path,base)).as_posix()


def optimize_labels(path,data):
    """将非常狭窄通道的完整标签缩入本区，并避让已定位门洞。"""
    tree=ET.parse(path)
    nodes={e.get('id'):e for e in tree.iter() if e.get('id')}
    points=[Point(o['position_px']) for r in data['relations'] for o in r.get('openings',[])]
    changed=[]
    for s in data['spaces']:
        node=nodes[s['id']]
        if any(e.get('data-rotated-label') for e in node):continue
        rect=next(e for e in node if e.tag==NS+'rect')
        texts=[e for e in node if e.tag==NS+'text']
        x,y,w,h=[float(rect.get(k)) for k in ['x','y','width','height']]
        poly=Polygon(s['polygon_px'])
        b=box(x,y,x+w,y+h)
        nearby=[pt for pt in points if poly.distance(pt)<20]
        if poly.covers(b) and not any(b.distance(pt)<9 for pt in nearby):continue
        minx,miny,maxx,maxy=poly.bounds
        r=poly.representative_point()
        found=None
        for fs in [float(texts[0].get('font-size','7')),7,6,5.5]:
            maxwidth=max(10,min(210,maxx-minx-4))
            lines=[s['id']]+at.wrap(s['name'],fs,maxwidth-4)
            lines+=at.wrap('〔'+at.TYPE_NAMES[s['type']]+'〕',fs,maxwidth-4)
            lw=max(at.visual_width(row,fs) for row in lines)+4
            lh=len(lines)*(fs+2)+3
            candidates=[(r.x,r.y)]
            for dx in [0,-10,10,-20,20,-35,35,-55,55]:
                for dy in [0,-12,12,-25,25,-45,45,-70,70]:candidates.append((r.x+dx,r.y+dy))
            for cx,cy in candidates:
                nb=box(cx-lw/2,cy-lh/2,cx+lw/2,cy+lh/2)
                if poly.covers(nb) and all(nb.distance(pt)>=9 for pt in nearby):
                    found=(cx-lw/2,cy-lh/2,lw,lh,fs,lines)
                    break
            if found:break
        if not found:
            full=s['id']+' '+s['name']+'〔'+at.TYPE_NAMES[s['type']]+'〕'
            candidates=[(r.x,r.y)]
            for ix in range(1,12):
                for iy in range(1,32):
                    candidates.append((minx+(maxx-minx)*ix/12,miny+(maxy-miny)*iy/32))
            compact=None
            for fs in [6,5.5,5]:
                for width in [44,32,24,19,16]:
                    lines=[s['id']]+at.wrap(s['name'],fs,width-4)
                    lines+=at.wrap('〔'+at.TYPE_NAMES[s['type']]+'〕',fs,width-4)
                    lw=max(at.visual_width(row,fs) for row in lines)+4
                    lh=len(lines)*(fs+2)+3
                    for cx,cy in candidates:
                        nb=box(cx-lw/2,cy-lh/2,cx+lw/2,cy+lh/2)
                        if poly.covers(nb) and all(nb.distance(pt)>=5 for pt in nearby):
                            compact=(cx-lw/2,cy-lh/2,lw,lh,fs,lines)
                            break
                    if compact:break
                if compact:break
            if compact:
                nx,ny,lw,lh,fs,lines=compact
                for k,v in zip(['x','y','width','height'],[nx,ny,lw,lh]):rect.set(k,str(v))
                color=texts[0].get('fill')
                for t in texts:node.remove(t)
                for i,line in enumerate(lines):node.append(at.txt(nx+2,ny+fs+1+i*(fs+2),line,fs,color,True))
                changed.append(s['id']+'(局部紧凑标签)')
                continue
            rotated=None
            for fs in [7,6,5.5]:
                length=at.visual_width(full,fs)+4
                for cx,cy in candidates:
                    nb=box(cx-(fs+4)/2,cy-length/2,cx+(fs+4)/2,cy+length/2)
                    if poly.covers(nb) and all(nb.distance(pt)>=5 for pt in nearby):
                        rotated=(cx,cy,length,fs,nb)
                        break
                if rotated:break
            if rotated:
                cx,cy,length,fs,nb=rotated
                for e in [rect]+texts:node.remove(e)
                group=at.element('g',{'transform':f'rotate(90 {cx} {cy})',
                    'data-rotated-label':'true','data-label-bounds':','.join(map(str,nb.bounds))})
                color=texts[0].get('fill')
                group.append(at.element('rect',{'x':cx-length/2,'y':cy-(fs+4)/2,
                    'width':length,'height':fs+4,'fill':'white','fill-opacity':'.94',
                    'stroke':color,'stroke-width':'.6','rx':1}))
                group.append(at.txt(cx-length/2+2,cy+fs/2-1,full,fs,color,True))
                node.append(group)
                changed.append(s['id']+'(窄通道旋转标签)')
            continue
        nx,ny,lw,lh,fs,lines=found
        for k,v in zip(['x','y','width','height'],[nx,ny,lw,lh]):rect.set(k,str(v))
        color=texts[0].get('fill')
        for t in texts:node.remove(t)
        for i,line in enumerate(lines):node.append(at.txt(nx+2,ny+fs+1+i*(fs+2),line,fs,color,True))
        changed.append(s['id'])
    # MuPDF未完整支持paint-order；白色描边会覆盖小号P文字，改用独立白底与红字。
    occupied=[]
    marker_points=[Point(o['position_px']) for r in data['relations'] for o in r.get('openings',[])]
    room_boxes=[]
    for s in data['spaces']:
        for e in nodes[s['id']]:
            if e.get('data-rotated-label'):
                room_boxes.append(box(*map(float,e.get('data-label-bounds').split(','))))
            if e.tag==NS+'rect':
                rx,ry,rw,rh=[float(e.get(k)) for k in ['x','y','width','height']]
                room_boxes.append(box(rx,ry,rx+rw,ry+rh))
    for r in data['relations']:
        for opening in r.get('openings',[]):
            node=nodes[opening['id']]
            for e in list(node):
                if e.tag in [NS+'rect',NS+'line']:node.remove(e)
            label=next(e for e in node if e.tag==NS+'text')
            for key in ['stroke','stroke-width','paint-order']:label.attrib.pop(key,None)
            label.set('fill','#b91c1c')
            x,y=opening['position_px']
            fs=float(label.get('font-size'))
            lw=at.visual_width(opening['id'],fs)+4
            lh=fs+3
            candidates=[]
            for dx,dy in [(7,-lh-5),(7,5),(-lw-7,-lh-5),(-lw-7,5),
                          (7,-lh-18),(7,18),(-lw-7,-lh-18),(-lw-7,18),
                          (7,-lh-32),(7,32),(-lw-7,-lh-32),(-lw-7,32)]:
                b=box(x+dx,y+dy,x+dx+lw,y+dy+lh)
                if not (0<=b.bounds[0] and b.bounds[2]<=data['image']['width'] and 0<=b.bounds[1] and b.bounds[3]<=data['image']['height']):continue
                score=sum(b.intersection(q).area*2 for q in occupied)
                score+=sum(b.intersection(q).area for q in room_boxes)
                score+=sum(1000 for pt in marker_points if b.distance(pt)<6)
                candidates.append((score,b))
            _,b=min(candidates,key=lambda pair:pair[0])
            occupied.append(b)
            bx,by,_,_=b.bounds
            back=at.element('rect',{'x':bx,'y':by,'width':lw,'height':lh,
                                  'fill':'white','fill-opacity':'.88','rx':1})
            guide=at.element('line',{'x1':x,'y1':y,'x2':bx+lw/2,'y2':by+lh/2,
                                   'stroke':'#b91c1c','stroke-width':'.6'})
            node.insert(1,guide)
            node.insert(list(node).index(label),back)
            label.set('x',str(bx+2));label.set('y',str(by+fs))
    tree.write(path,encoding='unicode')
    return changed


def make_crops(work,im,spaces,questions):
    f=ImageFont.truetype(FONT,22)
    colors=['#b91c1c','#0369a1','#047857','#7c3aed','#b45309','#be185d','#4338ca']
    for i,q in enumerate(questions):
        pts=[xy for sid in q['spaces'] for xy in spaces[sid]['polygon_px']]
        xs,ys=zip(*pts)
        margin=75
        bb=(max(0,int(min(xs)-margin)),max(0,int(min(ys)-margin)),
            min(im.width,int(max(xs)+margin)),min(im.height,int(max(ys)+margin)))
        crop=im.crop(bb).convert('RGB')
        draw=ImageDraw.Draw(crop)
        for sid in q['spaces']:
            poly=[(x-bb[0],y-bb[1]) for x,y in spaces[sid]['polygon_px']]
            draw.line(poly+[poly[0]],fill=colors[i%7],width=3)
            a=Polygon(poly).representative_point()
            label=sid
            size=draw.textbbox((0,0),label,font=f)
            draw.rectangle((a.x,a.y,a.x+size[2]+5,a.y+28),fill='white')
            draw.text((a.x+2,a.y+2),label,font=f,fill=colors[i%7])
        scale=min(2,1300/crop.width)
        crop=crop.resize((int(crop.width*scale),int(crop.height*scale)))
        crop.save(work/f'{q["number"]}_局部.png')
        im.crop(bb).save(work/f'{q["number"]}_原图局部.png')
        q['crop_box']=bb
    # 全原图定位总图：两侧标签按图面次序；固定问题编号不变。
    side=600
    canvas=Image.new('RGB',(im.width+side*2,im.height+110),'white')
    canvas.paste(im,(side,100))
    draw=ImageDraw.Draw(canvas)
    big=ImageFont.truetype(FONT,32)
    draw.text((side,25),'主要连通关系｜固定核对号，明日确认',fill='#18314c',font=big)
    columns={'L':[],'R':[]}
    for q in questions:
        sid=q['spaces'][0]
        p=Polygon(spaces[sid]['polygon_px'])
        a=p.representative_point()
        q['anchor']=[a.x,a.y]
        columns['L' if a.x<im.width/2 else 'R'].append(q)
    paths=[]
    for col,qs in columns.items():
        qs.sort(key=lambda q:q['anchor'][1])
        prev=90
        for q in qs:
            x,y=q['anchor'];y+=100;x+=side
            ly=max(y,prev+115);ly=min(ly,im.height+50)
            prev=ly
            left=col=='L'
            edge=side-25 if left else side+im.width+25
            labelx=20 if left else side+im.width+45
            path=[(edge,ly),(edge+(-10 if left else 10),ly),(x,y)]
            color=colors[questions.index(q)%7]
            paths.append((q['number'],LineString(path)))
            draw.line(path,fill=color,width=3)
            poly=[(xx+side,yy+100) for xx,yy in spaces[q['spaces'][0]]['polygon_px']]
            draw.line(poly+[poly[0]],fill=color,width=4)
            text=q['number']+'｜'+q['spaces'][0]+' '+spaces[q['spaces'][0]]['name']
            draw.text((labelx,ly-25),text,fill=color,font=f)
            draw.text((labelx,ly+8),'详见同号局部图及填写处',fill='#475569',font=f)
            draw.ellipse((x-5,y-5,x+5,y+5),fill=color)
    crossings=[]
    for i,(a,pa) in enumerate(paths):
        for b,pb in paths[i+1:]:
            if pa.crosses(pb):crossings.append([a,b])
    canvas.save(work/'关键连通核对总图.png')
    return crossings


def generate(number):
    p=next((ROOT/'标注试样').glob(number+'_*'))
    work=HERE/p.name
    data=json.loads((p/'annotation.json').read_text())
    old=json.loads((work/'修改前备份/annotation.json').read_text())
    spaces={s['id']:s for s in data['spaces']}
    qs=json.loads((work/'明日关键确认.json').read_text())
    retired=json.loads((work/'退出逐项追问.json').read_text())
    inf=json.loads((work/'布局推断.json').read_text())
    if number=='08':
        by_sid={q['spaces'][0]:q for q in qs}
        qs=[by_sid[s] for s in ['S065','S074','S139','S153','S190','S213','S211']]
        for i,q in enumerate(qs,1):q['number']=f'{i:02d}'
    image_path=p/data['image']['file']
    im=Image.open(image_path).convert('RGB')
    crossings=make_crops(work,im,spaces,qs)
    dump(work/'明日关键确认.json',qs)
    changed=optimize_labels(p/'标注.svg',data)
    at.summary(data,work/'自动概览.md')
    summary=(work/'自动概览.md').read_text()
    summary=summary.replace('# 平面标注概览', '# '+p.name+'｜概念标注与连通复核')
    summary=summary.replace('空间名称已齐；结构与关系仍以原图及人工核对为依据。',
        f'**名称已齐；已按01—04的概念口径补充门洞与主要连通。仍有{len(qs)}组关键疑点待你确认，本图连通复核尚未全部完成。**')
    prefix=relpath(work,p)
    extra='\n\n## 本轮范围与保留内容\n\n'
    extra+='仅处理当前这一张平面。全部既有S编号、已确认房名、类别、功能范围及既有P编号保留；原图未修改。'
    if number=='08':extra+='补入S322“急诊西侧后场通道”、S323“西南片区东侧内通道”，补齐旧草稿漏标的通行带；同步修正医技斜入口及南侧入口带轮廓。'
    extra+='明确可辨的门洞以红点定位，连续区域、半墙及整体交通核采用有依据的概念连接；服务窗口、共墙与人员可达分别保存。\n\n'
    extra+='[查看原图]('+data['image']['file']+') · [查看具名标注](标注.svg) · [本轮修改前说明与用户填写]('+prefix+'/修改前备份/标注说明.md)\n\n'
    extra+='## 明日集中确认\n\n'
    extra+='保留本轮固定核对号。请在各题“我的确认／备注”写实际相连的空间／通道，或说明其他处理；有明确建议时可写同意，也可在聊天按编号回复。不清楚可继续待确认。无需补门宽、门扇构造或内部精确路线。自动判断及未作答均不当作用户确认。\n\n'
    extra+='![完整原图与关键问题定位](<'+prefix+'/关键连通核对总图.png>)\n\n'
    for q in qs:
        num=q['number']
        names='、'.join(s+' '+spaces[s]['name'] for s in q['spaces'])
        extra+=f'### {num}｜{names}\n\n'
        extra+=f'![{num}：相关空间及必要邻接上下文](<{prefix}/{num}_局部.png>)\n\n'
        extra+=f'[查看同范围无标记原图](<{prefix}/{num}_原图局部.png>)\n\n'
        extra+=f'**问题：**{q["question"]}\n\n**我的判断：**{q["judgment"]}\n\n**我的确认／备注：**待填写（写实际连接／处理；不清楚可保留待确认）\n\n'
    extra+='## 本轮不细究的内部细节与旧题处理\n\n'
    for q in retired:extra+='- **'+q['number']+'：**'+q['result']+'\n'
    extra+='\n这些处理不等于已确认不可通行，未记关系不能作为训练负例。旧题原文、映射及原填写保存在上方修改前说明中；本轮不重排既有核对号。\n'
    if inf:
        extra+='\n## 布局推断（不是用户已确认）\n\n'
        for r in inf:extra+=f'- **{r["source"]}—{r["target"]}（{r["relation"]}）：**{r["basis"]}\n'
    extra+='\n## 核验边界\n\n正式结构校验检查名称、几何、编号、面积及红点与JSON一致性；不替代上述关键连通判断。原图、历史名称确认和全部修改前文件均保留。最终目录仍仅保留原图、SVG、JSON、MD四文件。\n'
    if number=='08':
        original=(work/'修改前备份/标注说明.md').read_text()
        history=original[original.index('## 名称与属性核对记录'):]
        extra+='\n'+history
    (p/'标注说明.md').write_text(summary+extra)
    # 渲染当前实际SVG；全图和密集局部均保存在工作区。
    doc=pymupdf.open(p/'标注.svg')
    page=doc[0]
    page.get_pixmap(matrix=pymupdf.Matrix(min(1.0,1900/page.rect.width),min(1.0,1900/page.rect.width)),alpha=False).save(work/'最终SVG_全图.png')
    w=data['image']['width'];head=max(65,min(125,w*.05))
    if number=='05':regions=[(560,1580,1260,2180),(1830,980,2690,1510),(1840,2150,2640,2850)]
    elif number=='06':regions=[(2250,2110,2690,2550),(2530,3860,2780,4090),(1200,900,2150,1500)]
    elif number=='07':regions=[(100,100,1150,720),(950,700,1650,1300),(100,1350,1000,2220)]
    else:regions=[(330,1150,1040,1695),(330,2170,1040,2670),(1390,2180,2070,2700),(1390,1250,2070,1680)]
    for i,(x1,y1,x2,y2) in enumerate(regions,1):
        clip=pymupdf.Rect(x1,y1+head,x2,y2+head)
        page.get_pixmap(matrix=pymupdf.Matrix(1.5,1.5),clip=clip,alpha=False).save(work/f'最终SVG_密集局部{i}.png')
    result,code=at.check(data,p/'annotation.json',check_dir=True)
    before_hash=hashlib.sha256((work/'修改前备份'/data['image']['file']).read_bytes()).hexdigest()
    actual_hash=hashlib.sha256(image_path.read_bytes()).hexdigest()
    assert before_hash==actual_hash
    current_points={o['id']:o for r in data['relations'] for o in r.get('openings',[])}
    old_points={o['id']:o for r in old['relations'] for o in r.get('openings',[])}
    assert all(current_points[k]==v for k,v in old_points.items())
    links=[]
    for match in re.finditer(r'!?\[[^\]]*\]\((?:<([^>]+)>|([^\)]+))\)',summary+extra):
        target=match.group(1) or match.group(2)
        if not target.startswith(('http:','https:','#')) and not (p/target).exists():links.append(target)
    report={'formal_validate':result,'exit_code':code,'original_sha256_unchanged':actual_hash==before_hash,
            'stable_old_spaces_preserved':all(any(s['id']==o['id'] and all(s[k]==o[k] for k in ['name','type','level','scope']) for s in data['spaces']) for o in old['spaces']),
            'old_openings_preserved':len(old_points),'current_openings':len(current_points),
            'key_questions':len(qs),'unresolved_image_links':links,'overview_leader_crossings':crossings,
            'labels_adjusted':changed,'relations':dict(Counter(r['type'] for r in data['relations']))}
    dump(work/'交付核验.json',report)
    print(p.name, json.dumps(report,ensure_ascii=False))
    assert code==0 and not links and not crossings


if __name__=='__main__':
    import sys
    generate(sys.argv[1])
