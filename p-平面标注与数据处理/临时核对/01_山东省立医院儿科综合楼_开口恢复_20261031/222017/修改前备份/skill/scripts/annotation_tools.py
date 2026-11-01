#!/usr/bin/env python3
"""Render/check conceptual annotations. No automatic room recognition or training."""
from pathlib import Path
from collections import Counter
import argparse,base64,json,math,re,sys,xml.etree.ElementTree as ET

TYPE_NAMES=json.loads((Path(__file__).resolve().parent.parent/'references/space-types.json').read_text())
LEVELS={'room','open_space','semi_open_space','core_block','functional_block','landscape'}
LEVEL_NAMES={'room':'房间级单元','open_space':'开放空间','semi_open_space':'半墙服务区','core_block':'交通核','functional_block':'功能块','landscape':'绿化'}
SPACE_KEYS={'id','name','type','level','scope','polygon_px','area_ratio'}
REL_KEYS={'id','source','target','type','name','entrance_type','position_px'}
REL_NAMES={'access':'人员可达','service':'服务联系','shared_wall':'共墙','entrance':'入口连接'}
PENDING=re.compile(r'待核|未确认|未分类|未知|候选|待定|unknown|tbd|\?',re.I)
NS='http://www.w3.org/2000/svg';XL='http://www.w3.org/1999/xlink'
ET.register_namespace('',NS);ET.register_namespace('xlink',XL)

def load(path):
    return json.loads(Path(path).read_text())

def polygon_area(points):
    return abs(sum(points[i][0]*points[(i+1)%len(points)][1]-points[(i+1)%len(points)][0]*points[i][1] for i in range(len(points)))/2)

def indoor(s):
    return s['type'] not in {'landscape','courtyard'} and s['level']!='landscape'

def unresolved(data):
    return [s for s in data['spaces'] if not str(s.get('name','')).strip() or PENDING.search(str(s.get('name',''))) or s.get('type')=='unknown']

