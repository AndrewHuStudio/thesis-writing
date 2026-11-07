from pathlib import Path
import json
O=Path('/Users/hushili/Documents/研究-论文写作/大论文/p-平面标注与数据处理/临时核对/28_广东省人民医院心脑血管专科医院一期项目/20261105_首次补充')
s=(O/'历史取证/62_command.txt').read_text().split("<<'PY'\n",1)[1].split('\nD=dict(',1)[0]
s=s.replace('p-写作过程','p-平面标注与数据处理')
s=s.replace("a('em_obs','留观区','observation',", "u('em_obs',").replace("[885,2276],[577,2276]],level='functional_block')", "[885,2276],[577,2276]],'输液区／留观区','大量重复座椅或床位示意，急诊相邻；原名末字不清','中',level='functional_block')")
s=s.replace("a('em_duty','急诊值班室','staff_support',(889,2221,969,2276))", "u('em_duty',(889,2221,969,2276),'消毒室／治疗支持用房','护士站下方独立房间，字形疑似消毒','中')")
s=s.replace("a('out_phlebo','门诊采血区','laboratory',(1639,2230,1695,2518),level='semi_open_space')", "u('out_phlebo',(1639,2230,1695,2518),'挂号收费／门诊服务柜台','蓝色长条空间朝大厅布置多个服务位，文字疑似挂号收费','中',level='semi_open_space')")
ns={};exec(s,ns)
r=ns['reviews']
for i,q in enumerate(r,1):q['number']=f'{i:02d}'
(O/'固定核对映射.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('Recovered',len(r),'spaces',len(ns['spaces']))
