# 单层医院边界核验与训练样本导出 Implementation Plan

> **For agentic workers:** Use executing-plans inline. The user has authorized continuing the boundary extraction, normalization and mask export described in `e-实验评估/20261111_01-53_训练数据审计/检查报告与处理方案.md`; do not request the same authorization again.

**Goal:** 对53图逐图生成并图面核验概念级单层边界，导出来源可追溯、输入/监督隔离、带有效掩码的布局训练数据。

**Architecture:** 正式标注只读；原图、当前空间和外部核对作为证据。边界适配记录独立保存，保留多部件、明确排除域和不确定区。共享词表与同尺度坐标变换导出JSON及NPZ；完整真实关系作为标签，不默认作为输入图。

**Tech Stack:** Python、Shapely、Pillow、NumPy；使用现有uv缓存环境。

## Global Constraints

- 仅单层，全部53图进入训练池，不划分测试集，不启动模型训练。
- 原正式四文件212个保持SHA-256不变；不改原名称/编号/轮廓/关系。
- 单个代码文件最多599行。仅在新增适配代码和训练数据目录写入。
- 边界是基于当前图纸的概念可布置域，不承诺实测、精确墙线或建筑合规。
- unknown屏蔽功能监督；未知关系不当负例；粗细粒度分层；精确门位监督暂缓。
- 记录坐标方向、原点、统一长边尺度及逆变换；未校准真实尺度保持null。
- 不能凭自动闭合就设置图面核验通过；每图保存叠加预览和具体核验说明。
- 形状或室内外含义不能确认的区域，保存不确定域及相应任务掩码；不猜补事实。
- 保留现有工作区修改，不提交/上传，不执行清理。

## Task 1: 可靠的边界与样本转换函数

Files: `m-GCN模型/training_data_prep/{geometry.py,export.py,test_preparation.py}`。

- [x] 用单元测试覆盖庭院孔洞、分离组团、室内分割不泄漏、等比例变换及逆变换。
- [x] 运行测试确认所需能力缺失，再实现几何与导出函数。
- [x] 测试unknown功能mask、缺失关系不是负例、真实几何不进节点输入、边界未复核不能启用边界条件监督。

## Task 2: 53图边界提取与逐图核验

Files: `m-GCN模型/training_data_prep/{build.py,preview.py}`、`p-平面标注与数据处理/训练数据/单层医院_v1/边界记录/`。

- [x] 建立逐图参数与来源记录，在局部小间隙闭合后去除内部碎缝，保留明确庭院及独立组团。
- [x] 生成全图及目标范围叠加图，逐张查看；对外边界偏移、跨空地和额外图块调整记录。
- [x] 保存实际查看记录；不能确认的部分保持不确定区/待核，不自动升级为完整真值。
- [x] 根据原图复核28项组合名称；保留原标注，仅在训练粒度mask中作区别。

## Task 3: 导出全部53图

Files: `p-平面标注与数据处理/训练数据/单层医院_v1/{samples,tensors,manifest.json,vocabulary.json,README.md}`。

- [x] JSON区分inputs、targets、masks、provenance；共享type/level编码，scope原文不自动当统一功能输入。
- [x] NPZ保存节点特征、几何标签、边界坐标、关系标签及有效mask；不将真实access默认为GNN的edge_index。
- [x] loader能读取每图张量；真实尺度未知时保持未知，保留反变换记录。
- [x] 生成53图训练池清单、任务监督统计、范围与不确定项报告。

## Task 4: 完成核验

- [x] 运行转换单元测试、全量导出一致性与几何覆盖检查；任一错误不得报告全量成功。
- [x] 检查所有JSON/NPZ可读、节点顺序与编号一致、边界合法、排除域未填平、逆变换可还原。
- [x] 再次核实212个源文件SHA-256与审计基线一致，输出实际完成/待核数量。

本计划承接用户已接受的处理方案；执行中将按证据更新任务状态，最终交付数据包及使用说明。

## 执行结果

2026-11-11：53图完成概念外壳叠加核验并导出JSON/NPZ；49图边界条件任务启用，4图保留对应mask。28项组合复核中20项可作单一围合，8项保留组合/不确定粒度。11项单元测试及全量数据校验通过。实际数量与源文件保护结果以数据包validation_report.json为准。未训练模型、未划分测试集。
