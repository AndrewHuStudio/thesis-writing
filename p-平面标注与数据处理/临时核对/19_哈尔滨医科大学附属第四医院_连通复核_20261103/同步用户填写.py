from pathlib import Path
import importlib.util
import json

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SAMPLE = ROOT / 'p-平面标注与数据处理/标注试样/19_哈尔滨医科大学附属第四医院门诊外科楼'
baseline = json.loads((OUT / '本轮基线.json').read_text())
backup = ROOT / baseline['backup']
data = json.loads((backup / 'annotation.json').read_text())
rows = json.loads((OUT / '本轮读取填写.json').read_text())
types = {
    '休息区': 'hall', '消控中心': 'building_control', '财务室': 'office',
    '主任办公室': 'office', '办公室': 'office', '诊室': 'consultation',
    '换药室': 'treatment', '儿科入口门厅': 'hall', '银行': 'retail_service',
    '电梯前室': 'vestibule', '收款': 'registration', '挂号': 'registration',
    '护士站': 'nurse_station', '配药': 'medication_preparation',
    '商务中心': 'retail_service', '用药咨询室': 'service_work_area',
    '儿童输液室': 'treatment', '主任室': 'office', '复印室': 'retail_service',
    '管井': 'building_services', '更衣室': 'staff_support', '备品室': 'storage',
    '库房': 'storage', '保安室': 'service_work_area', '超市': 'retail_service',
    '厕所前室': 'vestibule', '副主任办公室': 'office', '挂号示意室': 'registration',
    '配药工作间': 'medication_preparation', '输血前检验室': 'laboratory',
    '血型鉴定': 'laboratory', '采血室': 'laboratory', '配血室': 'laboratory',
    '财务办公室': 'office', '鲜花超市': 'retail_service', '麻药室': 'pharmacy',
    '中草药调剂室': 'medication_preparation', '资料室': 'storage',
    '医护办公': 'office', '医保办公室': 'office', '分发室': 'service_work_area',
    '储藏室': 'storage', '设备维修': 'building_services', '值班室': 'staff_support',
    '设备间': 'building_services', '观察、挂号': 'service_work_area',
    '预检分诊': 'triage', '导诊值班': 'triage', '儿科门诊': 'consultation',
    '处置室': 'treatment', '更衣休息': 'staff_support',
}
excluded = {'S141', 'S174', 'S175'}
by_id = {s['id']: s for s in data['spaces']}
updates = []
for row in rows:
    sid, answer = row['id'], row['answer']
    if sid in excluded or answer in {'待确认', '', '待定'}:
        continue
    before = [by_id[sid]['name'], by_id[sid]['type']]
    by_id[sid]['name'], by_id[sid]['type'] = answer, types[answer]
    if sid in {'S151', 'S152', 'S153'}:
        by_id[sid]['scope'] = 'pediatric'
    updates.append({'number': row['number'], 'id': sid, 'answer': answer, 'before': before, 'after': [answer, types[answer]]})
data['spaces'] = [s for s in data['spaces'] if s['id'] not in excluded]
data['relations'] = [r for r in data['relations'] if r['source'] not in excluded and r['target'] not in excluded]
spec = importlib.util.spec_from_file_location('annotation_tools', '/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts/annotation_tools.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.normalize(data)
(SAMPLE / 'annotation.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
(OUT / '名称同步后.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
(OUT / '用户填写落实记录.json').write_text(json.dumps({'confirmed_rows': updates, 'excluded': sorted(excluded), 'unknown': [s['id'] for s in data['spaces'] if s['type'] == 'unknown'], 'geometry': '保留其余稳定S编号及既有概念轮廓；本轮无合并指令。S028/S050改为电梯前室，S070改为厕所前室，S075/S083/S139/S140按用户名称确定当前概念单元，不进一步细分内部小间。'}, ensure_ascii=False, indent=2) + '\n')
print({'confirmed_rows': len(updates), 'changed_name_or_type': sum(x['before'] != x['after'] for x in updates), 'excluded': sorted(excluded), 'remaining': len(data['spaces']), 'unknown': [s['id'] for s in data['spaces'] if s['type'] == 'unknown']})
