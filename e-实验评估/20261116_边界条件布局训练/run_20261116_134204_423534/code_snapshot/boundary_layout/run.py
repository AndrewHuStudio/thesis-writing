"""Train and evaluate a boundary-plus-program layout baseline by held-out source."""
import argparse
from copy import deepcopy
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import sys
import time
from zoneinfo import ZoneInfo

os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from boundary_layout.data import load_layouts, move_sample, ProgramMeanBaseline
from boundary_layout.evaluation import aggregate, score_layout, summarize
from boundary_layout.loss import generate, objective
from boundary_layout.model import BoundaryLayoutModel, spatial_slots
from relation_prediction.benchmark_groups import partitions, write_json
from relation_prediction.data import fingerprints
from room_layout_pilot.evaluate import boxes


ROOT = Path(__file__).resolve().parents[2]


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', type=Path, default=ROOT)
    parser.add_argument('--source-audit', type=Path)
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--device', default='cuda:1')
    parser.add_argument('--seeds', type=int, nargs='+', default=[7, 19, 43])
    parser.add_argument('--test-folds', type=int, nargs='+')
    parser.add_argument('--epochs', type=int, default=120)
    parser.add_argument('--hidden', type=int, default=64)
    parser.add_argument('--learning-rate', type=float, default=.001)
    parser.add_argument('--batch-graphs', type=int, default=4)
    parser.add_argument('--resolution', type=int, default=32)
    parser.add_argument('--candidates', type=int, default=4)
    parser.add_argument('--patience-checks', type=int, default=5)
    args = parser.parse_args()
    if any(getattr(args, key) <= 0 for key in ['epochs', 'hidden', 'learning_rate', 'batch_graphs',
                                              'candidates', 'patience_checks']):
        parser.error('Training counts and hyperparameters must be positive')
    if args.resolution < 8 or len(args.seeds) != len(set(args.seeds)):
        parser.error('Resolution must be at least eight, and seeds must be unique')
    return args


@torch.no_grad()
def validation_loss(model, samples, candidates):
    scores = []
    for sample in samples:
        prediction, _ = generate(model, sample['inputs'], candidates)
        scores.append(float(objective(sample, prediction)))
    return float(np.mean(scores))


