"""Compare source-grouped frequency, MLP and GCN with validation-selected weights."""
import argparse
from copy import deepcopy
from datetime import datetime
import json
import math
import os
from pathlib import Path
import platform
import shutil
import time
from zoneinfo import ZoneInfo

os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
import numpy as np
import torch

from benchmark_groups import audit_digest, partitions, source_audit, write_json
from benchmark_metrics import aggregate, evaluate, sample_metrics
from benchmark_models import ObservedDensity, build_model
from data import fingerprints, load_dataset, sample_training_pairs
from model import assumed_prior, graph_loss


ROOT = Path(__file__).resolve().parents[2]


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', type=Path, default=ROOT)
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--device', default='cuda:1')
    parser.add_argument('--seeds', type=int, nargs='+', default=[7, 19, 43])
    parser.add_argument('--folds', type=int, default=5)
    parser.add_argument('--test-folds', type=int, nargs='+')
    parser.add_argument('--epochs', type=int, default=120)
    parser.add_argument('--hidden', type=int, default=32)
    parser.add_argument('--learning-rate', type=float, default=.003)
    parser.add_argument('--prior-multiplier', type=float, default=2.)
    parser.add_argument('--population-pairs', type=int, default=1024)
    parser.add_argument('--batch-graphs', type=int, default=8)
    parser.add_argument('--patience-checks', type=int, default=6)
    parser.add_argument('--models', nargs='+', choices=['mlp', 'gcn'], default=['mlp', 'gcn'])
    args = parser.parse_args()
    positive = [args.epochs, args.hidden, args.learning_rate, args.prior_multiplier,
                args.population_pairs, args.batch_graphs, args.patience_checks]
    if any(value <= 0 for value in positive) or args.folds < 3:
        parser.error('Counts and hyperparameters must be positive, with at least three folds')
    for name in ('seeds', 'models', 'test_folds'):
        values = getattr(args, name)
        if values is not None and len(values) != len(set(values)):
            parser.error(f'Duplicate values in {name}')
    if args.test_folds is not None and any(not 0 <= i < args.folds for i in args.test_folds):
        parser.error('Test fold is outside fold range')
    return args


