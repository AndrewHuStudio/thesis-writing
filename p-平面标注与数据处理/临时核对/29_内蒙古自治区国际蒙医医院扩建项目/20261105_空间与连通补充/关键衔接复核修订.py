from pathlib import Path
import json,re
from PIL import Image,ImageDraw,ImageFont
from shapely.geometry import Polygon,Point
base=Path('/Users/hushili/Documents/研究-论文写作/大论文/p-平面标注与数据处理');root=base/'标注试样/29_内蒙古自治区国际蒙医医院扩建项目';w=base/'临时核对/29_内蒙古自治区国际蒙医医院扩建项目/20261105_空间与连通补充'
d=json.loads((root/'annotation.json').read_text());d['relations']=[r for r in d['relations'] if not(r['source']=='S017' and r['target']=='S052')];(root/'annotation.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
added=json.loads((w/'本轮补充关系.json').read_text());added=[r for r in added if not(r['source']=='S017' and r['target']=='S052')];(w/'本轮补充关系.json').write_text(json.dumps(added,ensure_ascii=False,indent=2)+'\n')
records=json.loads((w/'review-data.json').read_text());font='/System/Library/Fonts/STHeiti Medium.ttc'
def f(n):return ImageFont.truetype(font,n)
s=(w/'补充关系与填写材料.py').read_text();exec(s[s.index('source=Image.open'):s.index('# Preserve the historical numbering')])
connrows=[r for r in records if r['key'].startswith('west_connect') or r['id'] in ['S016','S017']]
mark_crop(connrows,(325,1100,1100,1845),w/'L01_大厅连续分区复核.png','29号｜L01 已补充的公共大厅连续分区',mode='space')
mark_crop([r for r in records if r['id'] in ['S017','S052']],(560,1340,1460,1520),w/'K01_主楼大厅衔接待核对.png','29号｜K01 主楼公共大厅衔接',mode='space')
md=(root/'标注说明.md').read_text().replace('96 条，人员可达 89 条','95 条，人员可达 88 条').replace('补充16条','补充15条').replace('S017—S052为主楼公共大厅的连续衔接，','').replace('、S017↔S052','').replace('当前89条','当前88条')
md+='\n### K01｜主楼公共大厅 S017 与 S052\n\n![K01：主楼大厅衔接，房内数字对应S编号]('+__import__('os').path.relpath(w/'K01_主楼大厅衔接待核对.png',root)+')\n\n**问题：**公共大厅 S017 是否直接连向中段大厅 S052？\n\n**我的判断：**两侧灰色通行区域相接，但交界处黑线较重，现图不能可靠区分隔墙、开口或分区线；这会影响主楼与中段的主要连接，本轮暂不写入 access。\n\n**我的确认／备注：**待填写（可填“直接相通”或说明实际连接方式，无需确定具体门位）\n'
(root/'标注说明.md').write_text(md)
# Recalculate only the graph inventory after withdrawing this uncertain bridge.
g={s['id']:set() for s in d['spaces']}
for r in d['relations']:
 if r['type']=='access':g[r['source']].add(r['target']);g[r['target']].add(r['source'])
seen=set();comps=[]
for a in g:
 if a in seen:continue
 stack=[a];seen.add(a);c=[]
 while stack:
  a=stack.pop();c.append(a)
  for b in g[a]-seen:seen.add(b);stack.append(b)
 comps.append(sorted(c))
p=json.loads((w/'连通盘点.json').read_text());p['after']={'components':sorted(comps,key=lambda c:-len(c)),'degree_zero':[k for k,v in g.items() if not v],'opening_count':0};p['added_access']=15;(w/'连通盘点.json').write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n')
md=md.replace('当前人员可达图有136个已记录分量',f'当前人员可达图有{len(comps)}个已记录分量');(root/'标注说明.md').write_text(md)
print('relations',len(d['relations']),'added',len(added),'components',len(comps),'pending_connectivity',1)
