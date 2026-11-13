# Windows 主机与多电脑同步

更新日期：2026-11-13。适用仓库：`AndrewHuStudio/thesis-writing`（当日核查为公开；后续以 GitHub 实时状态为准）。本文说明如何将论文、标注及 GCN 实验带到 Windows 主机，不代表整套平面生成系统已经实现。

## 第一次在 Windows 主机使用

安装 Git for Windows、Git LFS、GitHub CLI 和 Python 3.13；论文 DOCX 使用 Word 或兼容的办公软件打开。下列命令在 PowerShell 执行。GitHub 登录时使用有该仓库访问权限的账号（推送还需写权限）；登录通过浏览器完成，不把令牌写入项目文件。

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

### 立即收到这次更新

在 Windows 已克隆的论文仓库根目录打开 PowerShell，保存并关闭 Word，确认当前为 `main` 且 `git status --short` 没有输出，再运行以下命令；任一步报错就先处理该错误。

```powershell
git status --short
git branch --show-current
git pull --ff-only origin main
git lfs pull
git lfs fsck
git rev-parse HEAD
git ls-remote origin refs/heads/main
```

最后两条的提交号应相同。首次拉取也会拿到“多端同步”Skill，位置为 `.agents/skills/multi-device-sync/`，可在项目中请求“使用多端同步”。该位置参照 [OpenAI 官方技能说明](https://learn.chatgpt.com/docs/build-skills)；未发现时重新打开项目。

### 每两分钟检查并接收

完成首次拉取后，在同一个仓库根目录执行：

```powershell
py -3 -X utf8 .agents/skills/multi-device-sync/scripts/receive.py --repo . --watch
```

保持该窗口运行，默认每 120 秒检查一次；Ctrl+C 停止，省略 `--watch` 则只检查并接收一轮。电脑休眠、离线或关闭窗口时无法接收。这不是已安装的开机后台服务，Windows 端仍需执行此命令。

接收器只在 `main`、远端正确、工作区干净且可快进时更新，并下载和校验 LFS。输出 `updated` 表示本轮拿到新版本，`current` 表示本轮版本一致。未提交改动、Office 锁文件（包括被 Git 忽略的锁文件）、本地领先或分叉都会暂停更新，保留本地内容；被忽略的本地文件若与远端新增文件同名，也会阻止合并。LFS 文件仍为占位指针时不报告成功。不会自动提交、推送、stash 或强制覆盖。不要在接收更新时同时编辑同一文件。

`dirty` 时先审阅并提交本地改动，`word_open` 时保存并关闭 Word，`ahead` / `diverged` 时先同步本地提交。`error` 需处理网络、GitHub 登录或 Git LFS，不能当作成功。异常退出遗留的 `.git/multi-device-sync.lock` 只有在确认无接收进程运行后才能移除。

### 日常手工交接

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
