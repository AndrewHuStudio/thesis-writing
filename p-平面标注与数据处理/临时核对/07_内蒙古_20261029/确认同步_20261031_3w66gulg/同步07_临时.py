from pathlib import Path
import json,re,copy
BASE=Path(__file__).resolve().parent
PROJECT=Path((BASE/'项目路径.txt').read_text())
original=json.loads((BASE/'修改前备份/annotation.json').read_text())
responses=json.loads((BASE/'用户确认原名_临时.json').read_text())
# 特殊拆分、合并与面积项单独处理，避免把说明语句当作房间名。
SPECIAL={'66','112','113','114','115','118','195','200','203','208','268'}
EXACT={}
def group(typ,names):
 for name in names.split('|'):
  assert name not in EXACT,(name,typ)
  EXACT[name]=typ

group('staff_support','120值班|值班室|急诊值班|男更|新生值班|女更|护更|医生休息|值班|更衣|更衣室|淋浴|男浴|女浴|女更衣室|男更衣室|更衣刷手')
group('pharmacy','急诊药房|门诊药房|草药房')
group('staff_support','保安室')
group('storage','平车存放间|平车存放|敷料|库房|贵重药瓶|阴凉库|周转库|草药库')
group('entrance','门斗的一部分')
group('resuscitation','抢救室')
group('office','主任办公室|主任办|门诊部办公室|药房办公|财务办公|财务办公室|办公室|医办|办公')
group('registration','急诊挂号|挂号病房')
group('consultation','五官科|内科诊室|内科|外科|新生儿|诊室|儿童感染科|产后营养咨询|孕前诊室|孕前营养咨询')
group('treatment','治疗室|处置|清创室|换药|注射室|急诊输液室|隔离输液区|留观输液室|静脉穿刺|肌注|处置室|羊水穿刺室|拍背吸痰湿|肺感染雾化|普通雾化室|脱敏治疗室')
group('sterile_supply','消毒')
group('equipment_room','器械|计算机终端')
group('observation','急诊留观|留观室')
group('education','示教室|宣教室')
group('toilet','男厕|女厕|残厕|医厕|儿厕|厕所|卫生间')
group('laboratory','急诊化验|脱落细胞|抽血室')
group('imaging','B超|X光|CT扫描|超声')
group('examination','心电|胎心监护室|皮试|检查室|胎心监护|超神心电|肺功能室|过敏源点测试室|激发实验室|一氧化碳检测室|一氧化碳弥散检测室|产后检查')
group('operating_room','分娩人流手术室')
group('corridor','链接共享大厅的走廊|走廊|绿色通道')
group('hall','输液等候区|医护入口大厅')
group('medication_preparation','配药|煮药房|接药室|调钡室')
group('service','门诊用药咨询室|儿童活动区')
group('pharmacy_counter','取药窗口')
group('isolation','隔离诊室')
group('service_work_area','控制室')
group('patient_preparation','准备间')
group('equipment_room','设备机房')
group('staff_support','影相配套用房|影像配套用房')
group('building_services','空调机房')
group('conference','会议室')
group('rehabilitation','孕期运动训练室|产后恢复')
by={s['id']:s for s in original['spaces']}
updated=[]
for row in responses:
 num=str(int(row['number'])); name=row['name']
 if num in SPECIAL: continue
 assert name in EXACT,(num,name)
 s=by[row['id']]; s['name']=name;s['type']=EXACT[name]
 if s['type'] in {'corridor','hall','entrance','service'} and name in {'门斗的一部分','链接共享大厅的走廊','走廊','绿色通道','输液等候区','医护入口大厅','儿童活动区'}:s['level']='open_space'
 if s['type']=='pharmacy_counter':s['level']='semi_open_space'
 updated.append(row['number'])
(BASE/'同步中_临时.json').write_text(json.dumps(original,ensure_ascii=False,indent=2))
print('EXPLICIT_NAMES_CLASSIFIED',len(updated),'SPECIAL_CASES',len(SPECIAL))
print('REMAINING_UNKNOWN',[(s['id'],s['name']) for s in original['spaces'] if s['type']=='unknown'])
