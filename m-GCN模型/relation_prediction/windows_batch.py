"""Run and record the existing 53-plan baseline on a Windows CUDA workstation."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
from zoneinfo import ZoneInfo


def write_json(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device', default='cuda:1')
    parser.add_argument('--epochs', type=int, default=120)
    parser.add_argument('--seeds', nargs='+', type=int, default=[7, 19, 43])
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    stamp = datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y%m%d_%H%M%S_%f')
    output = root / 'e-实验评估/20261114_Windows显卡训练' / f'batch_{stamp}'
    output.mkdir(parents=True, exist_ok=False)
    state = {'status': 'running', 'pid': os.getpid(),
             'device': args.device, 'epochs_per_run': args.epochs,
             'seeds': args.seeds, 'evaluation_scope': 'training_pool_diagnostics',
             'prior_multiplier': 2., 'runs': []}
    write_json(output / 'status.json', state)
    print(f'BATCH_DIRECTORY={output}', flush=True)
    try:
        for seed in args.seeds:
            run_directory = output / f'seed_{seed}'
            command = [sys.executable, '-X', 'utf8', str(Path(__file__).with_name('run.py')),
                       '--project-root', str(root), '--device', args.device,
                       '--epochs', str(args.epochs), '--seed', str(seed),
                       '--prior-multiplier', '2', '--output-dir', str(run_directory)]
            state['current_seed'] = seed
            write_json(output / 'status.json', state)
            with (output / f'seed_{seed}.log').open('w', encoding='utf-8') as log:
                result = subprocess.run(command, cwd=root, stdout=log,
                                        stderr=subprocess.STDOUT, check=False)
            if result.returncode:
                raise RuntimeError(f'Seed {seed} failed; see seed_{seed}.log')
            status = json.loads((run_directory / 'status.json').read_text(encoding='utf-8'))
            verification = json.loads((run_directory / 'verification.json').read_text(encoding='utf-8'))
            if status['status'] != 'complete':
                raise RuntimeError(f'Seed {seed} did not complete')
            state['runs'].append({'seed': seed, 'directory': str(run_directory),
                                  'result': status, 'verification': verification})
            write_json(output / 'status.json', state)
            print(f'COMPLETED seed={seed}', flush=True)
        state['status'] = 'complete'
        state.pop('current_seed', None)
        write_json(output / 'status.json', state)
    except BaseException as error:
        state['status'] = 'failed'
        state['error'] = repr(error)
        write_json(output / 'status.json', state)
        raise


if __name__ == '__main__':
    main()