def check(data,path,allow_incomplete=False,check_dir=False):
    from shapely.geometry import Polygon
    errors=[]
    if set(data)!={'image','spaces','relations'}:errors.append('顶层仅允许 image、spaces、relations。')
    image=data.get('image',{});w=image.get('width',0);h=image.get('height',0)
    if not isinstance(w,(int,float)) or not isinstance(h,(int,float)) or w<=0 or h<=0:errors.append('图像宽高无效。')
    source=Path(path).parent/str(image.get('file',''))
    if not source.is_file():errors.append('原图文件不存在。')
    spaces=data.get('spaces',[]);ids=[s.get('id') for s in spaces]
    if not spaces or len(ids)!=len(set(ids)) or any(not isinstance(i,str) or not i for i in ids):errors.append('空间编号为空或重复。')
    polygons=[]
    for s in spaces:
        sid=s.get('id','?')
        required=SPACE_KEYS-{'area_ratio'}
        if not required<=set(s) or not set(s)<=SPACE_KEYS:errors.append(f'{sid}: 空间字段不符约定。');continue
        if s['type'] not in TYPE_NAMES:errors.append(f'{sid}: 新类型 {s["type"]} 尚未加入共享类型表。')
        if s['level'] not in LEVELS:errors.append(f'{sid}: 空间层级无效。')
        pts=s['polygon_px']
        try:
            assert len(pts)>=3
            assert all(len(p)==2 and all(isinstance(v,(int,float)) and math.isfinite(v) for v in p) for p in pts)
            assert all(0<=x<=w and 0<=y<=h for x,y in pts)
            poly=Polygon(pts);assert poly.is_valid and poly.area>0;polygons.append((sid,poly))
        except (AssertionError,TypeError,ValueError):errors.append(f'{sid}: 多边形无效或超出原图。')
        if indoor(s) and not (isinstance(s.get('area_ratio'),(int,float)) and 0<s['area_ratio']<=1):errors.append(f'{sid}: 缺少有效的相对面积。')
        if not indoor(s) and 'area_ratio' in s:errors.append(f'{sid}: 非室内区域不参与室内面积归一化。')
    for i,(a,pa) in enumerate(polygons):
        for b,pb in polygons[i+1:]:
            if pa.intersection(pb).area>1:errors.append(f'{a}/{b}: 标注区域重叠，会重复计面积。')
    total=sum(s.get('area_ratio',0) for s in spaces if isinstance(s.get('area_ratio',0),(int,float)))
    if not math.isclose(total,1,abs_tol=1e-6):errors.append('室内相对面积占比合计须为 1。')
    rels=data.get('relations',[]);rids=[r.get('id') for r in rels]
    if len(rids)!=len(set(rids)) or any(not i for i in rids):errors.append('关系编号为空或重复。')
    keys=set()
    for r in rels:
        rid=r.get('id','?');typ=r.get('type');a=r.get('source');b=r.get('target')
        if not {'id','source','target','type'}<=set(r) or not set(r)<=REL_KEYS:errors.append(f'{rid}: 关系字段不符约定。')
        if typ not in REL_NAMES or b not in ids:errors.append(f'{rid}: 关系类型或目标空间无效。')
        if typ=='entrance':
            if a is not None or not {'name','entrance_type','position_px'}<=set(r):errors.append(f'{rid}: 入口关系无效。')
            if not str(r.get('name','')).strip() or PENDING.search(str(r.get('name',''))):errors.append(f'{rid}: 入口名称未确认。')
            q=r.get('position_px',[])
            if len(q)!=2 or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in q) or not(0<=q[0]<=w and 0<=q[1]<=h):errors.append(f'{rid}: 入口坐标无效。')
            key=(rid,a,b,typ)
        else:
            if a not in ids or a==b:errors.append(f'{rid}: 起点无效或自连接。')
            if any(k in r for k in ['position_px','entrance_type']):errors.append(f'{rid}: 普通连接不保存门坐标。')
            key=tuple(sorted([str(a),str(b)]))+(str(typ),)
        if key in keys:errors.append(f'{rid}: 重复空间关系。')
        keys.add(key)
    if check_dir:
        files=[f for f in Path(path).parent.iterdir() if f.is_file()]
        if len(files)!=4 or sum(f.suffix.lower()=='.svg' for f in files)!=1 or sum(f.suffix.lower()=='.md' for f in files)!=1 or sum(f.suffix.lower()=='.json' for f in files)!=1:errors.append('最终图纸目录应只有原图、SVG、JSON、MD 四文件。')
    pending=[s['id'] for s in unresolved(data)]
    return {'valid':not errors,'names_complete':not pending,'pending_name_ids':pending,'errors':errors,'spaces':len(spaces),'relations':len(rels)}, (1 if errors else 2 if pending and not allow_incomplete else 0)

def normalize(data):
    areas={s['id']:polygon_area(s['polygon_px']) for s in data['spaces'] if indoor(s)}
    total=sum(areas.values())
    if total<=0:raise ValueError('没有可归一化的室内空间。')
    for s in data['spaces']:
        s.pop('area_m2',None);s.pop('area_px2',None);s.pop('area_ratio',None)
        if s['id'] in areas:s['area_ratio']=round(areas[s['id']]/total,8)

def element(tag,attrs=None,text=None):
    e=ET.Element('{'+NS+'}'+tag,{k:str(v) for k,v in (attrs or {}).items()})
    if text is not None:e.text=text
    return e

def txt(x,y,text,size=14,color='#18314c',bold=False):
    return element('text',{'x':x,'y':y,'font-size':size,'font-family':'Arial, PingFang SC, Microsoft YaHei, sans-serif','fill':color,'font-weight':'700' if bold else '400'},text)

