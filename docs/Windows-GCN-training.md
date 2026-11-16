# Windows GCN训练

2026年11月14日在本机配置。训练使用仓库已有53图关系评分基线，当前结果属于训练池诊断。两张NVIDIA RTX 4500 Ada各有24GB显存，本轮选用第二张卡`cuda:1`。

## 环境

项目环境位于`.venv/gcn-win/`，由Git忽略。已安装Python 3.12.7、PyTorch 2.11.0+cu128、NumPy 2.5.4、Pillow 13.0.0、Shapely 2.2.0和tzdata 2026.6。PyTorch来自官方CUDA 12.8轮子索引。通用依赖因默认下载源超时，使用清华大学PyPI镜像完成安装。

在另一台Windows机器复建时，从项目根目录运行以下命令。已有环境可省略第一条。

```powershell
uv venv --python 3.12 .venv/gcn-win
uv pip install --python .venv/gcn-win/Scripts/python.exe torch==2.11.0 --index-url https://download.pytorch.org/whl/cu128 --link-mode copy
uv pip install --python .venv/gcn-win/Scripts/python.exe -r m-GCN模型/requirements-windows-gcn.txt --index-url https://pypi.tuna.tsinghua.edu.cn/simple --link-mode copy
```

使用随PyTorch二进制包提供的CUDA运行库。显卡驱动需支持该运行库，本机已通过实际显卡计算验证。

## 启动训练

从项目根目录执行以下命令。脚本在后台依次运行种子7、19、43，每次120轮，并返回进程号和启动日志路径。

```powershell
powershell -NoProfile -File .\m-GCN模型\开始Windows训练.ps1
```

脚本调用本仓库训练程序，结果与日志保存在项目中。

希望在当前终端直接查看任务完成消息时，运行以下命令。

```powershell
.venv/gcn-win/Scripts/python.exe -X utf8 m-GCN模型/relation_prediction/windows_batch.py --device cuda:1 --epochs 120
```

结果位于`e-实验评估/20261114_Windows显卡训练/batch_时间戳/`。批次`status.json`保存当前种子和已完成结果。每次训练的`seed_数字.log`记录进度，`seed_数字/`保存权重、配置、曲线、预测及哈希核验。

## 查看进度

在项目根目录运行以下命令。

```powershell
$batch = Get-ChildItem -LiteralPath 'e-实验评估/20261114_Windows显卡训练' -Directory -Filter 'batch_*' | Sort-Object Name | Select-Object -Last 1
Get-Content -Encoding UTF8 -LiteralPath (Join-Path $batch.FullName 'status.json')
nvidia-smi
```

`running`表示正在执行，`complete`表示三次训练及其结果核验均完成，`failed`需查看批次和对应种子的日志。训练时应保持电脑开机并避免休眠。

## 本轮检查

### 训练完成记录

2026年11月16日复核，批次`batch_20261114_103153_574675`及三个种子的`status.json`均为`complete`，每次完成120轮。批次完成状态文件写入时间为2026年11月14日10时35分50秒。三份`weights.pt`均已保存，训练时的权重重载分数最大差为0，重载指标一致，55项输入及371项源文件哈希核验通过。

| 随机种子 | 完成轮数 | 训练循环耗时 | 宏平均训练风险 | 训练预算召回 |
| --- | --- | --- | --- | --- |
| 7 | 120 | 48.000秒 | 0.101402 | 14.46% |
| 19 | 120 | 58.093秒 | 0.104254 | 14.14% |
| 43 | 120 | 53.156秒 | 0.101829 | 14.49% |

训练循环耗时取各自`progress.jsonl`最后一轮的`elapsed_seconds`。计时从初始诊断之后开始，覆盖逐轮训练及此前轮次的周期诊断，最后一轮耗时字段在该轮诊断之前写入。数据加载、初始诊断、最终评价、结果导出和权重重载核验另需时间。批次目录时间为10时31分53秒，至完成状态写入约3分57秒。

结果、配置、逐轮日志和训练曲线见[本轮结果目录](../e-实验评估/20261114_Windows显卡训练/batch_20261114_103153_574675/)，汇总状态见[批次状态](../e-实验评估/20261114_Windows显卡训练/batch_20261114_103153_574675/status.json)。

### 训练较快的原因与结果范围

本轮读取已整理的53份图数据。每个空间节点使用50维功能类别、层级及功能已知编码，两层32维隐藏特征的图卷积和对称关系解码器共含8,449个可训练参数。全连接输入图的归一化消息聚合通过图内特征均值实现，计算量较小。

每轮使用全部53图，每8图更新一次参数，每轮7次更新，120轮共840次参数更新。每图每轮均匀有放回抽取1,024个总体空间对用于PU总体风险估计，同时使用全部有效正例及明确负例计算监督损失。全空间对诊断每10轮执行一次。上述规模结合RTX 4500 Ada显卡，解释了本轮较短的训练耗时。

当前任务输出空间对的无向access候选分数。全部53图参加训练，表中指标属于训练池诊断，独立分组评价与完整平面布局生成仍待后续工作。三组最低诊断风险均出现在第120轮，充分收敛情况及新平面预测效果仍需进一步评价。

GPU前向与反向计算、7项关系模型测试及13项数据准备测试已通过。显卡适配保留原默认CPU入口，并补充GPU输入搬运、诊断结果转回CPU、中文UTF-8读写与Windows绘图字体支持。

本轮仍使用现有50维输入及PU监督假设。三次重复训练用于Windows环境验收和随机种子诊断，独立分组评价与输入条件改进需在后续实验中完成。
