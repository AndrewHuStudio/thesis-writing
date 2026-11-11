from pathlib import Path
import json,math,sys
import xml.etree.ElementTree as ET
from shapely.geometry import Polygon,LineString
from shapely.ops import unary_union,split
import pymupdf
sys.path.insert(0,'/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts')
from annotation_tools import render,element,txt
from region_overlay import COLORS
B=Path(__file__).resolve().parents[2];O=Path(__file__).resolve().parent

def no_holes(p):
 if not p.interiors:return [p]
 ring=Polygon(p.interiors[0]);y=ring.representative_point().y
 parts=split(p,LineString([(p.bounds[0]-1,y),(p.bounds[2]+1,y)]))
 out=[]
 for part in parts.geoms:out.extend(no_holes(part))
 return out

for sample in sorted((B/'标注试样').iterdir()):
 if sample.name[:2] not in ['41','42','43','44','45']:continue
 q=O/sample.name;d=json.loads((sample/'annotation.json').read_text());state=json.loads((q/'review_state.json').read_text())
 spaces={s['id']:Polygon(s['polygon_px']) for s in d['spaces']}
 for reg in state['regions']:
  ids=set(reg['member_space_ids']);g=unary_union([spaces[i] for i in ids])
  # 仅跨越本图10—20像素的墙厚间隙；排除其他区域的既有空间。
  g=g.buffer(12,join_style=2).buffer(-12,join_style=2)
  others=unary_union([p for i,p in spaces.items() if i not in ids])
  g=g.difference(others).simplify(.01,preserve_topology=True)
  parts=[g] if g.geom_type=='Polygon' else [x for x in g.geoms if x.geom_type=='Polygon']
  parts=[x for p in parts for x in no_holes(p)]
  reg['polygons_px']=[[list(c) for c in list(p.exterior.coords)[:-1]] for p in parts]
  reg['boundary_basis']='按本图成员外边界及墙厚间隙勾勒；排除其他空间；多片段或内院不跨覆、不重复计面积。'
 (q/'review_state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
 render(d,sample/'annotation.json',sample/'标注.svg',q/'review_state.json')
 tree=ET.parse(sample/'标注.svg');root=tree.getroot();w=float(root.get('width'));oldh=float(root.get('height'))
 rows=math.ceil(len(state['regions'])/3);added=70+36*rows
 root.set('height',str(oldh+added));root.set('viewBox',f'0 0 {w} {oldh+added}')
 root.append(element('rect',{'x':0,'y':oldh,'width':w,'height':added,'fill':'white'}))
 root.append(txt(20,oldh+28,'区域概览（外轮廓不另计面积；区域成员不表示内部互通）',20,bold=True))
 for k,r in enumerate(state['regions']):
  root.append(txt(20+(k%3)*w/3,oldh+65+(k//3)*36,f'{r["id"]} {r["name"]}',19,COLORS[k%len(COLORS)],True))
 tree.write(sample/'标注.svg',encoding='utf-8',xml_declaration=True)
 doc=pymupdf.open(sample/'标注.svg');page=doc[0];page.get_pixmap().save(q/'正式SVG预览.png')
 # SVG页包含顶栏，原图坐标仍从plan的translate起算。
 head=max(65,min(125,d['image']['width']*.05))
 boxes={'41':[(830,245,1865,930),(845,1530,1740,2195)],
 '42':[(1170,1910,1850,2720)],'43':[(1250,700,1580,1400),(320,1550,2215,1860)],
 '44':[(1490,790,1980,1120),(1070,2180,1980,2550)],'45':[(775,230,1140,615),(425,1080,790,1245)]}
 for i,box in enumerate(boxes[sample.name[:2]],1):
  rect=pymupdf.Rect(box[0],box[1]+head,box[2],box[3]+head)
  page.get_pixmap(matrix=pymupdf.Matrix(1.7,1.7),clip=rect).save(q/f'正式SVG密集局部{i}.png')
 print(sample.name[:2],'region parts',sum(len(r['polygons_px']) for r in state['regions']))
