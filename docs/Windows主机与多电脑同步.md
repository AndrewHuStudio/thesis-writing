# Windows 主机与多电脑同步

更新日期：2026-11-07。适用仓库：`AndrewHuStudio/thesis-writing`（私有）。本文说明如何将已有论文、标注及 GCN 小试验带到 Windows 主机，不代表整套平面生成系统已经实现。

## 第一次在 Windows 主机使用

安装 Git for Windows、Git LFS、GitHub CLI 和 Python 3.13；论文 DOCX 使用 Word 或兼容的办公软件打开。下列命令在 PowerShell 执行。GitHub 登录时使用有该私有仓库权限的账号；登录通过浏览器完成，不把令牌写入项目文件。

```powershell
gh auth login
gh auth setup-git
git lfs install
git clone https://github.com/AndrewHuStudio/thesis-writing.git
cd thesis-writing
git lfs pull
git lfs fsck
git status --short
```

项目文件及历史资料需要数 GB 本地空间，克隆还会创建 Git 对象。首次下载需等待完成。大 PDF 通过 Git LFS 管理，不能仅下载 GitHub ZIP 后就假定资料完整。`git lfs fsck` 应返回 `Git LFS fsck OK`；工作区状态应为空。

若 `git lfs install` 提示已有钩子，不强制覆盖公司的或本机已有钩子；先检查已有钩子是否调用 `git lfs pre-push`，再按 `git lfs update --manual` 的说明整合。

## 为已有 GCN 小试验建立环境

从仓库根目录执行，无需激活 PowerShell 虚拟环境，也不依赖 PowerShell 脚本执行权限：

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-pilot.txt
.\.venv\Scripts\python.exe -X utf8 -c "import numpy, PIL; from zoneinfo import ZoneInfo; print(numpy.__version__, PIL.__version__, ZoneInfo('Asia/Shanghai'))"
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s m-GCN模型/room_layout_pilot -p 'test_*.py' -v
```

`requirements-pilot.txt` 对应目前已有的 NumPy/Pillow 小试验，`tzdata` 为 Windows 的时区支持。该试验只需 CPU，不依赖 CUDA 或 PyTorch。此依赖文件不覆盖未来 Rhino、Grasshopper 或其他模型实验的环境。

先做短运行以检查读写和结果输出，再进行完整试验：

```powershell
.\.venv\Scripts\python.exe -X utf8 m-GCN模型/room_layout_pilot/run.py --project-root . --epochs 20 --seeds 7
.\.venv\Scripts\python.exe -X utf8 m-GCN模型/room_layout_pilot/run.py --project-root . --epochs 6000 --seeds 7 19 43
```

每次运行在 `e-实验评估/20261103_09体检区_GCN复原/run_时间戳/` 创建独立结果，包含代码快照、权重、预测、指标、源文件哈希和说明。20 步只用于检查运行链路，不用于论文性能结论。现有实验是 09 号体检区的同图拟合诊断，没有独立测试集。

当前 PNG 绘图仅自动查找 macOS 字体，Windows 的中文可能显示为方框。可用浏览器打开输出 SVG 查看中文，指标和 JSON 仍可核查；Windows PNG 中文字体尚待适配。`-X utf8` 用于避免 Windows 默认编码影响中文 JSON 和说明文件。

## 两台电脑之间交接

开始工作前，先确认上一台电脑的改动已经推送，再在当前电脑执行：

```powershell
git status --short
git pull --ff-only
git lfs pull
```

如果有本地改动，先保存并提交；出现冲突或分叉时停止自动同步，逐项处理。不要用强制推送或丢弃本地改动来代替冲突处理。

结束工作前，关闭 Word 以保存正文和释放临时锁文件，检查本次修改，再提交上传：

```powershell
git status --short
git add --all
git diff --cached --stat
git commit -m "Update thesis and experiment work"
git push origin main
```

检查暂存清单，确认包含应保存的正文、标注、代码及实验结果。默认忽略本地虚拟环境、缓存、Word 锁文件和凭据；临时核对材料作为研究追溯资料保留。不要在两台电脑同时编辑同一 DOCX，Git 无法自动合并 Word 内容。

## 当前验证范围

上传前在 macOS 使用 Python 3.13.13、NumPy 2.4.6、Pillow 12.2.0 检查现有单元测试和短运行，具体结果以本次交付说明为准。尚未在你的 Windows 主机执行安装或运行；在主机完成上述环境检查、单元测试及短运行后，才能确认该主机环境可用。
