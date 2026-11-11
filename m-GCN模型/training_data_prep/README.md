# 单层医院训练数据准备

用于逐图概念边界适配、共享编码、等比例坐标转换、任务掩码和JSON/NPZ导出。没有改动现有09号同图拟合代码。

数据入口：[单层医院_v1](../../p-平面标注与数据处理/训练数据/单层医院_v1/README.md)。全部53图为train，未划分测试集、未启动模型训练。

代码职责：

- `geometry.py`：外壳候选、孔洞保留、坐标归一化及逆变换。
- `export.py`：严格分离输入、标签和任务mask。
- `build.py`：逐图边界记录、共享词表、JSON/NPZ和manifest导出。
- `preview.py`：原图叠加、内域不确定项与28项组合名称局部图。
- `validate_dataset.py`：全53图数据一致性与原212文件哈希核验。
- `test_preparation.py`：庭院、分离组团、内部划分泄漏、坐标还原、unknown和任务mask等测试。

从大论文根目录执行，使用现有uv缓存环境：

```bash
~/.local/bin/uv run --offline --with shapely --with pillow --with pymupdf python -m unittest discover -s m-GCN模型/training_data_prep -p 'test_*.py' -v
~/.local/bin/uv run --offline --with shapely --with pillow --with pymupdf python m-GCN模型/training_data_prep/build.py --stage boundaries
~/.local/bin/uv run --offline --with shapely --with pillow --with pymupdf python m-GCN模型/training_data_prep/preview.py
~/.local/bin/uv run --offline --with shapely --with pillow --with pymupdf python m-GCN模型/training_data_prep/build.py --stage export
~/.local/bin/uv run --offline --with shapely --with pillow --with pymupdf python m-GCN模型/training_data_prep/validate_dataset.py
```

边界参数或人工外壳变更后，旧的`reviewed_shape_sha256`会失效，需查看新的叠加图并更新核验记录。程序不会因自动闭合成功就把边界置为已核验。

本轮运行环境记录在数据包`environment.json`。原标注四文件只读，所有新结果在训练数据目录；不运行原样本normalize/render/summary。