def fit(samples, args, fold, seed, output):
    torch.manual_seed(seed)
    model = BoundaryLayoutModel(args.hidden).to(args.device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=1e-4)
    order_generator = torch.Generator().manual_seed(seed + fold * 1000)
    slot_generator = torch.Generator(device=args.device).manual_seed(seed + 1)
    best_value = validation_loss(model, samples['validation'], args.candidates)
    best_epoch, stale = 0, 0
    best_state = deepcopy(model.state_dict())
    history = [{'epoch': 0, 'validation_objective': best_value}]
    started = time.monotonic()
    completed = 0
    for epoch in range(1, args.epochs + 1):
        model.train()
        order = torch.randperm(len(samples['train']), generator=order_generator).tolist()
        total = 0.
        for start in range(0, len(order), args.batch_graphs):
            indexes = order[start:start + args.batch_graphs]
            optimizer.zero_grad(set_to_none=True)
            losses = []
            for index in indexes:
                sample = samples['train'][index]
                anchors, noise = spatial_slots(sample['inputs'], slot_generator)
                prediction = model(sample['inputs'], anchors, noise)
                losses.append(objective(sample, prediction))
            loss = torch.stack(losses).mean()
            if not torch.isfinite(loss):
                raise FloatingPointError(f'Nonfinite layout loss at epoch {epoch}')
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5., error_if_nonfinite=True)
            optimizer.step()
            total += float(loss.detach()) * len(indexes)
        completed = epoch
        if epoch % 10 == 0 or epoch == args.epochs:
            measured = validation_loss(model, samples['validation'], args.candidates)
            history.append({'epoch': epoch, 'training_objective': total / len(order),
                            'validation_objective': measured, 'elapsed_seconds': time.monotonic() - started})
            if measured < best_value:
                best_value, best_epoch, stale = measured, epoch, 0
                best_state = deepcopy(model.state_dict())
            else:
                stale += 1
            write_json(output / 'history.json', history)
            print(json.dumps({'fold': fold, 'seed': seed, 'epoch': epoch,
                              'validation_objective': measured}), flush=True)
            if epoch >= 40 and stale >= args.patience_checks:
                break
    model.load_state_dict(best_state)
    checkpoint = {'state_dict': model.state_dict(), 'model_specification': model.specification(),
                  'best_epoch': best_epoch, 'resolution': args.resolution, 'candidates': args.candidates,
                  'input_contract': 'normalized_boundary_and_50_column_space_program_only',
                  'feature_order': args.feature_order,
                  'partitions': {role: [s['plan_id'] for s in rows] for role, rows in samples.items()}}
    temporary = output / 'weights.pt.tmp'
    torch.save(checkpoint, temporary)
    temporary.replace(output / 'weights.pt')
    loaded = torch.load(output / 'weights.pt', map_location='cpu', weights_only=True)
    restored = BoundaryLayoutModel(**loaded['model_specification']).to(args.device)
    restored.load_state_dict(loaded['state_dict'])
    rows = []
    predictions_dir = output / 'predictions'
    predictions_dir.mkdir()
    for sample in samples['test']:
        prediction, selection = generate(model, sample['inputs'], args.candidates)
        reloaded, _ = generate(restored, sample['inputs'], args.candidates)
        if not torch.equal(prediction, reloaded):
            raise RuntimeError('Reloaded layout model changed fixed-seed predictions')
        rows.append(score_layout(sample, prediction))
        bounds = boxes(prediction.cpu().numpy())
        polygons = [[[float(x0), float(y0)], [float(x1), float(y0)],
                     [float(x1), float(y1)], [float(x0), float(y1)]] for x0, y0, x1, y1 in bounds]
        write_json(predictions_dir / (sample['plan_id'] + '.json'),
                   {'plan_id': sample['plan_id'], 'node_ids': sample['node_ids'],
                    'predicted_boxes': prediction.cpu().tolist(), 'predicted_polygons': polygons,
                    'coordinate_frame': sample['coordinate_frame'], 'candidate_selection': selection})
    result = {'model': 'boundary_gcn', 'seed': seed, 'test_fold': fold,
              'best_epoch': best_epoch, 'epochs_completed': completed,
              'best_validation_objective': best_value,
              'elapsed_seconds': time.monotonic() - started,
              'parameters': sum(p.numel() for p in model.parameters()),
              'checkpoint_reload_predictions_identical': True,
              'partitions': checkpoint['partitions'], 'test_rows': rows}
    write_json(output / 'result.json', result)
    return result


