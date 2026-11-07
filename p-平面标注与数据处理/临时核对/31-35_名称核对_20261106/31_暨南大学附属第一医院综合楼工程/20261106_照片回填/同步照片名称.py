"""Apply only readable names from the five user-supplied photographs."""
import hashlib
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

WORK = Path(__file__).resolve().parent
REVIEW = WORK.parent
BATCH = REVIEW.parent
ROOT = BATCH.parents[1] / '标注试样'
PROJECT = ROOT / REVIEW.name
SAMPLE = PROJECT / 'annotation.json'
BACKUP = WORK / '同步前备份'
BACKUP.mkdir(exist_ok=True)
assert not (WORK / '已同步.json').exists(), 'Do not reapply over later user edits'
for file in list(PROJECT.iterdir()) + [REVIEW/'review_state.json', REVIEW/'固定核对映射.json']:
    if file.is_file():
        shutil.copy2(file, BACKUP/file.name)
data = json.loads(SAMPLE.read_text())
before = json.loads(SAMPLE.read_text())
spaces = {s['id']: s for s in data['spaces']}
mapping = json.loads((REVIEW/'固定核对映射.json').read_text())
state = json.loads((REVIEW/'review_state.json').read_text())
old_md = (PROJECT/'标注说明.md').read_text()
for line in old_md.splitlines():
    if re.match(r'\| \d+ \| S\d+ \|', line):
        assert line.split('|')[6].strip() == '待确认', 'Read and preserve new user answers before applying'

# Exact readable strings, with shared functional types and the existing scopes.
updates = {
    'S001': ('药品统计','office','room','pharmacy'),
    'S007': ('二十四小时发药','pharmacy','room','pharmacy'),
    'S013': ('摆药大厅','medication_preparation','functional_block','pharmacy'),
    'S014': ('静脉输液配置中心','medication_preparation','functional_block','pharmacy'),
    'S015': ('杂物库','storage','room','pharmacy'),
    'S017': ('出院取药','pharmacy','room','pharmacy'),
    'S019': ('值班管理处','office','room','staff_support'),
    'S021': ('消防控制中心','building_control','room','building_support'),
    'S022': ('综合布线','building_services','room','building_support'),
    'S023': ('库房','storage','room','building_support'),
    'S026': ('物品库','storage','room','staff_support'),
    'S032': ('客服中心','service','semi_open_space','inpatient_service'),
    'S033': ('出入院手续办理','registration','semi_open_space','inpatient_service'),
    'S034': ('健康咨询中心','service','functional_block','public_service'),
    'S037': ('候药厅','hall','open_space','public_service'),
    'S043': ('公共电梯厅','vertical_core','core_block','public_service'),
    'S052': ('试管辅料','storage','room','imaging'),
    'S053': ('控制室','service_work_area','room','imaging'),
    'S054': ('DSA','imaging','room','imaging'),
    'S060': ('设备机房','building_services','room','imaging'),
    'S061': ('发片室','service_work_area','room','imaging'),
    'S080': ('储片室','storage','room','imaging'),
}
corrections = {
    'S012': ('中药库','storage'), 'S016': ('西药库','storage'),
    'S049': ('共享大厅','hall'), 'S073': ('医生走廊','corridor'),
    'S079': ('洗片室','service_work_area'),
    'S082': ('女更浴','staff_support'), 'S083': ('男更浴','staff_support'),
}
changes = []
for sid, values in updates.items():
    s = spaces[sid]
    assert s['type'] == 'unknown'
    previous = {key:s[key] for key in ['name','type','level','scope']}
    s.update(zip(['name','type','level','scope'],values))
    changes.append(dict(space_id=sid,previous=previous,result={key:s[key] for key in previous},
                        evidence='用户补充照片可读文字；助手图像判读，并非用户逐项口头确认'))
for sid,(name,typ) in corrections.items():
    s = spaces[sid]
    previous = dict(name=s['name'],type=s['type'])
    s.update(name=name,type=typ)
    changes.append(dict(space_id=sid,previous=previous,result=dict(name=name,type=typ),
                        evidence='照片清晰文字纠正旧稿名称'))
for item in state['name_items']:
    sid = item['space_id']
    if sid in updates:
        item.update(status='resolved',confirmed_name=spaces[sid]['name'],applied=True,
                    evidence='2026-11-06用户补充照片可读文字',source='user_supplied_photographs',
                    image_files=[f'20261106_照片回填/用户补充照片_{i:02d}.jpg' for i in range(1,6)])
state['checks'].update(connectivity_reviewed=False,visual_reviewed=False)
assert data['relations'] == before['relations']
assert all(s['polygon_px'] == before['spaces'][i]['polygon_px'] for i,s in enumerate(data['spaces']))
assert [s['id'] for s in data['spaces']] == [s['id'] for s in before['spaces']]
pending = [s['id'] for s in data['spaces'] if s['type']=='unknown']
assert pending == ['S040','S042','S044','S045']
SAMPLE.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
(REVIEW/'review_state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
(WORK/'已同步.json').write_text(json.dumps(dict(resolved=22,corrected_existing=7,pending=pending,
               changes=changes,original_sha256=hashlib.sha256((PROJECT/data['image']['file']).read_bytes()).hexdigest()),
               ensure_ascii=False,indent=2)+'\n')
print('Resolved 22 unknowns; corrected 7 names; pending:',pending)