def source_data(data,path):
    source=Path(path).parent/data['image']['file'];ext=source.suffix.lower()
    if ext in ['.jpg','.jpeg','.png']:
        mime='image/png' if ext=='.png' else 'image/jpeg';return f'data:{mime};base64,'+base64.b64encode(source.read_bytes()).decode()
    import pymupdf
    doc=pymupdf.open(source)
    if len(doc)!=1:raise ValueError('请先选定 PDF 页，并将每页作为独立图纸样本处理。')
    p=doc[0];w=data['image']['width'];h=data['image']['height']
    pix=p.get_pixmap(matrix=pymupdf.Matrix(w/p.rect.width,h/p.rect.height),alpha=False)
    return 'data:image/png;base64,'+base64.b64encode(pix.tobytes('png')).decode()

def visual_width(text,font):
    return sum(font*(.58 if ord(c)<128 else 1) for c in text)

def wrap(text,font,width):
    rows=['']
    for c in text:
        if rows[-1] and visual_width(rows[-1]+c,font)>width:rows.append('')
        rows[-1]+=c
    return rows

def place_label(poly,s):
    from shapely.geometry import LineString,box
    a=poly.representative_point();x,y=a.x,a.y
    horizontal=poly.intersection(LineString([(poly.bounds[0]-1,y),(poly.bounds[2]+1,y)]))
    vertical=poly.intersection(LineString([(x,poly.bounds[1]-1),(x,poly.bounds[3]+1)]))
    def span(g):
        gs=list(g.geoms) if hasattr(g,'geoms') else [g]
        lines=[q for q in gs if q.geom_type=='LineString' and q.distance(a)<.01]
        return max(lines,key=lambda q:q.length).bounds if lines else poly.bounds
    hb=span(horizontal);vb=span(vertical)
    maxw=max(12,min(220,hb[2]-hb[0]-6));maxh=max(10,vb[3]-vb[1]-6)
    pending=s['type']=='unknown' or PENDING.search(s['name'])
    name='名称未确认' if pending else s['name']
    for font in [14,12,11,10,9,8,7]:
        lines=([s['id']+' '+name] if maxh<42 else [s['id']]+wrap(name,font,maxw-8))
        lw=max(visual_width(row,font) for row in lines)+8;lh=len(lines)*(font+2)+5
        if lw>maxw or lh>maxh:continue
        r=box(x-lw/2,y-lh/2,x+lw/2,y+lh/2)
        if poly.covers(r):return x-lw/2,y-lh/2,lw,lh,font,lines
    # Very thin irregular shapes still get their full visible name, attached
    # to an interior anchor; the source remains zoomable.
    lines=[s['id']]+wrap(name,7,max(12,maxw-6));lw=max(visual_width(row,7) for row in lines)+6;lh=len(lines)*9+4
    return x-lw/2,y-lh/2,lw,lh,7,lines

