# 小规模GCN房间布局复原

本试验回应“给定房间清单和连接，预测每个房间位置与大小”。采用09号体检区做同图拟合，尚无独立验证或测试。这里只学习外接框，不生成建筑施工平面。

```bash
python -m unittest discover -s m-GCN模型/room_layout_pilot -p 'test_*.py' -v
python m-GCN模型/room_layout_pilot/run.py --project-root . --epochs 6000 --seeds 7 19 43
```

从项目根目录执行；使用已有NumPy和Pillow，不安装其他依赖。结果在 `e-实验评估/20261103_09体检区_GCN复原/run_时间戳/`，优先打开其中的 `结果说明.md` 和 `参考与GCN.png`。

- `data.py`：只读数据适配，模型输入与几何标签分开，识别图结构不可区分的节点。
- `model.py`：两层标准GCN、逐节点尺寸位置输出、解析梯度和Adam；无消息传递MLP作为对照。
- `evaluate.py`：框重合、位置尺寸误差、同类匹配、重叠诊断。
- `render.py`、`report.py`：比例保持的PNG/SVG和中文报告。
- `run.py`：多种子训练、权重、代码快照、日志、原始四文件SHA-256检查。
- `test_pilot.py`：泄漏隔离、置换等变、梯度数值校验、几何评分与训练下降检查。

给定access保留原概念含义，不能全部解释成直接开门。S123组合卫生间只参与关系上下文，不用作单间几何答案。未标关系不作不连通负例；源文件永不写回。

参考：[Kipf & Welling, GCN](https://arxiv.org/abs/1609.02907)。
