from pathlib import Path
import json,collections,xml.etree.ElementTree as ET
P=Path('/Users/hushili/Documents/研究-论文写作/大论文/p-写作过程/标注试样/32_青岛大学附属医院东区病房综合楼')
a=json.loads((P/'annotation.json').read_text())
for s in a['spaces']:
 if s['type']=='vertical_core':s['name']='交通核'
(P/'annotation.json').write_text(json.dumps(a,ensure_ascii=False,indent=2)+'
')
