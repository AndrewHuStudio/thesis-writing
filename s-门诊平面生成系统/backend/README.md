# 门诊平面生成后端 Demo

此目录先提供独立 Python 后端，暂不依赖 Rhino 界面。输入是以米为单位的二维闭合边界与门诊空间清单，输出是可供 Rhino 建模使用的坐标、质检和概念评估 JSON。四阶段由 LangGraph 顺序执行，当前任务仅在本进程中保留检查点。

## Windows 快速运行

从仓库根目录执行，复用现有 PyTorch、Shapely 和 NetworkX 环境，不修改训练脚本：

```powershell
$backend = 's-门诊平面生成系统/backend'
$python = '.venv/gcn-win/Scripts/python.exe'
uv pip install --python $python -r "$backend/requirements.txt"
& $python -X utf8 "$backend/run.py" run --input "$backend/examples/l_shape.json"
& $python -X utf8 -m unittest discover -s $backend -p 'test_*.py' -v
```

上例使用已确认的合成清单和两组真实 GCN 权重，只在本地运行。若另需保存报告，增加 `--out` 指定一个不存在的文件。

## 有任务书、无任务书

从仓库根目录的本地 `.env`（或环境变量）读取 `APIYI_BASE_URL`、`APIYI_API_KEY`。需求分析（聊天、清单拟定和修改）读取 `APIYI_DEEPSEEK_MODEL`（默认 `deepseek-v4-flash`），可选布局建议读取 `APIYI_MODEL`（默认 `gpt-5.4-mini`）。默认不联网；只有显式传入 `--allow-api` 才调用 API 易。任务书先在本地提取，上传时只发送文字及边界摘要。选择真实任务书之前，先由使用者确认并脱敏；不发送原文件、边界坐标或模型权重，也不记录密钥。

```powershell
$draft = Join-Path $env:TEMP ('outpatient-draft-' + [guid]::NewGuid().ToString('N') + '.json')
& $python -X utf8 "$backend/run.py" propose --input "$backend/examples/l_shape.json" --brief "$backend/examples/brief.txt" --allow-api --out $draft
# 省略 --brief 时，模型根据边界摘要拟定房间清单，仍需确认。
# 检查并修订 $draft 后再生成；后一步的 --allow-api 只用于匿名拓扑建议，可省略。
& $python -X utf8 "$backend/run.py" run --input "$backend/examples/l_shape.json" --program $draft --allow-api
```

- 任务书支持 `.txt`、`.docx` 和文本型 `.pdf`。扫描件无 OCR，空文件会报错，不会默默切换到无任务书模式。任务书没写的关键尺寸可在草稿中留空，确认前必须补齐。
- 草稿通过 `--out` 交给用户核对；无任务书时，模型只能建议可选连接，不会将推测标为必连或禁连。`run --program` 视为调用方已完成确认。使用示例中的内嵌 `program` 效果相同。
- 第二阶段发送房间匿名 ID、类型、允许的可选关系和分数。若外部建议失败，报告中标记降级，仍可使用本地 GCN；外部建议不能修改必连、禁连、面积和净宽。

## 输入、输出与适用边界

- `boundary` 首尾点必须相同，每点为 `[x, y]`。支持单个最大跨度 60 米的直线围合单区，允许凹形和斜边。建议明确指定从零开始编号的 `entrance_edge`；省略时取最长边并标记为建议入口。
- 每次生成 2–12 间矩形房，使用 0.5 米搜索网格；房间直连只在共享边上有符合宽度的门洞才算实现。布局从现有 GCN 预测起步，算法只尝试两种确定性的走廊与摆位搜索，不保证任意边界下都能找到方案。
- 标准输出为一行一条 UTF-8 JSON，包含 `stage` 事件和最终 `result` 或 `error`。成功报告包含坐标已转换回输入坐标系的平面与评估，模型候选框另外标为局部坐标。退出码 `0` 表示完成或草稿可审，`2` 表示两次搜索或审查均未找到可交付布局，`1` 表示输入或工具错误。
- 视觉可达性采用二维直视线，流线共用长度采用指定起终点的最短示意路线。未设置分析对象时明确标记未评估。示例参数不是规范阈值；这些结果不表示建筑或临床合规。
