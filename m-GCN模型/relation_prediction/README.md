# 53图access关系评分基线试跑

Windows显卡环境已于2026年11月14日配置并通过短运行、GPU测试与数据哈希核验。使用项目根目录下的`.venv/gcn-win/Scripts/python.exe`执行本目录`windows_batch.py --device cuda:1 --epochs 120`，依次运行三个随机种子。后台启动入口为`m-GCN模型/开始Windows训练.ps1`，详见`docs/Windows-GCN-training.md`。默认`run.py`仍使用CPU，可通过`--device cuda:1`指定显卡。

当前研究阶段为模型方案探索。本入口完成了数据读取、一次参数训练、权重保存和候选输出，后续模型定型需要输入图论证、监督假设核验和独立评价。

2026年11月16日复核，Windows批次`batch_20261114_103153_574675`的种子7、19、43均已完成120轮，权重重载和数据哈希核验通过。三组训练预算召回分别为14.46%、14.14%、14.49%。模型含8,449个可训练参数，每次训练循环日志耗时约48至58秒，整个批次约3分57秒。耗时口径与当前结果范围见[训练完成记录](../../docs/Windows-GCN-training.md#训练完成记录)。

给定空间清单，输出无向access候选分数。模型使用50维类型、层级和功能已知编码，两层残差GCN及对称空间对解码器。空间清单构成全连接输入图，图卷积聚合按图内均值实现。

本轮全部53图用于训练。监督为有效access正例、总体空间对的非负PU风险和少量明确负例。每图正类比例假设为已记录正例比例的2倍，上限0.5。该比例和正例抽样代表性尚未核实，分数作为探索性候选排序使用。

全连接图的均值聚合为各节点提供相同的图内上下文，自身投影保留类型与层级信息。同类、同层级且其余输入相同的空间具有相同表示，因此当前基线对具体空间实例的区分能力有限。训练集排序反映这一输入与结构选择下的拟合情况。

从项目根目录运行以下命令。

```bash
~/.local/bin/uv run --with torch==2.15.0 --with numpy==2.4.6 --with pillow==12.2.0 python -m unittest discover -s m-GCN模型/relation_prediction -p 'test_*.py' -v
~/.local/bin/uv run --with torch==2.15.0 --with numpy==2.4.6 --with pillow==12.2.0 python m-GCN模型/relation_prediction/run.py --epochs 120 --seed 7 --prior-multiplier 2
```

输出位于`e-实验评估/20261113_53图_GCN关系预测/run_时间戳/`。先查看`结果说明.md`和`verification.json`，候选JSON和全部空间对分数在`predictions/`中。

完整任务约定见`w-论文正文/GCN_train/03_53图首轮关系训练.md`。训练集召回按已有正例数确定预算并均摊并列分数。当前运行完成情况以结果目录中的`status.json`为准。

推理可在Python中加载权重，仅传入同词表的节点特征及待评分空间对。

```python
from model import load_checkpoint

model, checkpoint = load_checkpoint(checkpoint_path)
scores = model.score_pairs(node_features, candidate_pairs).sigmoid()
```

`model.py`和调用脚本需位于可导入路径。节点数可变化，类型与层级列序沿用检查点配置。相同输入节点得到相同表示，实际候选选择需要结合设计条件进一步检查。

## 来源分组对照

`benchmark_run.py`按医院名称与精确源文件哈希建立暂定来源组，对照训练来源关系统计、空间对MLP和现有GCN。每折训练、验证和测试来源组互斥，验证集选择神经网络权重。默认运行5折与3个随机种子，每次最长120轮。

```powershell
.venv/gcn-win/Scripts/python.exe -X utf8 m-GCN模型/relation_prediction/benchmark_run.py --device cuda:1
```

结果保存至`e-实验评估/20261116_关系模型分组对照/run_时间戳/`，包含来源审计、分折、逐轮验证记录、权重、留出预测及汇总。主指标为每图保留节点数n对候选时的已标注正例召回，先逐图计算再按来源组平均，保留并列均摊处理。未知空间对在PU训练和评价中保持未标注状态。

完成全部折后，可生成实验说明、来源分组核对表、分区字段清单和30对关系核对清单。

```powershell
.venv/gcn-win/Scripts/python.exe -X utf8 m-GCN模型/relation_prediction/benchmark_report.py "结果目录的完整路径"
```

2026年11月16日用户确认未来提供建筑边界与空间清单。当前三个对照方法沿用原有50维功能与层级输入，边界条件编码和多个布局方案生成属于后续模型实现。已有分区字段可研究作为辅助监督，输入条件以实际设计用途为准。暂定来源分组需结合项目身份核对，当前实验用于探索性比较。