def execute(args, output):
    root = args.project_root.resolve()
    directory = root / 'p-平面标注与数据处理/训练数据/单层医院_v1'
    samples, input_paths, vocabulary = load_layouts(directory, args.resolution)
    audit_path = args.source_audit or (root / 'e-实验评估/20261116_关系模型分组对照/run_20261116_111027_795796/source_audit.json')
    audit = json.loads(audit_path.read_text(encoding='utf-8'))
    group_ids = {r['plan_id']: r['group_id'] for r in audit['plans']}
    if set(group_ids) != {s['plan_id'] for s in samples}:
        raise ValueError('Layout data and frozen source groups differ')
    test_folds = args.test_folds if args.test_folds is not None else list(range(audit['fold_count']))
    if len(test_folds) != len(set(test_folds)) or any(not 0 <= f < audit['fold_count'] for f in test_folds):
        raise ValueError('Invalid or repeated test fold')
    hashes = fingerprints(input_paths + [audit_path], root)
    args.feature_order = vocabulary['node_feature_order']
    config = {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()}
    config.update({'created_at': datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
                   'torch': str(torch.__version__), 'numpy': np.__version__,
                   'outside_loss_weight': 2., 'overlap_loss_weight': .05,
                   'log_area_loss_weight': .02, 'candidate_selection_uses_target': False,
                   'matching_scope': 'same_50_input_columns_with_valid_geometry',
                   'level_balanced_loss': True, 'physical_navigation_output': False,
                   'source_grouping_status': audit['grouping_status']})
    write_json(output / 'config.json', config)
    write_json(output / 'source_audit.json', audit)
    write_json(output / 'input_hashes.json', hashes)
    snapshot = output / 'code_snapshot'
    snapshot.mkdir()
    for folder in ['boundary_layout', 'relation_prediction', 'layout_evaluation', 'room_layout_pilot']:
        destination = snapshot / folder
        destination.mkdir()
        for path in (Path(__file__).parents[1] / folder).glob('*.py'):
            shutil.copy2(path, destination / path.name)
    for sample in samples:
        move_sample(sample, args.device)
    runs = []
    for fold in test_folds:
        split = partitions(samples, audit, fold)
        baseline = ProgramMeanBaseline().fit(split['train'])
        baseline_rows = [score_layout(s, baseline.predict(s['inputs'])) for s in split['test']]
        statistics = {'default': baseline.default.tolist(), 'patterns': [
            {'features': list(key), 'mean_box_fraction': value.tolist()} for key, value in baseline.means.items()]}
        write_json(output / f'fold_{fold}_program_mean_statistics.json', statistics)
        baseline_result = {'model': 'program_mean', 'seed': None, 'test_fold': fold,
                           'partitions': {role: [s['plan_id'] for s in rows] for role, rows in split.items()},
                           'test_rows': baseline_rows}
        write_json(output / f'fold_{fold}_program_mean_result.json', baseline_result)
        runs.append(baseline_result)
        for seed in args.seeds:
            run_dir = output / f'fold_{fold}_seed_{seed}'
            run_dir.mkdir()
            write_json(output / 'status.json', {'status': 'running', 'fold': fold, 'seed': seed,
                                               'completed_neural_runs': sum(r['model'] != 'program_mean' for r in runs)})
            result = fit(split, args, fold, seed, run_dir)
            result['test_summary'] = aggregate(result['test_rows'], group_ids)
            write_json(run_dir / 'result.json', result)
            runs.append(result)
            write_json(output / 'summary.json', summarize(runs, group_ids))
            print(json.dumps({'completed_fold': fold, 'seed': seed, 'best_epoch': result['best_epoch'],
                              'test_room_iou': result['test_summary']['fine_rooms_box_iou']['group_macro']}), flush=True)
    if hashes != fingerprints(input_paths + [audit_path], root):
        raise RuntimeError('Layout labels or source groups changed during training')
    summary = summarize(runs, group_ids)
    summary.update({'input_files_unchanged': True, 'input_files_checked': len(hashes),
                    'test_folds': test_folds, 'grouping_status': audit['grouping_status'],
                    'total_test_rooms': sum(int(s['room_mask'].sum()) for s in samples)})
    write_json(output / 'summary.json', summary)
    write_json(output / 'status.json', {'status': 'complete', 'neural_runs': len(args.seeds) * len(test_folds),
                                       'full_source_coverage': len(test_folds) == audit['fold_count']})


def main():
    args = arguments()
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    if torch.device(args.device).type == 'cuda':
        torch.cuda.set_device(args.device)
    now = datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y%m%d_%H%M%S_%f')
    output = (args.output_dir or (args.project_root / 'e-实验评估/20261116_边界条件布局训练' / f'run_{now}')).resolve()
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / 'status.json', {'status': 'running'})
    print('OUTPUT_DIRECTORY=' + str(output), flush=True)
    try:
        execute(args, output)
    except BaseException as error:
        write_json(output / 'status.json', {'status': 'failed', 'error': repr(error)})
        raise


if __name__ == '__main__':
    main()
