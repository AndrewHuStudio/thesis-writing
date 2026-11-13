# 53图access关系评分基线试跑

当前研究阶段为模型方案探索。本入口完成了数据读取、一次参数训练、权重保存和候选输出，后续模型定型需要输入图论证、监督假设核验和独立评价。

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
