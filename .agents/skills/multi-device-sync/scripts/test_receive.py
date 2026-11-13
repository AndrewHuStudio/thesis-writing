"""Exercise the receiver against real local Git repositories; no GitHub writes."""
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).with_name('receive.py')


class ReceiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        config = root / 'empty-gitconfig'
        config.write_text('', encoding='utf-8')
        isolated_config = patch.dict(os.environ, {
            'GIT_CONFIG_GLOBAL': str(config), 'GIT_CONFIG_NOSYSTEM': '1'})
        isolated_config.start()
        self.addCleanup(isolated_config.stop)
        self.remote = root / 'remote.git'
        self.source = root / 'Mac 论文'
        self.target = root / 'Windows 论文'
        self.git(root, 'init', '--bare', '--initial-branch=main', str(self.remote))
        self.git(root, 'clone', str(self.remote), str(self.source))
        self.configure(self.source)
        self.commit(self.source, 'paper.md', 'initial')
        self.git(self.source, 'push', '-u', 'origin', 'main')
        self.git(root, 'clone', str(self.remote), str(self.target))
        self.configure(self.target)

    def git(self, repo, *args):
        result = subprocess.run(['git', '-C', str(repo), *args], text=True,
                                encoding='utf-8', capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def configure(self, repo):
        self.git(repo, 'config', 'user.email', 'sync-test@example.invalid')
        self.git(repo, 'config', 'user.name', 'Sync Test')
        # Keep tests independent of the workstation's global push hooks.
        hooks = repo / '.git' / 'sync-test-hooks'
        hooks.mkdir()
        self.git(repo, 'config', 'core.hooksPath', str(hooks))

    def commit(self, repo, filename, content):
        (repo / filename).write_text(content, encoding='utf-8')
        self.git(repo, 'add', filename)
        self.git(repo, 'commit', '-m', content)

    def publish(self):
        self.commit(self.source, 'paper.md', 'updated')
        self.git(self.source, 'push', 'origin', 'main')

    def receive(self, **kwargs):
        self.assertTrue(SCRIPT.is_file(), 'receiver implementation is missing')
        spec = importlib.util.spec_from_file_location('sync_receive', SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.sync_once(self.target, str(self.remote), **kwargs)

    def test_fast_forward_downloads_published_files(self):
        self.publish()
        result = self.receive()
        self.assertEqual(result['status'], 'updated')
        self.assertEqual((self.target / 'paper.md').read_text(), 'updated')
        self.assertEqual(self.git(self.target, 'rev-parse', 'HEAD'),
                         self.git(self.source, 'rev-parse', 'HEAD'))

    def test_current_repository_is_verified(self):
        self.assertEqual(self.receive()['status'], 'current')

    def test_unsaved_tracked_change_is_preserved(self):
        self.publish()
        (self.target / 'paper.md').write_text('Windows changes')
        self.assertEqual(self.receive()['status'], 'dirty')
        self.assertEqual((self.target / 'paper.md').read_text(), 'Windows changes')

    def test_untracked_word_lock_pauses_receiving(self):
        (self.target / '~$thesis.docx').write_text('lock')
        self.assertEqual(self.receive()['status'], 'dirty')

    def test_ignored_word_lock_also_pauses_receiving(self):
        self.commit(self.source, '.gitignore', '~$*\n')
        self.git(self.source, 'push', 'origin', 'main')
        self.git(self.target, 'pull', '--ff-only')
        (self.target / '~$thesis.docx').write_text('lock')
        self.publish()
        self.assertEqual(self.receive()['status'], 'word_open')
        self.assertEqual((self.target / 'paper.md').read_text(), 'initial')

    def test_local_commit_is_not_pushed(self):
        self.commit(self.target, 'windows.md', 'Windows work')
        self.assertEqual(self.receive()['status'], 'ahead')
        self.assertNotEqual(self.git(self.target, 'rev-parse', 'HEAD'),
                            self.git(self.source, 'rev-parse', 'HEAD'))

    def test_diverged_history_is_not_merged(self):
        self.commit(self.target, 'windows.md', 'Windows work')
        before = self.git(self.target, 'rev-parse', 'HEAD')
        self.publish()
        self.assertEqual(self.receive()['status'], 'diverged')
        self.assertEqual(self.git(self.target, 'rev-parse', 'HEAD'), before)

    def test_other_branch_is_not_changed(self):
        self.git(self.target, 'switch', '-c', 'draft')
        self.publish()
        self.assertEqual(self.receive()['status'], 'wrong_branch')
        self.assertEqual(self.git(self.target, 'branch', '--show-current'), 'draft')

    def test_wrong_remote_is_not_contacted(self):
        self.git(self.target, 'remote', 'set-url', 'origin', '/missing/other.git')
        self.assertEqual(self.receive()['status'], 'wrong_remote')

    def test_ignored_local_file_is_not_overwritten_by_new_remote_file(self):
        (self.target / '.git' / 'info' / 'exclude').write_text('draft.docx\n')
        (self.target / 'draft.docx').write_text('unsaved Windows draft')
        before = self.git(self.target, 'rev-parse', 'HEAD')
        self.commit(self.source, 'draft.docx', 'remote draft')
        self.git(self.source, 'push', 'origin', 'main')
        self.assertEqual(self.receive()['status'], 'error')
        self.assertEqual((self.target / 'draft.docx').read_text(),
                         'unsaved Windows draft')
        self.assertEqual(self.git(self.target, 'rev-parse', 'HEAD'), before)

    def test_concurrent_receiver_is_skipped(self):
        (self.target / '.git' / 'multi-device-sync.lock').write_text('other process')
        self.assertEqual(self.receive()['status'], 'locked')

    def test_repository_subdirectory_is_rejected(self):
        self.assertTrue(SCRIPT.is_file(), 'receiver implementation is missing')
        spec = importlib.util.spec_from_file_location('sync_receive', SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        nested = self.target / 'nested'
        nested.mkdir()
        self.assertEqual(module.sync_once(nested, str(self.remote))['status'],
                         'wrong_root')

    def test_lfs_object_is_downloaded_and_verified(self):
        self.git(self.source, 'lfs', 'install', '--local')
        self.git(self.target, 'lfs', 'install', '--local')
        self.git(self.source, 'lfs', 'track', '*.bin')
        self.git(self.source, 'add', '.gitattributes')
        self.commit(self.source, 'weights.bin', 'model weights')
        self.git(self.source, 'push', 'origin', 'main')
        self.assertEqual(self.receive()['status'], 'updated')
        self.assertEqual((self.target / 'weights.bin').read_text(), 'model weights')
        self.git(self.target, 'lfs', 'fsck')

    def test_missing_lfs_filter_does_not_report_pointer_as_success(self):
        self.git(self.source, 'lfs', 'install', '--local')
        self.git(self.source, 'lfs', 'track', '*.bin')
        self.git(self.source, 'add', '.gitattributes')
        self.commit(self.source, 'weights.bin', 'model weights')
        self.git(self.source, 'push', 'origin', 'main')
        self.assertEqual(self.receive()['status'], 'error')


if __name__ == '__main__':
    unittest.main()
