import json,sys
from pathlib import Path
sys.path.insert(0,'/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts')
import annotation_tools as at
P=Path('/Users/hushili/Documents/研究-论文写作/大论文/p-写作过程/标注试样/21_海军总医院外科医疗大楼');T=Path('/tmp/outpatient21-review')
d=json.loads((P/'annotation.json').read_text());items=json.loads((T/'reading_items.json').read_text());bykey={i['key']:i for i in items};byid={i['id']:i for i in d['spaces']}
i=bykey['derm'];i.update(name='名称未确认',type='unknown',candidate='烧伤 / 皮肤',evidence='两字图面近烧伤，床与诊桌并置',confidence='中');byid[i['id']].update(name='名称未确认',type='unknown')
# Correct overly strong direct-access claims where the room doorway is unclear.
blocked={bykey[k]['id'] for k in ['med1','med2','surgery']}
d['relations']=[r for r in d['relations'] if not (r['type']=='access' and r['source'] in blocked)]
# Main southern door has a clearly drawn two-door vestibule and adjacent service strip.
for ix,(key,name,typ,b,level) in enumerate([
 ('main_south_vest','南入口门斗','entrance',(1433,1558,1605,1610),'open_space'),
 ('main_map','导医图服务区','service',(1288,1558,1431,1610),'open_space'),
 ('main_phone','电话及ATM服务区','service',(1607,1558,1840,1610),'open_space')],152):
 x1,y1,x2,y2=b;rp=[[x1,y1],[x2,y1],[x2,y2],[x1,y2]];sid=f'S{ix:03d}'
 item=dict(key=key,id=sid,name=name,type=typ,level=level,scope='public_service',rpoly=rp,group=6,candidate='',evidence='',confidence='高');items.append(item)
 d['spaces'].append({k:item[k] for k in ['id','name','type','level','scope']}|dict(polygon_px=[[2443-y,x] for x,y in rp]))
 d['relations'].append(dict(id=f'R{ix:03d}',source=sid,target=bykey['inpatient_hall']['id'],type='access'))
for r in d['relations']:
 if r['id']=='E003':r.update(target='S152',position_px=[2443-1610,1528])
at.normalize(d)
(P/'annotation.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
(T/'reading_items.json').write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n')
print('154 spaces; 19 unresolved; southern entry vestibule included; unclear accesses removed.')