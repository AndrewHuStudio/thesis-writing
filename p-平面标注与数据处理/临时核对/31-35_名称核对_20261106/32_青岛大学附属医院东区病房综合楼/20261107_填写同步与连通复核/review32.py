from sync_paths import P,R,W
from PIL import Image
import sys,json,pymupdf
sys.path.insert(0,'/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts')
from review_graphics import draw_question
p=P/'annotation.json';d=json.loads(p.read_text());state=json.loads((R/'review_state.json').read_text())
# 洗刷用途沿用原名；未确认消毒供应业务，不扩写成消毒供应功能。
next(s for s in d['spaces'] if s['id']=='S011')['type']='staff_support'
state['connectivity_items']=[{'review_id':'K01','source':'S084','target':'S105','status':'pending','reason':'合并后的电梯节点唯一对外连接尚不明：南侧S105、东侧S099或经S082均会改变主要关系，需要用户判断；无门位时仅记录概念连接'}]
state['checks']={'connectivity_reviewed':True,'visual_reviewed':False}
state['scope_notes']=['主要功能空间与主通行组织已逐区复核；K01电梯唯一接入仍待判断','中庭独立保留；无可见开口未补通行关系，不作为负例','小间内部细节未穷尽，见外部人工记录']
(P/'annotation.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');(R/'review_state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
with pymupdf.open(P/d['image']['file']) as doc:
 for rid in ['20','21','22','33']:
  i=next(i for i in state['name_items'] if i['review_id']==rid)
  draw_question(d,p,doc,state['name_items'],[i['space_id']],rid,f'{rid} | {i["space_id"]}',W/f'{rid}_房名核对')
 draw_question(d,p,doc,[],['S084'],'K01','K01 | S084 / S082 / S099 / S105',W/'K01_电梯连通')
# 额外读图，补查交通核和两个工作人员内部片区；不靠共墙补门。
im=Image.open(P/d['image']['file'])
for name,b in {'核心075':(875,1590,1045,1795),'北护士站':(1370,490,1540,595),'南护士站':(870,2310,1045,2435)}.items():
 im.crop(b).resize(((b[2]-b[0])*4,(b[3]-b[1])*4)).save(W/f'{name}_原貌.png')
print('已保留四项房名核对和K01电梯接入问题；其余用户填写已归档。')
