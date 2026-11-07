from sync_paths import P,R,W
from pathlib import Path
import json,sys,subprocess,xml.etree.ElementTree as ET,copy
# 图中门位P标签用白色描边底层和红色文字前层，兼容SVG栅格预览。
svg=P/'标注.svg';tree=ET.parse(svg);ns='{http://www.w3.org/2000/svg}'
for g in tree.iter(ns+'g'):
 if g.get('data-opening-id'):
  for t in list(g):
   if t.tag==ns+'text' and t.get('stroke')=='white':
    fg=copy.deepcopy(t)
    for attr in ['stroke','stroke-width','paint-order']:fg.attrib.pop(attr,None)
    g.append(fg)
tree.write(svg,encoding='unicode')
md=P/'标注说明.md'
assert md.read_bytes()==(W/'同步前备份/标注说明.md').read_bytes(),'填写在同步过程中有新变动，不能覆盖。'
body='''# 32_青岛大学附属医院东区病房综合楼｜标注草稿

<!-- annotation:summary:start -->
待更新概览。
<!-- annotation:summary:end -->

明确填写已同步；52—54按原话合并成电梯，S084存活，S085/S086退役。完整填写已归档，原核对号保持不变。8处中庭均不计室内面积。

### 核对33｜S053 房名

![33｜S053及相邻药房](../../临时核对/31-35_名称核对_20261106/32_青岛大学附属医院东区病房综合楼/20261107_填写同步与连通复核/33_房名核对.png)

**问题：**S053实际叫什么？原填写仍为“待确认”。

| 核对号 | S编号 | 预估名称（可改） | 备选名称 | 依据与把握 | 我的确认／备注 | 核对号（重复） |
| --- | --- | --- | --- | --- | --- | --- |
| 33 | S053 | 工作人员用房 | 办公 | 药房北侧独立小间，房名不能可靠辨读。把握：低。 | 待确认 | 33 |

### 核对20—22｜名称与房间对应复核

![20—24固定号局部](../../临时核对/31-35_名称核对_20261106/32_青岛大学附属医院东区病房综合楼/局部_08_核对20-24.png)

**问题：**原填写“20／S038＝卫生间、21／S039＝MIR、22／S040＝MIR”是否与房间对应无误？

**我的判断：**20、21为两间较大的房间，22为东侧小间，和旧稿的功能预估存在差异；保留您的原话，暂不挪动编号或改写“MIR”。

**我的确认／备注：**待确认（可填“按原填写”，或按20、21、22写正确名称）

### K01｜合并电梯S084的直接接入

![K01｜电梯及相邻CT、两侧大厅S号](../../临时核对/31-35_名称核对_20261106/32_青岛大学附属医院东区病房综合楼/20261107_填写同步与连通复核/K01_电梯连通.png)

**问题：**电梯S084直接连向南侧大厅S105、东侧大厅S099，还是经CT室S082接入？如本层不开放，也可注明。

**我的判断：**原图未见足以区分上述解释的清晰开口；暂不补连接或虚构门位，只需确认直接相连空间。

**我的确认／备注：**待确认（填实际相连的S号／名称；无需确定门位）
'''
md.write_text(body)
t='/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts/annotation_tools.py'
z=subprocess.run([sys.executable,t,'summary',str(P/'annotation.json'),'--output',str(md),'--review-state',str(R/'review_state.json')],capture_output=True,text=True);print(z.stdout);assert z.returncode==0
