p='/Users/hushili/Documents/研究-论文写作/大论文/p-平面标注与数据处理/临时核对/38_梅州市蕉岭县中医医院/历史映射恢复/build_annotation.py'
s=open(p).read()
needle="# 取药窗口只记服务关系。"
new="""# 以下门口在放大图可见；仅记录概念联系，不存门位或门扇参数。
for n in range(1,11):rel('tech_north_'+str(n),'tech_north_passage')
for n in [1]:rel('radiology_'+str(n),'tech_north_passage')
for a,b in [('radiology_1','radiology_2'),('radiology_2','radiology_3'),('radiology_5','radiology_6')]:rel(a,b)
for n in [4,6,7,8,9,10,11,12,13,14]:rel('radiology_'+str(n),'radiology_passage')
for side,nums in [('west',range(1,11)),('east',range(1,10))]:
 for n in nums:rel('functional_'+side+'_'+str(n),'functional_passage' if side=='east' else 'radiology_passage')
for n in range(1,7):rel('tech_east_'+str(n),'functional_passage')
# 某些连续走道因单环数据结构分为支段，只有边界连续时记录相互可达。
for a in ordered:
 if a['type']!='corridor':continue
 for b in ordered:
  if a['key']>=b['key'] or b['type']!='corridor':continue
  if a['key'].split('_passage')[0]!=b['key'].split('_passage')[0]:continue
  if a['geom'].boundary.intersection(b['geom'].boundary).length>2:rel(a['key'],b['key'])
"""
s=s.replace(needle,new+needle)
# 功能检测西列开向放射影像东侧走道，此为物理开口，不自动当功能相同。
open(p,'w').write(s)