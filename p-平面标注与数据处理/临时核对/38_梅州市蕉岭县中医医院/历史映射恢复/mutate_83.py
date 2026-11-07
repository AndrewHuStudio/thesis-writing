p='/Users/hushili/Documents/研究-论文写作/大论文/p-平面标注与数据处理/临时核对/38_梅州市蕉岭县中医医院/历史映射恢复/build_annotation.py'
s=open(p).read().replace('from shapely.geometry import Polygon,box','from shapely.geometry import Polygon,box,LineString').replace('from shapely.ops import unary_union','from shapely.ops import unary_union,split')
s=s.replace("items=[]","""items=[]
def simple_parts(geom):
 gs=[geom] if geom.geom_type=='Polygon' else [g for g in geom.geoms if g.geom_type=='Polygon']
 out=[]
 while gs:
  g=gs.pop()
  if not g.interiors:out.append(g);continue
  h=Polygon(g.interiors[0]);x=h.representative_point().x
  parts=split(g,LineString([(x,g.bounds[1]-1),(x,g.bounds[3]+1)]))
  assert len(parts.geoms)>1
  gs.extend(parts.geoms)
 return out
""")
s=s.replace("gs=[geom] if geom.geom_type=='Polygon' else list(geom.geoms)","gs=simple_parts(geom)")
s=s.replace("[(268,645),(350,645)","[(279,645),(350,645)")
s=s.replace("(165,780),(268,780)]","(165,780),(268,780),(268,710),(279,710)]")
s=s.replace("(165,702,268,780)","Polygon([(165,702),(221,702),(221,710),(268,710),(268,780),(165,780)])")
s=s.replace("(165,1058,268,1164)","(165,1058,270,1165)")
s=s.replace("remaining('radiology_passage','放射影像室公共通道',(889,607,1147,1025),im,3)","remaining('radiology_passage','放射影像室公共通道',[(1001,607),(1039,607),(1039,944),(1105,944),(1105,607),(1147,607),(1147,1025),(969,1025),(969,918),(1001,918)],im,3)")
s=s.replace("remaining('functional_passage','功能检测室公共通道',(1148,607,1351,1025),ft,3)","remaining('functional_passage','功能检测室公共通道',[(1215,607),(1256,607),(1256,924),(1318,924),(1318,607),(1351,607),(1351,925),(1317,925),(1317,1025),(1215,1025)],ft,3)")
s=s.replace("remaining('tech_east_passage','医技东侧通道',(1352,607,1427,1025),mt,3)","")
s=s.replace("'tech_east_passage'","'functional_passage'")
# 同一节点替换产生的自环不写入。
s=s.replace("if a not in bykey or b not in bykey:return","if a not in bykey or b not in bykey or a==b:return")
# 任何几何洞必须在写入前处理，核心格式只保存单环轮廓。
s=s.replace("coords=[to_original(x,y)","assert not it['geom'].interiors,it['key']\n coords=[to_original(x,y)")
open(p,'w').write(s)