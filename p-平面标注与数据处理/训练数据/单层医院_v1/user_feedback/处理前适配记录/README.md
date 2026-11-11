# 单层医院布局训练数据 v1

建立日期：2026-11-11。全53图保留为训练来源；未划分验证/测试集，未启动模型训练。

**已导出53份标准JSON、53份NPZ及53份逐图概念边界记录。49图可启用边界条件布局监督；45、46、49、53号因原始范围属性不明，保留数据并屏蔽这一监督项。原始212个四文件交付物保持不变。**

## 入口

- [逐图边界核验清单](边界核验清单.md)：每图外壳部件、孔洞、使用状态、叠加图及实际核验说明。
- [4图范围不确定项](范围不确定项.md)：当前受限的具体空间；不要求猜补房名。
- [manifest.json](manifest.json)：全53图样本索引及任务覆盖统计。
- [vocabulary.json](vocabulary.json)：全局共享type、level、特征列序和关系类型编码。
- [validation_report.json](validation_report.json)：全量机器校验结果。
- `review_evidence/`：29图可定位外部核对记录的只读快照；各样本provenance保存快照及审计记录哈希。
- [boundary_controls.json](boundary_controls.json)：逐图提取参数、视觉复核证据、组合名称训练粒度判断。
- [数据准备代码](../../../m-GCN模型/training_data_prep/README.md)：复现命令和字段说明。

## 本版数量

| 项目 | 数量 |
| --- | ---: |
| 单层图纸/训练样本 | 53 |
| 原有空间节点 | 8,436 |
| 概念外壳完成逐图叠加核验 | 53 |
| 边界条件布局监督可用图 | 49 |
| 节点几何标签可用 | 8,421 |
| 室内布局节点mask有效 | 8,310 |
| 上述节点中属于49图边界条件任务 | 7,959 |
| 功能类别已知 | 7,407 |
| 已知类别且按本轮物理粒度复核可作单房间候选 | 4,521 |
| 普通空间关系标签 | 9,672 |
| 暂缓关系损失的定位优先复核项 | 14条关系 |
| 入口/边界接口标签，单独保存 | 510 |
| 有明确证据的不连接access | 2 |
| 辅助区域标签 | 197 |

以上是任务mask覆盖数量，不是训练效果。候选单房间由既有room节点、功能可用性、本轮28项组合局部复核与几何/范围mask共同决定；未逐房重新确认全部医院语义。

28项组合名称已回看原图：20项为单一围合内的多用途表述，可恢复单房间候选；8项保留组合/不确定粒度，不做严格单房间布局监督。原名称和空间编号均未改变。具体判断和局部图在boundary_controls及边界预览中。

## 边界精度与范围

外壳对应**当前已标注单层范围的概念设计域**，不是实测外墙中心线，也不是把原图所有附图都合成一层。以已有空间定位范围，闭合墙厚小缝、去除内部房间分割痕迹后，逐图与原图叠加查看；保留明确庭院/挑空及分离组团。

每图外壳、孔洞、明确排除项、未分配内域与原始限制分别保存在边界记录中。室内尚未标注的白色内区不一律确认为庭院或可布置室内；`unallocated_inner_regions`保留提示，`full_domain_partition_mask=false`，本版不将整个域作为完整室内分区真值。

为对应“用户只画外边界”的实际场景，默认`inputs.boundary`只提供外壳；原图内部庭院位置及其它内部几何保存在标签侧。用户明确给定既有庭院/不可布置区时，可在未来适配器中额外传入该条件。

## 输入、标签与掩码

JSON按`inputs / targets / masks / provenance`分开：

- `inputs.node_features`：43维type、6维level、1维功能是否已知，共50列；不包含房间坐标、真实面积、S编号或scope文字。
- `inputs.boundary`：归一化单层外壳；可能有多个不相连部件。
- `inputs.provided_constraint_edges`：本版默认空。真实access保存在标签侧，未默认伪装成推理时已知的GNN图。
- `targets.boxes`：中心x、中心y、外接框宽、高；不是最终可施工房间多边形。
- `targets.polygons`、`area_normalized`：归一化轮廓与以长边平方为分母的面积。
- `targets.relations`、`entrances`：普通关系与边界接口分别保存；不将所有入口通过室外总节点互连。
- `targets.regions`：辅助区域几何已归一化；按层级监督，不能与内部房间面积重复累计。
- `masks.function`：已知功能标签的可用性。布局任务已经给定type时，不据此报告功能分类能力；辅助补名实验需要额外遮蔽已知输入，unknown仍无真值。
- `masks.geometry`：几何标签可用性；`masks.layout`进一步限制到当前室内布局口径。绿化、庭院作为单独对象/上下文保存，不计作室内房间分区。
- `masks.single_room / known_single_room`：分别约束物理粒度及功能条件；组合块仍保留为上下文或粗层级对象。
- `masks.boundary_condition`：是否可启用边界条件布局任务；4图的该值为false。
- `masks.full_domain_partition`：false；不将缺失/不明内域强制当成完整面积分区真值。

精确门位和入口位置的回归监督本版暂缓，原有定位数据保留。未记录关系没有自动补为负例，仅2条明确不连接证据进入负标签。

本版提供布局监督数据，正式GCN模型的候选图构造、随机实例表征和输出模块仍需单独设计。软件的“仅边界”模式还需前置空间配置推荐；本次没有将这一能力称为已训练完成。

## 坐标与尺度

原图左上原点、y向下；归一化后为局部左下原点、y向上。统一长边L缩放两个方向，保持长宽比：

```text
x_normalized = (x_px - xmin) / L
y_normalized = (ymax - y_px) / L
width_normalized = width_px / L
height_normalized = height_px / L
```

`coordinate_frame`保存逆变换所需原点和L。米/像素未校准时为null；本版不生成虚构平方米。用户新边界的实际尺寸可以用于将预测恢复到用户局部平面，再由几何工具检查排布。某些图含拍摄变形，因此本版精度保持概念相对层级。

## 读取示例

在Python中读取某份tensor：

```python
import numpy as np

with np.load(tensor_path, allow_pickle=False) as sample:
    x = sample['x']
    target = sample['y_bbox']
    usable = sample['layout_mask']
    boundary_task_enabled = bool(sample['boundary_condition_mask'])
```

NPZ避免object数组，不需要pickle。边界、房间多边形采用顶点加offset表示；关系用`relation_label_index`和`relation_label_type`表示，二者都是监督标签，不是默认输入edge_index。

样本索引保留全部原节点，mask决定对应任务是否计算损失。对于只用边界条件的布局实验，应同时使用`boundary_condition_mask`和相应节点mask；对单房间语义任务使用`known_single_room_mask`，并按图归一化损失，避免大图仅靠节点多支配训练。

11项单元测试及全量校验通过。验证覆盖53份JSON/NPZ的全部字段值逐项一致、共享编码、稳定编号、边界合法性、明确排除域、输入监督隔离、mask、关系引用、坐标逆变换、外部证据快照及212个源文件哈希。未进行模型训练或泛化评估。