def render(data,path,output):
    from shapely.geometry import Polygon
    w=data['image']['width'];h=data['image']['height'];head=max(65,min(125,w*.05));foot=max(20,min(35,w*.015))
    root=element('svg',{'width':w,'height':h+head+foot,'viewBox':f'0 0 {w} {h+head+foot}'})
    root.append(element('rect',{'width':w,'height':h+head+foot,'fill':'white'}))
    pending=unresolved(data);fs=max(10,min(30,w/70))
    root.append(txt(12,fs+10,'门诊平面结构化标注',fs,bold=True))
    status=f'未完成：{len(pending)} 个空间名称未确认' if pending else f'{len(data["spaces"])} 个具名空间／区域；名称已齐'
    root.append(txt(12,fs*2+17,status,max(8,fs*.65),'#b45309' if pending else '#166534'))
    g=element('g',{'id':'plan','transform':f'translate(0 {head})'});root.append(g)
    g.append(element('image',{'width':w,'height':h,'{'+XL+'}href':source_data(data,path)}))
    palette=['#2563eb','#0f766e','#7c3aed','#15803d','#b45309','#0369a1','#a21caf','#475569']
    polygons={s['id']:Polygon(s['polygon_px']) for s in data['spaces']}
    for s in data['spaces']:
        p=polygons[s['id']];is_pending=s in pending
        import hashlib
        color='#d97706' if is_pending else palette[int(hashlib.sha256(s['type'].encode()).hexdigest()[:4],16)%len(palette)]
        if s['level']=='semi_open_space':color='#059669'
        sg=element('g',{'id':s['id'],'data-space-name':s['name']});g.append(sg)
        sg.append(element('title',text=f'{s["id"]} | {s["name"]} | {TYPE_NAMES.get(s["type"],s["type"])}'))
        attrs={'points':' '.join(f'{x},{y}' for x,y in s['polygon_px']),'fill':color,'fill-opacity':'.07','stroke':color,'stroke-width':max(1,w/1400)}
        if is_pending or s['level']=='semi_open_space':attrs['stroke-dasharray']='6 3'
        sg.append(element('polygon',attrs))
        x,y,lw,lh,font,lines=place_label(p,s)
        sg.append(element('rect',{'x':x,'y':y,'width':lw,'height':lh,'rx':2,'fill':'#fff7df' if is_pending else 'white','fill-opacity':'.94','stroke':color,'stroke-width':'.8'}))
        for i,line in enumerate(lines):sg.append(txt(x+4,y+font+2+i*(font+2),line,font,color,bold=True))
    for r in data['relations']:
        if r['type']!='entrance':continue
        x,y=r['position_px'];p=polygons[r['target']].representative_point();dx=x-p.x;dy=y-p.y;length=math.hypot(dx,dy) or 1
        font=max(8,min(15,w/180));label=r['id']+' '+r['name'];lw=visual_width(label,font)+14;lh=font+10
        bx=max(2,min(w-lw-2,x+dx/length*46-lw/2));by=max(2,min(h-lh-2,y+dy/length*46-lh/2))
        eg=element('g',{'id':r['id']});g.append(eg)
        eg.append(element('line',{'x1':x,'y1':y,'x2':bx+lw/2,'y2':by+lh/2,'stroke':'#be185d','stroke-width':'2'}))
        eg.append(element('circle',{'cx':x,'cy':y,'r':max(3,w/400),'fill':'white','stroke':'#be185d','stroke-width':'2'}))
        eg.append(element('rect',{'x':bx,'y':by,'width':lw,'height':lh,'rx':3,'fill':'white','stroke':'#be185d'}))
        eg.append(txt(bx+7,by+font+3,label,font,'#9d174d',True))
    root.append(txt(12,h+head+foot-7,'空间名称随 SVG 显示；黄色表示名称未确认。概念级标注不记录施工门位。',max(7,min(14,w/150)),'#52677b'))
    ET.ElementTree(root).write(output,encoding='unicode')

def summary(data,output):
    types=Counter(s['type'] for s in data['spaces']);levels=Counter(s['level'] for s in data['spaces']);rels=Counter(r['type'] for r in data['relations']);pending=unresolved(data)
    state=f'未完成：{len(pending)} 个空间名称尚未确认。' if pending else '空间名称已齐；结构与关系仍以原图及人工核对为依据。'
    lines=['# 平面标注概览','',state,'',f'**标注规模：**{len(data["spaces"])} 个空间／区域，'+ '、'.join(f'{LEVEL_NAMES[k]} {v} 个' for k,v in levels.items())+'。','',
        '**类型与数量：**'+'、'.join(f'{TYPE_NAMES.get(k,k)} {v} 个' for k,v in types.items())+'。','',
        f'**连接关系：**{len(data["relations"])} 条，'+ '、'.join(f'{REL_NAMES[k]} {v} 条' for k,v in rels.items())+'。','',
        '**入口：**'+'、'.join(r['name'] for r in data['relations'] if r['type']=='entrance')+'。','',
        '**相对规模：**室内非重叠标注区域的 `area_ratio` 合计为 1；绿化不参与。具体物理尺寸由生成环节按任务确定。施工级门构造及内部精确路线不纳入数据。']
    if pending:lines.extend(['','**名称待确认：**'+'、'.join(s['id']+' '+s['name'] for s in pending)+'。此图尚不能宣布打标完成。'])
    Path(output).write_text('\n'.join(lines)+'\n')