def fit_neural(kind, samples, group_ids, seed, fold, args, output):
    torch.manual_seed(seed)
    model = build_model(kind, args.hidden).to(args.device)
    prior = float(np.mean([assumed_prior(s, args.prior_multiplier) for s in samples['train']]))
    torch.nn.init.constant_(model.decoder[-1].bias, math.log(prior / (1 - prior)))
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=1e-4)
    generator = torch.Generator().manual_seed(seed + 1 + fold * 1000)
    validation, _, _ = evaluate(model, samples['validation'], group_ids)
    metric_name = 'group_macro_recall_at_n'
    best_value = validation[metric_name]
    best_state, best_epoch, stale = deepcopy(model.state_dict()), 0, 0
    history = [{'epoch': 0, 'validation': validation}]
    started = time.monotonic()
    completed_epoch = 0
    for epoch in range(1, args.epochs + 1):
        model.train()
        order = torch.randperm(len(samples['train']), generator=generator).tolist()
        total = 0.
        for start in range(0, len(order), args.batch_graphs):
            indexes = order[start:start + args.batch_graphs]
            optimizer.zero_grad(set_to_none=True)
            losses = []
            for index in indexes:
                sample = samples['train'][index]
                pairs = sample_training_pairs(sample, generator, args.population_pairs)
                losses.append(graph_loss(model, sample, pairs, args.prior_multiplier))
            loss = torch.stack(losses).mean()
            if not torch.isfinite(loss):
                raise FloatingPointError(f'Nonfinite {kind} loss at epoch {epoch}')
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5., error_if_nonfinite=True)
            optimizer.step()
            total += float(loss.detach()) * len(indexes)
        completed_epoch = epoch
        if epoch % 10 == 0 or epoch == args.epochs:
            validation, _, _ = evaluate(model, samples['validation'], group_ids)
            value = validation[metric_name]
            history.append({'epoch': epoch, 'training_loss': total / len(order),
                            'validation': validation,
                            'elapsed_seconds': time.monotonic() - started})
            if value > best_value:
                best_value, best_epoch, stale = value, epoch, 0
                best_state = deepcopy(model.state_dict())
            else:
                stale += 1
            write_json(output / 'history.json', history)
            if epoch >= 40 and stale >= args.patience_checks:
                break
    model.load_state_dict(best_state)
    checkpoint = {'state_dict': model.state_dict(), 'model_kind': kind,
                  'model_specification': model.specification(), 'best_epoch': best_epoch,
                  'seed': seed, 'test_fold': fold,
                  'selection_metric': 'validation_' + metric_name,
                  'configuration': {'learning_rate': args.learning_rate,
                                    'prior_multiplier': args.prior_multiplier,
                                    'population_pairs': args.population_pairs,
                                    'batch_graphs': args.batch_graphs,
                                    'weight_decay': 1e-4},
                  'partitions': {role: [s['plan_id'] for s in rows]
                                 for role, rows in samples.items()}}
    temporary = output / 'weights.pt.tmp'
    torch.save(checkpoint, temporary)
    temporary.replace(output / 'weights.pt')
    summary, rows, scores = evaluate(model, samples['test'], group_ids, keep_scores=True)
    loaded = torch.load(output / 'weights.pt', map_location='cpu', weights_only=True)
    restored = build_model(loaded['model_kind'], loaded['model_specification']['hidden']).to(args.device)
    restored.load_state_dict(loaded['state_dict'])
    reloaded_summary, _, reloaded_scores = evaluate(restored, samples['test'], group_ids, True)
    maximum_difference = max(float(np.max(np.abs(scores[p] - reloaded_scores[p]))) for p in scores)
    if summary != reloaded_summary or maximum_difference != 0:
        raise RuntimeError('Saved checkpoint does not reproduce held-out scores')
    for sample in samples['test']:
        np.savez_compressed(output / (sample['plan_id'] + '.npz'),
                            scores=scores[sample['plan_id']],
                            node_ids=np.asarray(sample['node_ids']),
                            pairs=sample['all_pairs'].numpy(), labels=sample['pair_labels'])
    result = {'model': kind, 'seed': seed, 'test_fold': fold, 'best_epoch': best_epoch,
              'epochs_completed': completed_epoch, 'selection_metric': 'validation_' + metric_name,
              'best_validation_value': best_value, 'elapsed_seconds': time.monotonic() - started,
              'checkpoint_reload_max_score_difference': maximum_difference,
              'partitions': checkpoint['partitions'], 'test_summary': summary, 'test_rows': rows}
    write_json(output / 'result.json', result)
    return result


def summarize(results, expected_plans):
    grouped = {}
    for result in results:
        key = (result['model'], result['seed'])
        grouped.setdefault(key, []).extend(result['test_rows'])
    per_seed = []
    for (kind, seed), rows in grouped.items():
        plans = [row['plan_id'] for row in rows]
        if len(plans) != len(set(plans)):
            raise ValueError('Test plan appears in multiple folds for one model and seed')
        per_seed.append({'model': kind, 'seed': seed, 'all_plans_evaluated_once': len(plans) == expected_plans,
                         'summary': aggregate(rows)})
    comparisons = []
    for kind in sorted({row['model'] for row in per_seed}):
        seeds = [row for row in per_seed if row['model'] == kind]
        metrics = {}
        for key in seeds[0]['summary']:
            if key.startswith(('plan_macro_', 'group_macro_')):
                values = [row['summary'][key] for row in seeds]
                metrics[key] = {'mean': float(np.mean(values)),
                                'seed_standard_deviation': float(np.std(values, ddof=1)) if len(values) > 1 else None}
        comparisons.append({'model': kind, 'seed_count': len(seeds), 'metrics': metrics})
    return {'per_seed': per_seed, 'comparisons': comparisons}


