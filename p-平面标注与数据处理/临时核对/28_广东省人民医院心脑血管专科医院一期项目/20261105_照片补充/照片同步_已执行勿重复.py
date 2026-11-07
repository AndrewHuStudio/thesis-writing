from pathlib import Path
import json
P=next(Path('/Users/hushili/Documents/研究-论文写作/大论文/p-平面标注与数据处理/标注试样').glob('28_*'));O=P.parents[1]/'临时核对'/P.name/'20261105_照片补充'
d=json.loads((O/'照片同步前四文件与用户填写备份/annotation.json').read_text());by={s['id']:s for s in d['spaces']}
# 名称依据本轮照片逐项目读；OCR只作辅助，未用于自动定名。
changes={
14:('更衣室','staff_support'),15:('更衣室','staff_support'),3:('护长','office'),13:('辅料间','storage'),1:('打包区','sterile_supply'),2:('示教室','education'),4:('值班室','staff_support'),5:('值班室','staff_support'),9:('清洗消毒区','sterile_supply'),12:('灭菌区','sterile_supply'),17:('无菌物品库','storage'),18:('一次性物品库','storage'),19:('拆包区','sterile_supply'),20:('洗车间','sterile_supply'),21:('烘车间','sterile_supply'),23:('洁具间','building_services'),24:('发放区','sterile_supply'),25:('存车间','storage'),26:('存车间','storage'),
53:('打印室','office'),54:('登记室','registration'),59:('气瓶间','building_services'),64:('资料室','storage'),65:('值班室','staff_support'),66:('值班室','staff_support'),70:('主任办公室','office'),71:('资料室','storage'),73:('备用检查室','reserved_space'),76:('备用检查室','reserved_space'),83:('病人更衣室','patient_preparation'),84:('病人更衣室','patient_preparation'),85:('值班室','staff_support'),86:('值班室','staff_support'),90:('男更衣室','staff_support'),91:('女更衣室','staff_support'),92:('示教室','education'),93:('备用检查室','reserved_space'),96:('备用检查室','reserved_space'),98:('胃肠机房','imaging'),99:('灌肠室','patient_preparation'),100:('打印室','office'),108:('银行','retail_service'),
115:('准备室','patient_preparation'),118:('抢救室','resuscitation'),121:('楼梯交通核','vertical_core'),122:('设备间','equipment_room'),124:('配药室','medication_preparation'),125:('男更衣室','staff_support'),126:('主任办公室','office'),128:('DSA检查室','imaging'),129:('DSA控制室','imaging'),130:('女更衣室','staff_support'),132:('更衣室','staff_support'),133:('库房','storage'),134:('检验室','laboratory'),135:('值班室','staff_support'),136:('值班室','staff_support'),137:('值班室','staff_support'),138:('配药室','medication_preparation'),142:('护士站','nurse_station'),149:('留观室','observation'),150:('留观室','observation'),151:('留观室','observation'),152:('留观室','observation'),153:('留观室','observation'),
154:('门诊电梯厅','hall'),162:('挂号收费','registration'),192:('保安室','building_control'),193:('协调办','office'),195:('更衣室','staff_support')}
new=[];corrections=[]
for n,(name,typ) in changes.items():
 s=by[f'S{n:03d}'];(new if s['type']=='unknown' else corrections).append(dict(id=s['id'],before=s['name'],after=name));s.update(name=name,type=typ)
by['S121']['level']='core_block';by['S142']['level']='semi_open_space';by['S154']['level']='open_space'
# 旧识读与新照片冲突而字形仍有歧义的两项退回unknown，不沿用旧猜测。
for n in [123]:by[f'S{n:03d}'].update(name='名称未确认',type='unknown')
removed=[]
remove_ids={'R041','R043','R027','R113','R115','R116','R224'}
for r in d['relations']:
 if r['id'] in remove_ids:removed.append(r)
d['relations']=[r for r in d['relations'] if r['id'] not in remove_ids]
seq=max(int(r['id'][1:]) for r in d['relations'] if r['id'].startswith('R'));added=[];inferred=[]
def pair(a,b,typ='access',infer=False):
 global seq
 a=f'S{a:03d}';b=f'S{b:03d}'
 for r in d['relations']:
  if r['type']==typ and {r['source'],r['target']}=={a,b}:return r
 seq+=1;r=dict(id=f'R{seq:03d}',source=a,target=b,type=typ);d['relations'].append(r);added.append(r.copy())
 if infer:inferred.append([a,b])
 return r
pseq=max(int(p['id'][1:]) for r in d['relations'] for p in r.get('openings',[]));located=[]
def mark(a,b,x,y,kind='door'):
 global pseq
 r=pair(a,b);pseq+=1;o=dict(id=f'P{pseq:03d}',kind=kind,position_px=[x,y]);r.setdefault('openings',[]).append(o);located.append(dict(relation=r['id'],source=r['source'],target=r['target'],**o))
# MR检查室按控制室组织人员进入；仅做布局推断，不造门位。
pair(46,47,infer=True);pair(48,47,infer=True)
mark(47,44,631,1276)
# 清楚的供应区门；物流箭头越过灭菌设备不当作人员门。
mark(1,13,653,669);mark(17,18,650,762);mark(9,22,392,791);mark(9,23,414,791);mark(19,25,778,792);mark(19,26,819,792);mark(24,27,752,845)
pair(17,24,infer=True)
# 急诊电梯厅朝门诊大厅开放，准备室门朝电梯厅；护士站提供输液服务。
mark(115,116,971,2237);pair(116,110,infer=True);pair(114,112,'service');pair(114,115,infer=True)
# DSA控制室组织进入，删除误作南向直接门的P046，保留其编号退役不复用。
pair(128,129,infer=True);mark(129,141,650,2480)
# 挂号收费半墙工作区不借服务窗创建门；已有柜台service保留。
(P/'annotation.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
record=dict(new_names=new,corrected_names=corrections,returned_unknown=['S123'],removed_relations=removed,added_relations=added,inferred=inferred,new_openings=located,retired_openings=['P046'],remaining_unknown=[s['id'] for s in d['spaces'] if s['type']=='unknown'])
(O/'照片同步变更记录.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
print('new_names',len(new),'corrected_names',len(corrections),'remaining_unknown',len(record['remaining_unknown']),'relations',len(d['relations']),'openings',sum(len(r.get('openings',[])) for r in d['relations']))
print('pending',record['remaining_unknown'])