def questions(data,path,out_dir):
    import pymupdf
    out=Path(out_dir);out.mkdir(parents=True,exist_ok=True);doc=pymupdf.open(Path(path).parent/data['image']['file']);page=doc[0];w=data['image']['width'];h=data['image']['height']
    pending=unresolved(data)
    for i,s in enumerate(pending,1):
        xs=[p[0] for p in s['polygon_px']];ys=[p[1] for p in s['polygon_px']];cw=max(250,max(xs)-min(xs)+100);ch=max(180,max(ys)-min(ys)+90);cx=(min(xs)+max(xs))/2;cy=(min(ys)+max(ys))/2
        x1=max(0,cx-cw/2);y1=max(0,cy-ch/2);x2=min(w,x1+cw);y2=min(h,y1+ch)
        clip=pymupdf.Rect(x1/w*page.rect.width,y1/h*page.rect.height,x2/w*page.rect.width,y2/h*page.rect.height)
        pix=page.get_pixmap(matrix=pymupdf.Matrix(2,2),clip=clip,alpha=False)
        root=element('svg',{'width':1200,'height':800,'viewBox':'0 0 1200 800'});root.append(element('rect',{'width':1200,'height':800,'fill':'white'}))
        root.append(txt(25,45,f'{i:02d} · {s["id"]}：请确认粉框内空间名称',26,bold=True))
        scale=min(1120/(x2-x1),600/(y2-y1));ww=(x2-x1)*scale;hh=(y2-y1)*scale;ox=40+(1120-ww)/2;oy=90+(600-hh)/2
        root.append(element('image',{'x':ox,'y':oy,'width':ww,'height':hh,'{'+XL+'}href':'data:image/png;base64,'+base64.b64encode(pix.tobytes('png')).decode()}))
        root.append(element('rect',{'x':ox+(min(xs)-x1)*scale,'y':oy+(min(ys)-y1)*scale,'width':(max(xs)-min(xs))*scale,'height':(max(ys)-min(ys))*scale,'fill':'none','stroke':'#b91c72','stroke-width':3}))
        root.append(txt(25,755,'请只说明名称／用途，无需补施工门位。',20,'#52677b'))
        raw=ET.tostring(root,encoding='unicode');pymupdf.open(stream=raw.encode(),filetype='svg')[0].get_pixmap(alpha=False).save(out/f'{i:02d}_{s["id"]}.png')
    (out/'编号对应.txt').write_text('\n'.join(f'{i:02d}: {s["id"]}' for i,s in enumerate(pending,1))+'\n')

def main():
    parser=argparse.ArgumentParser(description=__doc__);subs=parser.add_subparsers(dest='command',required=True)
    for command in ['validate','normalize','render','summary','questions']:
        p=subs.add_parser(command);p.add_argument('json_path')
        if command=='validate':p.add_argument('--allow-incomplete',action='store_true');p.add_argument('--check-dir',action='store_true')
        if command in ['render','summary']:p.add_argument('--output',required=True)
        if command=='questions':p.add_argument('--out-dir',required=True)
    args=parser.parse_args();path=Path(args.json_path);data=load(path)
    if args.command=='normalize':
        normalize(data);path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');print('Relative area normalized; absolute-area fields removed.');return 0
    result,code=check(data,path,allow_incomplete=getattr(args,'allow_incomplete',False),check_dir=getattr(args,'check_dir',False))
    if args.command=='validate':print(json.dumps(result,ensure_ascii=False,indent=2));return code
    if result['errors']:print(json.dumps(result,ensure_ascii=False,indent=2));return 1
    if args.command=='render':render(data,path,args.output)
    elif args.command=='summary':summary(data,args.output)
    else:questions(data,path,args.out_dir)
    print(json.dumps({'written':getattr(args,'output',getattr(args,'out_dir',None)),'pending_name_ids':result['pending_name_ids']},ensure_ascii=False));return 0

if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,KeyError,TypeError,OSError,ImportError) as e:print(f'ERROR: {e}',file=sys.stderr);sys.exit(1)
