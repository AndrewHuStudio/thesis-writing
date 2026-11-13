"""Train an exploratory access-relation model on the existing 53 plans."""
import argparse
from copy import deepcopy
from datetime import datetime
import json
import math
from pathlib import Path
import platform
import shutil
import time
from zoneinfo import ZoneInfo

import numpy as np
import torch

from data import fingerprints, load_dataset, sample_training_pairs
from metrics import diagnostics
from model import SpaceRelationGCN, assumed_prior, graph_loss, load_checkpoint
from report import save_predictions, write_json, write_report


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--epochs', type=int, default=120)
    parser.add_argument('--seed', type=int, default=7)
    parser.add_argument('--hidden', type=int, default=32)
    parser.add_argument('--learning-rate', type=float, default=.003)
    parser.add_argument('--prior-multiplier', type=float, default=2.)
    parser.add_argument('--population-pairs', type=int, default=1024)
    parser.add_argument('--batch-graphs', type=int, default=8)
    parser.add_argument('--threads', type=int, default=2)
    parser.add_argument('--expected-plans', type=int, default=53)
    args = parser.parse_args()
    positive = [args.epochs, args.hidden, args.learning_rate, args.prior_multiplier,
                args.population_pairs, args.batch_graphs, args.threads, args.expected_plans]
    if any(value <= 0 for value in positive):
        parser.error('Training counts and hyperparameters must be positive')
    return args


def train(model, samples, args, output):
    generator = torch.Generator().manual_seed(args.seed + 1)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=1e-4)
    initial, _, _ = diagnostics(model, samples, args.prior_multiplier)
    history = [{'epoch': 0, **initial}]
    best_risk = initial['macro_pu_risk_plus_known_negatives']
    best_state, best_epoch = deepcopy(model.state_dict()), 0
    started = time.monotonic()
    write_json(output / 'history.json', history)
    print(json.dumps(history[0]), flush=True)
    with (output / 'progress.jsonl').open('w') as progress:
        for epoch in range(1, args.epochs + 1):
            model.train()
            order = torch.randperm(len(samples), generator=generator).tolist()
            total_loss = 0.
            for start in range(0, len(order), args.batch_graphs):
                indexes = order[start:start + args.batch_graphs]
                optimizer.zero_grad(set_to_none=True)
                losses = []
                for index in indexes:
                    sample = samples[index]
                    pairs = sample_training_pairs(sample, generator, args.population_pairs)
                    losses.append(graph_loss(model, sample, pairs, args.prior_multiplier))
                loss = torch.stack(losses).mean()
                if not torch.isfinite(loss):
                    raise FloatingPointError(f'Non-finite training loss at epoch {epoch}')
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5., error_if_nonfinite=True)
                optimizer.step()
                total_loss += float(loss.detach()) * len(indexes)
            row = {'epoch': epoch, 'sampled_macro_training_loss': total_loss / len(samples),
                   'elapsed_seconds': time.monotonic() - started}
            if epoch % 10 == 0 or epoch == args.epochs:
                exact, _, _ = diagnostics(model, samples, args.prior_multiplier)
                history.append({'epoch': epoch, **exact})
                row.update(exact)
                risk = exact['macro_pu_risk_plus_known_negatives']
                if risk < best_risk:
                    best_risk, best_epoch = risk, epoch
                    best_state = deepcopy(model.state_dict())
                write_json(output / 'history.json', history)
                print(json.dumps(row), flush=True)
            progress.write(json.dumps(row, allow_nan=False) + '\n')
            progress.flush()
    model.load_state_dict(best_state)
    return initial, history, best_epoch


