"""Receive a clean main branch from the intended origin, once or every 120s."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time


DEFAULT_REMOTE = 'https://github.com/AndrewHuStudio/thesis-writing.git'


def git(repo, *args):
    env = dict(os.environ, GIT_TERMINAL_PROMPT='0', GCM_INTERACTIVE='Never')
    env.setdefault('GIT_SSH_COMMAND', 'ssh -oBatchMode=yes')
    result = subprocess.run(['git', '-C', str(repo), *args], env=env,
                            capture_output=True, text=True, encoding='utf-8',
                            errors='replace', timeout=60)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip()
                           or f'git {args[0]} exited {result.returncode}')
    return result.stdout.strip()


def remote_key(url):
    return url.replace('git@github.com:', 'https://github.com/').rstrip('/').removesuffix('.git')


def git_path(repo, name):
    path = Path(git(repo, 'rev-parse', '--git-path', name))
    return path if path.is_absolute() else repo / path


def working_state(repo):
    if git(repo, 'status', '--porcelain', '--untracked-files=all'):
        return {'status': 'dirty', 'message': '先保存、审阅并提交本地改动；本轮未更新。'}
    locks = git(repo, 'ls-files', '--others', '--ignored', '--exclude-standard',
                '--', ':(glob)**/~$*')
    if locks:
        return {'status': 'word_open', 'message': '检测到 Office 锁文件，请保存并关闭 Word 后重试。'}
    for name in ('MERGE_HEAD', 'CHERRY_PICK_HEAD', 'REVERT_HEAD',
                 'rebase-merge', 'rebase-apply', 'index.lock'):
        if git_path(repo, name).exists():
            return {'status': 'busy', 'message': 'Git 正在执行其他操作；本轮未更新。'}
    if git(repo, 'branch', '--show-current') != 'main':
        return {'status': 'wrong_branch', 'message': '当前不是 main；本轮未更新。'}
    return None


def receive_locked(repo, expected_remote):
    if remote_key(git(repo, 'remote', 'get-url', 'origin')) != remote_key(expected_remote):
        return {'status': 'wrong_remote', 'message': 'origin 与指定仓库不符；本轮未联网。'}
    state = working_state(repo)
    if state:
        return state
    git(repo, 'lfs', 'version')
    git(repo, 'fetch', 'origin', 'refs/heads/main:refs/remotes/origin/main')
    state = working_state(repo)
    if state:
        return state
    remote = git(repo, 'rev-parse', 'origin/main')
    ahead, behind = map(int, git(repo, 'rev-list', '--left-right', '--count',
                                 f'HEAD...{remote}').split())
    if ahead:
        status = 'diverged' if behind else 'ahead'
        return {'status': status, 'ahead': ahead, 'behind': behind,
                'message': '存在本地提交；请审阅并同步，本轮未合并也未推送。'}
    if behind:
        git(repo, 'merge', '--ff-only', '--no-autostash', '--no-overwrite-ignore',
            '--no-edit', remote)
    git(repo, 'lfs', 'pull', 'origin')
    git(repo, 'lfs', 'fsck')
    pointers = [line for line in git(repo, 'lfs', 'ls-files', '--long').splitlines()
                if line[64:67] == ' - ']
    if pointers:
        return {'status': 'error', 'message': 'LFS 文件仍为占位指针；请检查 git lfs install 和下载设置，妥善整合已有 hook 后重试。'}
    state = working_state(repo)
    if state:
        return state
    head = git(repo, 'rev-parse', 'HEAD')
    if head != remote:
        return {'status': 'changed_during_sync', 'message': '同步中版本发生变化，请重新检查。'}
    return {'status': 'updated' if behind else 'current', 'head': head,
            'message': '已接收本轮远端版本，Git LFS 校验通过。'}


def sync_once(repo, expected_remote=DEFAULT_REMOTE):
    repo = Path(repo).resolve()
    lock = None
    try:
        root = Path(git(repo, 'rev-parse', '--show-toplevel')).resolve()
        if root != repo:
            return {'status': 'wrong_root', 'message': '--repo 必须指向仓库根目录。'}
        candidate = git_path(repo, 'multi-device-sync.lock')
        try:
            with candidate.open('x', encoding='utf-8') as handle:
                handle.write(str(os.getpid()))
            lock = candidate
        except FileExistsError:
            return {'status': 'locked', 'message': '另一个接收进程正在运行；本轮跳过。'}
        return receive_locked(repo, expected_remote)
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        return {'status': 'error', 'message': str(error)[:1500]}
    finally:
        if lock is not None:
            lock.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path.cwd())
    parser.add_argument('--expected-remote', default=DEFAULT_REMOTE)
    parser.add_argument('--watch', action='store_true')
    parser.add_argument('--interval', type=int, default=120)
    args = parser.parse_args()
    if args.interval < 30:
        parser.error('--interval must be at least 30 seconds')
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    while True:
        result = sync_once(args.repo, args.expected_remote)
        result['checked_at'] = datetime.now(timezone.utc).isoformat()
        print(json.dumps(result, ensure_ascii=False), flush=True)
        if not args.watch:
            return 0 if result['status'] in {'updated', 'current'} else 1
        time.sleep(args.interval)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(0)
