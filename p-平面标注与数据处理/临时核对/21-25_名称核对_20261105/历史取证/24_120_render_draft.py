from pathlib import Path
import subprocess,xml.etree.ElementTree as ET,json
P=Path('/Users/hushili/Documents/研究-论文写作/大论文/p-写作过程/标注试样/24_成都市第三人民医院住院综合楼')
base='/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts/annotation_tools.py'
for args in [['normalize',str(P/'annotation.json')],['render',str(P/'annotation.json'),'--output',str(P/'标注.svg')],['summary',str(P/'annotation.json'),'--output',str(P/'标注说明.md')]]:
 r=subprocess.run(['uv','run','--with','pymupdf','--with','shapely','python',base,*args],capture_output=True,text=True);assert r.returncode==0,r.stdout+r.stderr
 print(args[0],r.stdout.strip())
ns='{http://www.w3.org/2000/svg}'
p=P/'标注.svg';tree=ET.parse(p);root=tree.getroot()
for e in root.findall(ns+'text'):
 if e.text=='门诊平面结构化标注':e.text='24号｜住院综合楼首层功能标注草稿'
tree.write(p,encoding='unicode')
f=P/'标注说明.md';s=f.read_text().replace('# 平面标注概览','# 24_成都市第三人民医院住院综合楼｜标注草稿')
s=s.replace('未完成：45 个空间名称尚未确认。','未完成：45 个空间名称尚未确认；已建立 92 个空间／区域，47 项名称与用途可由图面文字或明确设施识别。')
s=s.replace('**标注规模：**','**本图范围：**仅处理本目录的单张平面。图内包含介入中心医技及医护／患者支持、静脉配液中心、住院入口与电梯交通、社保／住院缴费、医院街和综合教学区。按入口、公共服务及教学布局暂按首层功能平面理解，原图未给出清晰楼层标题。未见住院病房；门诊入口为公共大厅接口，不能据此把本图全部归为普通门诊。院外坡道、室外楼梯及其他楼层不计入室内空间。\n\n**标注规模：**',1)
s=s.replace('具体物理尺寸由生成环节按任务确定。','面积仅反映本图已标注室内范围的相对规模，不是建筑面积或平方米。')
s+='\n**判读精度：**按原图坐标保存概念轮廓；墙厚及少量边界缝隙不作为独立空间。交通核按整体节点保存，部分含其附属卫生间；社保、住院缴费与护士站为开放／半开放服务分区，范围为近似功能界线。相邻只在明确共墙时记 `shared_wall`；控制设备的技术联系不当作 `service`，也不据共墙推断人员可达。模糊门口、配液工艺顺序和未确认房间的通行关系暂不补造；未记关系不等于负样本。\n'
s+='\n**范围类别：**`interventional` 为介入医技及其支持；`intravenous_admixture` 为静脉配液中心；`inpatient_support` 为住院公共交通及服务；`education` 为教学培训；`public_service` 为公共大厅／医院街；`building_support` 为设备支持。共用类型补充 `education`（教学培训），用于已读出的演讲厅。\n'
s+='\n**当前状态：**这是名称核对草稿。全部 45 个疑点的核心名称均为“名称未确认”、类型均为 `unknown`；候选名称与连续核对号仅放临时材料，未写入核心 JSON。用户确认后同步 JSON、SVG 和说明，再正式核验。\n'
f.write_text(s)