def execute(args, output):
    root = args.project_root.resolve()
    directory = root / 'p-平面标注与数据处理/训练数据/单层医院_v1'
    samples, input_paths, _ = load_dataset(directory)
    hashes = fingerprints(input_paths, root)
    audit = source_audit(directory, samples, args.folds)
    group_ids = {row['plan_id']: row['group_id'] for row in audit['plans']}
    write_json(output / 'source_audit.json', audit)
    write_json(output / 'input_hashes.json', hashes)
    configuration = {key: str(value) if isinstance(value, Path) else value
                     for key, value in vars(args).items()}
    configuration.update({'created_at': datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
                          'source_audit_sha256': audit_digest(audit), 'torch': str(torch.__version__),
                          'numpy': np.__version__, 'python': platform.python_version(),
                          'primary_metric': 'group_macro_observed_positive_recall_at_n_candidates',
                          'checkpoint_selection': 'validation_group_macro_recall_at_n',
                          'input_features': 'existing_50_columns_only',
                          'user_inference_conditions': ['building_boundary', 'space_program'],
                          'evaluation_status': 'exploratory_provisional_source_groups',
                          'unknown_pair_policy': 'unlabeled_in_PU_training_and_evaluation',
                          'heldout_predictions_use_test_labels': False,
                          'observed_budget_metric_is_diagnostic_only': True,
                          'boundary_used_by_current_comparison_models': False,
                          'hyperparameter_search': False})
    write_json(output / 'config.json', configuration)
    snapshot = output / 'code_snapshot'
    snapshot.mkdir()
    for path in Path(__file__).parent.glob('*.py'):
        shutil.copy2(path, snapshot / path.name)
    results = []
    test_folds = args.test_folds if args.test_folds is not None else list(range(args.folds))
    for fold in test_folds:
        split = partitions(samples, audit, fold)
        density = ObservedDensity().fit(split['train'])
        rows = [sample_metrics(s, density.predict(s), group_ids[s['plan_id']]) for s in split['test']]
        frequency = {'model': 'frequency', 'seed': None, 'test_fold': fold,
                     'partitions': {role: [s['plan_id'] for s in rows] for role, rows in split.items()},
                     'test_summary': aggregate(rows), 'test_rows': rows}
        write_json(output / f'fold_{fold}_frequency.json', frequency)
        results.append(frequency)
        for seed in args.seeds:
            for kind in args.models:
                name = f'fold_{fold}_{kind}_seed_{seed}'
                run_output = output / name
                run_output.mkdir()
                write_json(output / 'status.json', {'status': 'running', 'current_run': name,
                                                   'completed_neural_runs': sum(r['model'] != 'frequency' for r in results)})
                result = fit_neural(kind, split, group_ids, seed, fold, args, run_output)
                results.append(result)
                print(json.dumps({'run': name, 'best_epoch': result['best_epoch'],
                                  'test_group_recall_at_n': result['test_summary']['group_macro_recall_at_n']},
                                 ensure_ascii=False), flush=True)
                write_json(output / 'summary.json', summarize(results, len(samples)))
    if hashes != fingerprints(input_paths, root):
        raise RuntimeError('Input data changed during grouped evaluation')
    summary = summarize(results, len(samples))
    summary.update({'evaluation_status': 'exploratory_provisional_source_groups',
                    'input_files_unchanged': True, 'input_files_checked': len(input_paths),
                    'run_count': len(results), 'source_group_count': len(audit['groups']),
                    'test_folds': test_folds,
                    'metric_scope': 'recall_of_observed_positives_with_unknown_pairs_unlabeled'})
    write_json(output / 'summary.json', summary)
    write_json(output / 'status.json', {'status': 'complete', 'neural_runs': len(args.seeds) * len(args.models) * len(test_folds),
                                       'frequency_folds': len(test_folds),
                                       'evaluation_status': summary['evaluation_status']})


def main():
    args = arguments()
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    device = torch.device(args.device)
    if device.type == 'cuda':
        torch.cuda.set_device(device)
    stamp = datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y%m%d_%H%M%S_%f')
    output = args.output_dir or (args.project_root / 'e-实验评估/20261116_关系模型分组对照' / f'run_{stamp}')
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    print('OUTPUT_DIRECTORY=' + str(output), flush=True)
    write_json(output / 'status.json', {'status': 'running'})
    try:
        execute(args, output)
    except BaseException as error:
        write_json(output / 'status.json', {'status': 'failed', 'error': repr(error)})
        raise


if __name__ == '__main__':
    main()
