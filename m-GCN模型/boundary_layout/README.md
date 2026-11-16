# 建筑边界与空间清单条件下的布局基线

输入采用已知建筑边界与现有50维功能类别、空间层级、功能已知编码。边界按已知外轮廓归一化，长边为1，y轴向上。训练目标来自有效几何标签，房间与其他空间按掩码区分。

模型用32乘32的边界占用及距离场编码形状，通过图内均值消息聚合建立空间清单上下文。每个空间使用从已知边界内部抽取的随机槽位及随机变量，输出中心坐标、宽和高。输出矩形位于输入边界的外接矩形内，真实边界孔洞与凹形范围通过软距离场惩罚学习，并以精确多边形计算复核。

相同50维输入的有效监督节点使用最小代价匹配。监督按空间层级分别平均后汇总，并加入对数面积误差、边界越界及房间重叠惩罚。该匹配属于当前输入编码下的实例对应假设。功能名称、科室或空间角色不同的节点仍可能具有相同编码，需要后续研究更细的清单语义。

匹配采用SciPy线性分配函数。[官方说明](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linear_sum_assignment.html)

## 训练与测试

在项目根目录执行，环境依赖见`m-GCN模型/requirements-windows-gcn.txt`。首次新增匹配依赖可执行以下命令。

```powershell
uv pip install --python .venv/gcn-win/Scripts/python.exe scipy==1.18.1 --link-mode copy
.venv/gcn-win/Scripts/python.exe -X utf8 -m unittest discover -s m-GCN模型/boundary_layout -p 'test_*.py' -v
.venv/gcn-win/Scripts/python.exe -X utf8 m-GCN模型/boundary_layout/run.py --device cuda:1
```

默认沿用2026年11月16日关系模型实验冻结的48个暂定来源组，进行5折、3随机种子留出测试，每次最长120轮。每折使用一折测试、下一折验证，其余折训练。验证目标选择权重，连续5次检查未改善后早停，最早在第40轮停止。`--source-audit`可指定更新后的来源分组文件。

统计对照仅从训练来源学习各输入类别的位置与尺寸均值。神经网络每次生成4个候选，按固定几何惩罚选择，候选选择仅使用输入和预测。独立评分时应用掩码与匹配，房间和其他有效空间分别报告位置、面积和IoU，房间另报告重叠、越界。

结果保存至`e-实验评估/20261116_边界条件布局训练/run_时间戳/`。各折权重位于`fold_折号_seed_种子/weights.pt`，预测位于对应的`predictions/`。完成全部折后生成报告。

```powershell
.venv/gcn-win/Scripts/python.exe -X utf8 m-GCN模型/boundary_layout/report.py "结果目录的完整路径"
```

## 独立预测

`predict.py`支持仅含输入的JSON。必要字段为`inputs.node_features`和`inputs.boundary`，格式与训练导出一致。`node_ids`用于标记输出，可选的`feature_order`会与检查点校验。输入可以省略`targets`、`masks`及`metadata`。

```powershell
.venv/gcn-win/Scripts/python.exe -X utf8 m-GCN模型/boundary_layout/predict.py --checkpoint "权重完整路径" --input-json "边界清单输入.json" --output-json "布局预测.json" --device cuda:1
```

输出为相对坐标下的空间矩形候选。实际门洞、可行走廊路径及医疗交通组织仍需后续模块与专业评价。当前来源分组和概念轮廓适用于探索性验证。
