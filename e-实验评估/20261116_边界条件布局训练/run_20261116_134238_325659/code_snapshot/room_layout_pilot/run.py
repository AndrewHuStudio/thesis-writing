"""Run an isolated, reproducible single-plan GCN fitting experiment."""
import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
import platform
import shutil
import time
from zoneinfo import ZoneInfo

import numpy as np

from data import build_sample, feature_mean_baseline, indistinguishable_groups, json_sample
from evaluate import layout_metrics
from model import train
from render import comparison, loss_chart
from report import write_report


def hashes(paths):
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+'\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--epochs', type=int, default=6000)
    parser.add_argument('--seeds', type=int, nargs='+', default=[7, 19, 43])
    args = parser.parse_args()
    root = args.project_root.resolve()
    source = next((root / 'p-平面标注与数据处理/标注试样').glob('09_*/annotation.json'))
    source_files = sorted(p for p in source.parent.iterdir() if p.is_file())
    source_before = hashes(source_files)
    raw = json.loads(source.read_text())
    sample = build_sample(raw, 'health_examination', excluded_ids={'S123'})
    if len(sample['ids']) != 34 or int(sample['raw_adjacency'].sum()/2) != 57:
        raise ValueError('Source has changed; recheck the agreed experiment scope')
    now = datetime.now(ZoneInfo('Asia/Shanghai'))
    output = root / 'e-实验评估/20261103_09体检区_GCN复原' / now.strftime('run_%Y%m%d_%H%M%S_%f')
    output.mkdir(parents=True, exist_ok=False)
    (output / 'weights').mkdir()
    (output / 'code_snapshot').mkdir()
    for script in Path(__file__).parent.glob('*.py'):
        shutil.copy2(script, output / 'code_snapshot' / script.name)
    save_json(output / '训练样本.json', json_sample(sample))
    groups = indistinguishable_groups(sample['x'], sample['adjacency'])
    group_ids = [[sample['ids'][i] for i in g] for g in groups]
    print(json.dumps(dict(output=str(output), nodes=len(sample['ids']),
                          symmetry_groups=group_ids), ensure_ascii=False), flush=True)
    baseline_prediction = feature_mean_baseline(sample)
    baseline_metrics = layout_metrics(sample, baseline_prediction)
    runs, curves, predictions, displays = [], [], {}, {}
    started = time.perf_counter()
    for method in ['gcn', 'mlp']:
        for seed in args.seeds:
            result = train(sample, seed, args.epochs, graph=method == 'gcn')
            metrics = layout_metrics(sample, result['prediction'])
            label = f'{method}_seed{seed}'
            np.savez(output / 'weights' / (label+'.npz'), **result['model'].params)
            record = dict(method=method, seed=seed, best_step=result['best_step'],
                          best_train_mse=result['best_train_mse'],
                          parameters=result['parameters'], metrics=metrics)
            runs.append(record)
            curves.append(dict(label=label, history=result['history']))
            predictions[label] = result['prediction'].tolist()
            if seed == args.seeds[0]:
                displays[method] = result['prediction']
            print(json.dumps(dict(model=label, best_step=record['best_step'],
                                  iou=metrics['room_mean_box_iou'],
                                  overlap_pairs=metrics['overlap_pairs']),
                             ensure_ascii=False), flush=True)
    elapsed = time.perf_counter()-started
    predictions['feature_mean_baseline'] = baseline_prediction.tolist()
    save_json(output / '预测结果.json',
              dict(ids=sample['ids'], target_columns=['center_x', 'center_y', 'width', 'height'],
                   coordinates='isotropic normalized source coordinates',
                   reference_frame=sample['reference_frame'],
                   supervised_mask=sample['supervised_mask'].tolist(),
                   predictions=predictions))
    save_json(output / '训练日志.json', curves)
    by_method = {}
    for method in ['gcn', 'mlp']:
        selected = [r for r in runs if r['method'] == method]
        by_method[method] = {
            k: dict(mean=float(np.mean([r['metrics'][k] for r in selected])),
                    std=float(np.std([r['metrics'][k] for r in selected])))
            for k in ['room_mean_box_iou', 'room_center_distance_pct_long_side',
                      'room_matched_mean_box_iou', 'overlap_pairs']}
    summary = dict(created_at=now.isoformat(), task='single-graph conditional box reconstruction',
                   epochs=args.epochs, seeds=args.seeds, display_seed=args.seeds[0],
                   architecture='GCN 11->64->32; nodewise 32->4 sigmoid box head',
                   feature_names=sample['feature_names'],
                   optimizer=dict(name='Adam', learning_rate=0.01, betas=[0.9, 0.999]),
                   loss='mean squared normalized box error over 33 supervised nodes',
                   split='train only; no held-out validation/test; best checkpoint uses training loss',
                   scope='health_examination', nodes=34, supervised_nodes=33,
                   room_evaluation_nodes=int(sample['room_mask'].sum()),
                   input_whitelist=['type one-hot', 'level one-hot', 'given conceptual access graph'],
                   excluded_geometry=['S123 combined toilets'],
                   no_inputs=['coordinates', 'area', 'opening positions', 'S IDs', 'names',
                              'reference frame', 'building outline', 'entrances', 'cores'],
                   symmetry_groups=group_ids,
                   baseline=dict(method='same-feature target mean on training graph',
                                 metrics=baseline_metrics),
                   runs=runs, aggregates=by_method, elapsed_seconds=elapsed,
                   source_hashes_before=source_before,
                   code_hashes=hashes(sorted(Path(__file__).parent.glob('*.py'))),
                   environment=dict(python=platform.python_version(), numpy=np.__version__,
                                    new_dependencies_installed=False),
                   reference='https://arxiv.org/abs/1609.02907')
    layouts = [('参考：原标注多边形', None, '33个拟合节点；S123*为组合卫生间，仅作上下文'),
               ('基线：同功能/层级均值', baseline_prediction, '直接统计同图答案；用作位置坍缩参照'),
               (f'GCN：种子{args.seeds[0]}', displays['gcn'], '只输入功能、层级与已知概念连接'),
               (f'MLP：种子{args.seeds[0]}', displays['mlp'], '相同节点输入、相同参数规模；无消息传递')]
    comparison(sample, layouts, output)
    comparison(sample, [layouts[0], layouts[2]], output, basename='参考与GCN')
    loss_chart(curves, output)
    summary['source_hashes_after'] = hashes(source_files)
    summary['source_unchanged'] = source_before == summary['source_hashes_after']
    if not summary['source_unchanged']:
        raise RuntimeError('Source changed during the run; results need rechecking')
    save_json(output / '实验记录.json', summary)
    write_report(output, summary)
    print(json.dumps(dict(output=str(output), elapsed_seconds=elapsed,
                          source_unchanged=summary['source_unchanged'],
                          aggregates=by_method), ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
