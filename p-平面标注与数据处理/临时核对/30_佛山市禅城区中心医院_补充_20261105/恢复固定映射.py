from pathlib import Path
import ast,json
from shapely.geometry import Polygon,box
T=Path(__file__).parent
R=T.parent.parent/'标注试样/30_佛山市禅城区中心医院'
d=json.loads((R/'annotation.json').read_text())
old=(T/'历史取证/旧构建_只读.py').read_text()
rows={}
for line in old.splitlines():
 if not line.startswith('unk('):continue
 e=ast.parse(line).body[0].value
 key=ast.literal_eval(e.args[0]);coords=ast.literal_eval(e.args[1])
 if len(coords)==4 and isinstance(coords[0],(int,float)):coords=list(box(*coords).exterior.coords)[:-1]
 p=Polygon([[2443-y,x] for x,y in coords])
 s=min(d['spaces'],key=lambda s:p.symmetric_difference(Polygon(s['polygon_px'])).area)
 assert p.symmetric_difference(Polygon(s['polygon_px'])).area<.1
 if s['type']!='unknown':continue
 rows[s['id']]={'id':s['id'],'key':key,'polygon_px':s['polygon_px'],'candidates':ast.literal_eval(e.args[3]),'basis':ast.literal_eval(e.args[4]),'confidence':ast.literal_eval(e.args[5]) if len(e.args)>5 else '低'}
qs=[]
for s in d['spaces']:
 if s['type']=='unknown':qs.append(dict(number=f'{len(qs)+1:02d}',**rows[s['id']]))
assert len(qs)==31
for q in qs:
 if q['id']=='S060':q.update(candidates='库房／保洁用房',basis='残厕旁独立小间，文字模糊；位置不足以区分库房和保洁用途',confidence='低')
 if q['id']=='S070':q.update(candidates='景观水池／水景庭院',basis='可见蓝色水面和景观构筑物；需确认用途。若确认为庭院则不计室内面积，无需核对顶盖',confidence='中')
 if q['id']=='S073':q.update(candidates='景观庭院',basis='树木、景观台、步道及楼梯组成整体；建议按一个庭院节点保留，确认后不计室内面积',confidence='中')
 (T/'固定核对映射.json').write_text(json.dumps(qs,ensure_ascii=False,indent=2)+'\n')
print([(q['number'],q['id'],q['candidates']) for q in qs])
