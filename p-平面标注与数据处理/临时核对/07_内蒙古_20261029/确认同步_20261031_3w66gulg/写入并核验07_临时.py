from pathlib import Path
from collections import Counter
import json,hashlib,re,shutil,subprocess,sys
B=Path(__file__).resolve().parent
P=Path((B/'项目路径.txt').read_text());SK=Path('/Users/hushili/.codex/skills/outpatient-plan-annotation')
D=json.loads((B/'几何已调整_临时.json').read_text());by={s['id']:s for s in D['spaces']}
for sid,name,typ,lev in [('S151','儿科取药窗口','pharmacy_counter','semi_open_space'),('S153','门诊药房','pharmacy','functional_block'),('S154','儿科取药窗口','pharmacy_counter','semi_open_space'),('S155','内庭院','unknown','open_space'),('S165','准备间／休息间','unknown','room'),('S289','值班／阅片室','unknown','room'),('S402','内天井','unknown','open_space')]:
 by[sid].update(name=name,type=typ,level=lev)
# 无法解析的195原文只留用户表格，核心空间继续名称未确认。
assert by['S278']['type']=='unknown'
# 同步前保护其他进程可能写入的数据。
for name in ['annotation.json','标注.svg']:
 assert (P/name).read_bytes()==(B/'修改前备份'/name).read_bytes(),f'{name}已变化，停止写入'
source=P/D['image']['file']; source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
(B/'原图哈希.txt').write_text(source_hash)
typespath=SK/'references/space-types.json';shutil.copy2(typespath,B/'空间类别_修改前.json')
types=json.loads(typespath.read_text());types.update(operating_room='手术',rehabilitation='康复训练')
typespath.write_text(json.dumps(types,ensure_ascii=False,indent=2)+'\n')
(P/'annotation.json').write_text(json.dumps(D,ensure_ascii=False,indent=2)+'\n')
tool=SK/'scripts/annotation_tools.py'
commands=[['normalize',str(P/'annotation.json')],['render',str(P/'annotation.json'),'--output',str(P/'标注.svg')],['summary',str(P/'annotation.json'),'--output',str(B/'当前概览_临时.md')],['validate',str(P/'annotation.json'),'--check-dir']]
for args in commands:
 res=subprocess.run([sys.executable,str(tool)]+args,text=True,capture_output=True)
 (B/(args[0]+'_结果.txt')).write_text(res.stdout+'\n'+res.stderr)
 print(args[0],res.returncode,res.stdout[:700])
 assert res.returncode in ({0,2} if args[0]=='validate' else {0}),res.stderr
 if args[0]=='validate': report=json.loads(res.stdout)
assert report['valid'] and len(report['pending_name_ids'])==5,report
assert source_hash==hashlib.sha256(source.read_bytes()).hexdigest()
# 保留用户整份填写表，修复重复编号；只将概览更新为当前数据。
md=(B/'修改前备份/标注说明.md').read_text()
body=md[md.index('## 待确认空间名称预估表'):]
body=body.replace('## 待确认空间名称预估表','## 用户确认记录与待核实事项',1)
start=body.index('本表整合');end=body.index('以下按原有相邻片区分组')
body=body[:start]+'''本表保留用户填写原文、原核对号与候选依据，供本轮续作追溯。当前明确名称已同步到JSON及SVG；旧候选和旧把握是历史记录，不代表当前结论。后续请继续在“我的确认／备注”栏补充下述尚未解决的事项。原S编号对应保留；拆分新增或合并移除的编号在对应行注明。

'''+body[end:]
notes={
 '66':'已同步：S084刷手、S407更衣、S408准备间。',
 '112':'已同步窗口名称；112—114合并范围待核实，暂保留原区域。',
 '113':'已同步药房名称；与112、114是否合并待核实。',
 '114':'已同步窗口名称；112—114合并范围待核实，暂保留原区域。',
 '115':'名称已采用；露天／挑空或室内可步入属性待核实，暂保留unknown及室内面积口径。',
 '118':'名称已记录；是否两个独立房间待核实，暂保留unknown。',
 '195':'原文用途待澄清，暂保留名称未确认与unknown。',
 '200':'已记录拆分要求；上下房间名称对应待核实，暂保留unknown。',
 '203':'已同步：S295阅片室、S409办公室；办公室已包含原208区域。',
 '208':'已并入S409办公室，原S302已从核心JSON移除。',
 '268':'名称已采用；露天／挑空或室内可步入属性待核实，暂保留unknown及室内面积口径。'
}
new=[]
for line in body.splitlines():
 if re.match(r'^\|\s*\d+\s*\|',line):
  cells=[x.strip() for x in line.split('|')[1:-1]];assert len(cells)==7
  n=str(int(cells[0]));cells[6]=cells[0]
  cells[5]=cells[5]+'；'+notes.get(n,'已同步。')
  line='| '+' | '.join(cells)+' |'
 new.append(line)
body='\n'.join(new)+'\n'
summary=(B/'当前概览_临时.md').read_text().replace('# 平面标注概览','# 07 内蒙古自治区儿童医院、妇产医院、妇幼保健院外迁合建项目门诊医技楼一层标注',1)
summary=summary.replace('未完成：5 个空间名称尚未确认。','已同步明确填写结果；5个空间仍有面积属性、用途或拆分待核实，当前尚未正式完成。',1)
summary += '''
**范围与精度：**仅本张门诊医技楼一层，覆盖儿科急诊、妇产科急诊、输液中心、门诊药房、产科门诊、发热门诊与哮喘中心、影像中心、产科超声与围产保健及公共医疗街。统计为概念空间与通道分区数量，不是独立房间总数。用户已明确的拆分、合并已体现在边界和关系中；原有未记录关系不自动表示不可达，尚不构成完整通行图。

**当前待核实：**115内庭院、268内天井的露天／挑空／室内可步入属性；118准备间与休息间是否独立；195原文“值班室的对外清浅”的实际用途；200上方值班、下方阅片的对应。此外112—114的合并范围需与113“门诊药房”的填写核对。269“儿童活动区”暂按室内活动空间保留，若实际为露天请补充说明。

**面积口径：**115、268属性未明确前暂参与室内归一化；269按已填写的儿童活动区暂计室内。待属性明确后重新归一化，不能凭名称自动排除面积。

'''
(P/'标注说明.md').write_text(summary+body)
print('UPDATED_SAMPLE',P)
print('CORE_SPACES',len(D['spaces']),'CORE_RELATIONS',len(D['relations']))