def execute(args, output):
    root = args.project_root.resolve()
    data_dir = root / 'p-平面标注与数据处理/训练数据/单层医院_v1'
    samples, input_paths, vocabulary = load_dataset(data_dir)
    if len(samples) != args.expected_plans:
        raise ValueError(f'Expected {args.expected_plans} plans, found {len(samples)}')
    if any(not len(sample['positive_pairs']) for sample in samples):
        raise ValueError('Each training plan needs an observed access positive')
    source_dir = root / 'p-平面标注与数据处理/标注试样'
    source_paths = [p for p in source_dir.rglob('*') if p.is_file() and p.name != '.DS_Store']
    if not source_paths:
        raise ValueError('Source-deliverable directory is empty')
    input_hashes = fingerprints(input_paths, root)
    source_hashes = fingerprints(source_paths, root)
    write_json(output / 'input_hashes.json', input_hashes)
    write_json(output / 'source_hashes.json', source_hashes)
    configuration = {
        'created_at': datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
        'project_root': str(root), 'data_directory': str(data_dir),
        'seed': args.seed, 'epochs': args.epochs, 'hidden': args.hidden,
        'learning_rate': args.learning_rate, 'prior_multiplier': args.prior_multiplier,
        'population_pairs_per_plan_per_epoch': args.population_pairs,
        'batch_graphs': args.batch_graphs, 'threads': args.threads,
        'optimizer': 'AdamW', 'weight_decay': 1e-4, 'device': 'cpu',
        'python': platform.python_version(), 'platform': platform.platform(),
        'torch': str(torch.__version__), 'numpy': np.__version__,
        'feature_order': vocabulary['node_feature_order'],
        'input_graph': 'complete_inventory_normalized_mean_with_residual_node_projection',
        'target': 'undirected_access_candidate_score',
        'supervision': 'non_negative_PU_plus_confirmed_negative_logistic_loss',
        'prior_assumption': 'min(0.5, multiplier * observed_positive_pair_fraction_per_plan)',
        'positive_sampling_representativeness_verified': False,
        'split': 'all_53_train', 'held_out_evaluation': None,
        'checkpoint_selection': 'lowest_exact_training_macro_risk_every_10_epochs',
        'geometry_used_by_model': False, 'node_ids_used_by_model': False,
        'scores_calibrated': False,
    }
    write_json(output / 'config.json', configuration)
    snapshot = output / 'code_snapshot'
    snapshot.mkdir()
    for path in Path(__file__).parent.glob('*.py'):
        shutil.copy2(path, snapshot / path.name)
    model = SpaceRelationGCN(50, args.hidden)
    mean_prior = np.mean([assumed_prior(sample, args.prior_multiplier) for sample in samples])
    torch.nn.init.constant_(model.decoder[-1].bias, math.log(mean_prior / (1 - mean_prior)))
    initial, history, best_epoch = train(model, samples, args, output)
    temporary = output / 'weights.pt.tmp'
    torch.save({'state_dict': model.state_dict(), 'model_specification': model.specification(),
                'configuration': configuration, 'best_epoch': best_epoch}, temporary)
    temporary.replace(output / 'weights.pt')
    final, rows, predictions = diagnostics(model, samples, args.prior_multiplier)
    reloaded, _ = load_checkpoint(output / 'weights.pt')
    reloaded_metrics, _, reloaded_predictions = diagnostics(reloaded, samples, args.prior_multiplier)
    maximum_difference = max(float(np.abs(left - right).max())
                             for left, right in zip(predictions, reloaded_predictions))
    checks = {
        'checkpoint_reload_max_absolute_score_difference': maximum_difference,
        'checkpoint_reload_metrics_identical': final == reloaded_metrics,
        'input_files_checked': len(input_paths),
        'input_files_unchanged': input_hashes == fingerprints(input_paths, root),
        'source_files_checked': len(source_paths),
        'source_files_unchanged': source_hashes == fingerprints(source_paths, root),
        'all_plans_used_each_epoch': len(samples),
        'code_file_line_counts': {p.name: len(p.read_text().splitlines())
                                  for p in snapshot.glob('*.py')},
        'split': 'all_53_train', 'held_out_evaluation': None,
    }
    if (maximum_difference != 0 or not checks['checkpoint_reload_metrics_identical']
            or not checks['input_files_unchanged'] or not checks['source_files_unchanged']):
        raise RuntimeError(f'Run verification failed: {checks}')
    save_predictions(output, samples, rows, predictions)
    write_report(output, configuration, initial, final, best_epoch, rows, history, checks)
    write_json(output / 'status.json', {'status': 'complete', 'best_epoch': best_epoch,
                                      'epochs_completed': args.epochs, 'metrics': final})
    print(json.dumps({'output_directory': str(output), 'best_epoch': best_epoch,
                      'final': final, 'verification': checks}, ensure_ascii=False), flush=True)


def main():
    args = arguments()
    torch.set_num_threads(args.threads)
    torch.manual_seed(args.seed)
    torch.use_deterministic_algorithms(True)
    stamp = datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y%m%d_%H%M%S_%f')
    output = args.project_root.resolve() / 'e-实验评估/20261113_53图_GCN关系预测' / f'run_{stamp}'
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / 'status.json', {'status': 'running'})
    print(f'OUTPUT_DIRECTORY={output}', flush=True)
    try:
        execute(args, output)
    except BaseException as error:
        write_json(output / 'status.json', {'status': 'failed', 'error': repr(error)})
        raise


if __name__ == '__main__':
    main()
