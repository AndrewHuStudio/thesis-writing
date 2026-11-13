---
name: multi-device-sync
description: Use when the user asks for 多端同步, GitHub progress sync, or Mac and Windows handoff of this thesis repository, including receiving updates and checking whether a push or pull actually completed.
---

# 多端同步

将当前电脑的论文进度提交到 GitHub，并让另一台电脑安全接收。默认项目为本仓库，远端 `AndrewHuStudio/thesis-writing`、分支 `main`；实际执行前核对，其他项目以用户指定范围为准。

## 本机提交与推送

1. 确认 Git 根目录、`AGENTS.md`、当前分支、`git status --short`、远端 URL 和 LFS。不要从父目录上传其他项目。代码文件最多 599 行。
2. 使用 GitHub MCP 或 `gh repo view --json visibility,url` 实查可见性；不能沿用旧文档的“私有”。用户已授权的现有同步直接执行；可见性与已知授权不符时再澄清，不因每次公开状态重复索要许可。
3. `git fetch origin main`，检查 `git rev-list --left-right --count HEAD...origin/main`。远端有新提交时先审阅；有本地改动或分叉时保留文件，妥善整合再推送。
4. 审阅新增、修改、删除与体积，按已核实的项目路径暂存。论文正文、标注、核对证据、实验结果和权重属于研究成果；不得为同步顺便清空 `临时核对`。凭据、环境、缓存不上传。大文件按实际大小与仓库规则使用 LFS，已有 hook 不覆盖。
5. 根据变更运行适当检查，检查暂存清单及 `git diff --cached --check`，提交有意义的中文说明后普通推送。不要强推、自动丢弃、自动 stash 或跳过 hook。
6. 用 `git ls-remote origin refs/heads/main` 验证远端 SHA 与本地 HEAD，重新 fetch 后确认差异为 `0 0`，运行 `git lfs fsck` 并检查工作区。提交成功不等于推送成功。

## Windows 接收

首次克隆、环境和手工交接见仓库 [`docs/Windows主机与多电脑同步.md`](../../../docs/Windows主机与多电脑同步.md)。已克隆时，先关闭并保存 Word，检查当前分支为 main、工作区干净，再 `git pull --ff-only origin main`、`git lfs pull`。

需要及时接收时，在 Windows 仓库根目录的 PowerShell 运行：

```powershell
py -3 -X utf8 .agents/skills/multi-device-sync/scripts/receive.py --repo . --watch
```

默认每 120 秒检查一次，保持窗口运行；Ctrl+C 停止。只运行一轮时省略 `--watch`。依赖 Git、Git LFS、Python 3.10+，首次登录在交互终端完成。脚本只接收，不自动提交或推送。

| 状态 | 实际处理 |
| --- | --- |
| `updated` / `current` | 本轮远端提交与 HEAD 一致且 LFS 校验通过 |
| `dirty` / `word_open` | 保留本地内容；保存、审阅、提交或关闭 Word 后重试 |
| `ahead` / `diverged` | 保留本地提交；人工审阅后同步，接收器不自动合并 |
| `wrong_branch` / `wrong_remote` / `wrong_root` | 校对路径、分支、远端后重试 |
| `busy` / `locked` | 等待其他 Git/接收进程；崩溃遗留锁须确认进程已退出再移除 |
| `error` | 查看错误，处理网络、登录或 LFS，下一轮重试；不能报告接收成功 |

脚本会复查状态并仅快进更新；被忽略的同名本地文件会阻止合并，LFS 文件仍为占位指针时不报告成功。接收运行期间仍应避免同时编辑同一文件。忽略规则中的 Office 锁文件也会触发暂停。休眠、离线、窗口关闭时无法及时接收；没有配置开机任务。

## 技能分发与验收

此 Skill 保存在仓库 `.agents/skills/multi-device-sync/`，随 Git 一起分发；Windows 第一次需手工 pull 获得它。项目技能位置依据 [OpenAI 官方说明](https://learn.chatgpt.com/docs/build-skills)。若当前客户端未发现，重新打开项目或按客户端支持方式安装，不假定另一台电脑自动加载了技能。

验证脚本：`python -m unittest discover -s .agents/skills/multi-device-sync/scripts -p 'test_*.py' -v`。验收两端时分别检查 HEAD 与实时远端 SHA、LFS、工作区。无法连接 Windows 时只报告“GitHub 已更新，Windows 待执行/待验收”，不要宣称两端均已完成。

最终回复包含：仓库链接、提交号、同步范围、检查结果、Windows 下一条命令，以及本次工具/MCP/Skill、直接效果和下一步。若反馈 VS Code 图谱没变化，核对并刷新实际界面后再报告界面结果。
