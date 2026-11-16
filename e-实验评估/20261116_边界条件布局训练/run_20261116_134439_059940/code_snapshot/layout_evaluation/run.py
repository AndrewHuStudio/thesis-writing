"""Remeasure existing layout predictions and held-out candidate graph topology."""
import argparse
from collections import defaultdict
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import sys
from zoneinfo import ZoneInfo

import numpy as np
from shapely.affinity import affine_transform
from shapely.geometry import Polygon
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from layout_evaluation.metrics import geometry_metrics, graph_metrics


ROOT = Path(__file__).resolve().parents[2]


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n',
                         encoding='utf-8')
    temporary.replace(path)


def fingerprints(paths, root):
    result = {}
    for path in sorted(set(paths)):
        result[path.resolve().relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def boundary_in_pilot_frame(source, frame):
    """Transform exported y-up building coordinates into the pilot's y-down frame."""
    domain = unary_union([Polygon(part['outer'], part.get('holes', []))
                          for part in source['inputs']['boundary']])
    current = source['coordinate_frame']
    ratio = current['long_side_px'] / frame['scale_px']
    x_offset = (current['origin_px'][0] - frame['origin_px'][0]) / frame['scale_px']
    y_offset = (current['origin_px'][1] - frame['origin_px'][1]) / frame['scale_px']
    return affine_transform(domain, [ratio, 0, 0, -ratio, x_offset, y_offset])


def select_runs(root, pilot_override, relation_override):
    pilot = pilot_override
    if pilot is None:
        candidates = list((root / 'e-实验评估/20261103_09体检区_GCN复原').glob('run_*'))
        pilot = max(candidates, key=lambda path: (read_json(path / '实验记录.json')['epochs'], path.name))
    relation = relation_override
    if relation is None:
        candidates = []
        for path in (root / 'e-实验评估/20261116_关系模型分组对照').glob('run_*'):
            summary_path = path / 'summary.json'
            if summary_path.exists() and read_json(path / 'status.json')['status'] == 'complete':
                if all(row['all_plans_evaluated_once'] for row in read_json(summary_path)['per_seed']):
                    candidates.append(path)
        relation = max(candidates)
    return pilot.resolve(), relation.resolve()


def evaluate_pilot(pilot, source, output):
    sample = read_json(pilot / '训练样本.json')
    prediction = read_json(pilot / '预测结果.json')
    record = read_json(pilot / '实验记录.json')
    source_hash = next(value for key, value in record['source_hashes_before'].items()
                       if Path(key).name == 'annotation.json')
    if source_hash != source['provenance']['source_annotation_sha256']:
        raise ValueError('Pilot annotation and current boundary provenance differ')
    if prediction['ids'] != sample['ids'] or prediction['reference_frame'] != sample['reference_frame']:
        raise ValueError('Saved layout prediction identities or coordinate frame differ')
    boundary = boundary_in_pilot_frame(source, sample['reference_frame'])
    rows = []
    for name, values in prediction['predictions'].items():
        if name == 'feature_mean_baseline':
            continue
        measured = geometry_metrics(sample, values, boundary)
        row = {'model': name.split('_seed', 1)[0], 'seed': int(name.split('_seed', 1)[1]),
               'metrics': measured}
        rows.append(row)
    metrics = ['mean_center_distance_pct_scope_long_side', 'mean_box_iou', 'mean_polygon_iou',
               'mean_polygon_area_relative_error', 'room_overlap_pair_count',
               'room_overlap_area_fraction', 'outside_building_area_fraction']
    aggregates = {}
    for kind in sorted({row['model'] for row in rows}):
        selected = [row['metrics'] for row in rows if row['model'] == kind]
        aggregates[kind] = {metric: {'mean': float(np.mean([row[metric] for row in selected])),
                                    'seed_standard_deviation': float(np.std(
                                        [row[metric] for row in selected], ddof=1)) if len(selected) > 1 else None}
                            for metric in metrics}
    result = {'source_run': str(pilot), 'scope': record['scope'], 'epochs': record['epochs'],
              'evaluation_status': 'historical_same_graph_fit_diagnostic',
              'input_conditions': record['input_whitelist'], 'evaluated_rooms': rows[0]['metrics']['evaluation_rooms'],
              'boundary': 'known_input_boundary_of_current_full_09_plan',
              'absolute_metric_scale_available': False, 'equivalent_room_matching': 'not_applied',
              'matching_note': 'Scored by saved identity. Interchangeable-instance matching requires an explicit equivalence definition.',
              'reference_room_overlap_pair_count': rows[0]['metrics']['reference_room_overlap_pair_count'],
              'aggregates': aggregates, 'runs': rows}
    write_json(output / 'layout_geometry.json', result)
    return result


def evaluate_graphs(relation, output):
    audit = read_json(relation / 'source_audit.json')
    group_ids = {row['plan_id']: row['group_id'] for row in audit['plans']}
    rows, seen = [], set()
    for path in sorted(relation.glob('fold_*_seed_*/*.npz')):
        kind, seed = path.parent.name.split('_')[2], int(path.parent.name.split('_')[4])
        key = (kind, seed, path.stem)
        if key in seen:
            raise ValueError('Repeated held-out plan for a model and seed')
        seen.add(key)
        with np.load(path, allow_pickle=False) as prediction:
            measured = graph_metrics(prediction['scores'], prediction['pairs'], len(prediction['node_ids']))
        rows.append({'model': kind, 'seed': seed, 'plan_id': path.stem,
                     'group_id': group_ids[path.stem], 'topology': measured})
    seeds = sorted({(row['model'], row['seed']) for row in rows})
    per_seed = []
    for kind, seed in seeds:
        selected = [row for row in rows if row['model'] == kind and row['seed'] == seed]
        if {row['plan_id'] for row in selected} != set(group_ids):
            raise ValueError('Incomplete held-out source coverage')
        groups = defaultdict(list)
        for row in selected:
            groups[row['group_id']].append(row)
        metrics = {}
        for metric in selected[0]['topology']['metrics']:
            means = [np.mean([row['topology']['metrics'][metric]['mean'] for row in members])
                     for members in groups.values()]
            metrics[metric] = float(np.mean(means))
        per_seed.append({'model': kind, 'seed': seed, 'source_group_macro': metrics})
    aggregates = {}
    for kind in sorted({row['model'] for row in per_seed}):
        selected = [row['source_group_macro'] for row in per_seed if row['model'] == kind]
        aggregates[kind] = {metric: {'mean': float(np.mean([row[metric] for row in selected])),
                                    'seed_standard_deviation': float(np.std(
                                        [row[metric] for row in selected], ddof=1)) if len(selected) > 1 else None}
                            for metric in selected[0]}
    result = {'source_run': str(relation), 'evaluation_status': audit['grouping_status'],
              'plans': len(group_ids), 'source_groups': len(audit['groups']),
              'model_seed_plan_predictions': len(rows), 'tie_trials_per_prediction': 20,
              'physical_routes': {'status': 'unavailable',
                                  'reason': 'Saved predictions contain conceptual pair scores without generated doors or traversable corridor geometry.'},
              'aggregates': aggregates, 'per_seed': per_seed, 'per_plan': rows}
    write_json(output / 'candidate_graph_topology.json', result)
    return result


def write_report(output, layout, graphs, readiness):
    names = {'gcn': 'GCN', 'mlp': 'MLP'}
    seed_count = len({row['seed'] for row in layout['runs']})
    lines = ['# 已有模型的布局与连通性复测', '',
             '已自动复测现有09号体检区布局预测，并检查53图留出关系候选的图连通性。'
             '完整53图布局评价需要相应的空间坐标或轮廓预测。', '',
             f"09号选用已有{layout['epochs']}步、{seed_count}个随机种子的布局预测，评价{layout['evaluated_rooms']}个有效房间。"
             '模型在同一张图上拟合，并使用给定的概念连接，结果属于历史原型诊断。', '',
             '| 方法 | 位置偏移占片区长边 | 房间框IoU | 房间轮廓IoU | 面积相对误差 | 房间重叠对数 | 重叠占地比例 | 建筑越界面积比例 |',
             '| --- | --- | --- | --- | --- | --- | --- | --- |']
    for kind, metrics in layout['aggregates'].items():
        mean = {key: value['mean'] for key, value in metrics.items()}
        lines.append(f"| {names[kind]} | {mean['mean_center_distance_pct_scope_long_side']:.2f}% | "
                     f"{mean['mean_box_iou']:.3f} | {mean['mean_polygon_iou']:.3f} | "
                     f"{100 * mean['mean_polygon_area_relative_error']:.2f}% | "
                     f"{mean['room_overlap_pair_count']:.2f} | {100 * mean['room_overlap_area_fraction']:.2f}% | "
                     f"{100 * mean['outside_building_area_fraction']:.2f}% |")
    lines.extend(['', '面积按原标注多边形计算，预测轮廓采用模型输出的矩形。重叠仅检查当前评价房间，'
                  '多重重叠区域按面积计一次，重叠占地比例以所有预测房间的占地并集面积为分母。'
                  '建筑越界检查使用当前09号整张图的已知输入边界，'
                  '与体检片区的参照窗范围分别记录。', '',
                  f"原标注中，这些有效房间有{layout['reference_room_overlap_pair_count']}对轮廓重叠。"
                  '当前采用保存的节点身份对应，尚未应用等价房间互换匹配。可靠米制尺度缺失，'
                  '距离与面积采用相对值。', '',
                  f"53图按每图节点数n保留n对候选关系，在截断处分数相同时重复随机抽样20次，"
                  '避免任意节点编号决定图结构。下表按暂定来源组和随机种子平均。', '',
                  '| 方法 | 孤立节点比例 | 最大连通分量节点比例 | 每图连通分量数 |',
                  '| --- | --- | --- | --- |'])
    for kind, metrics in graphs['aggregates'].items():
        lines.append(f"| {names[kind]} | {100 * metrics['isolated_node_fraction']['mean']:.2f}% | "
                     f"{100 * metrics['largest_component_node_fraction']['mean']:.2f}% | "
                     f"{metrics['component_count']['mean']:.2f} |")
    lines.extend(['', '这些指标描述候选关系图的拓扑。实际入口到房间的可达性和行走距离，'
                  '需要生成的走廊、通行口及有效入口锚点。当前物理通行评价状态为待补充输出。', '',
                  '候选图包含原空间清单中的全部节点。某个孤立节点是否构成设计问题，'
                  '还需要结合其功能和实际通行要求判断。', '',
                  f"现有53图数据具备{readiness['valid_room_geometry_nodes']}个有效且功能明确的单间几何标签。"
                  '当前53图模型预测文件包含空间对分数，完整留出布局的位置、面积、重叠、越界及路径评价'
                  '将在布局预测输出后执行。', '',
                  '我可以自动执行几何计算、候选关系图检查、批量评分和结果整理。'
                  '方案的医疗功能组织和使用体验需要专业评价，图纸疑难项也需要结合证据确认。', '',
                  '[逐房间几何结果](layout_geometry.json)　[逐图候选图结果](candidate_graph_topology.json)　'
                  '[数据与输出检查](readiness.json)', '',
                  f"历史布局预测来自 `{layout['source_run']}`。关系候选来自 `{graphs['source_run']}`。"])
    (output / '自动测试结果.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', type=Path, default=ROOT)
    parser.add_argument('--pilot-run', type=Path)
    parser.add_argument('--relation-run', type=Path)
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args()
    root = args.project_root.resolve()
    pilot, relation = select_runs(root, args.pilot_run, args.relation_run)
    data = root / 'p-平面标注与数据处理/训练数据/单层医院_v1'
    current = next((data / 'samples').glob('09_*.json'))
    source = read_json(current)
    annotation = root / source['provenance']['source_annotation']
    if hashlib.sha256(annotation.read_bytes()).hexdigest() != source['provenance']['source_annotation_sha256']:
        raise ValueError('Original annotation differs from exported provenance')
    files = [pilot / name for name in ['训练样本.json', '预测结果.json', '实验记录.json']]
    files += [relation / name for name in ['source_audit.json', 'summary.json', 'config.json']]
    files += list(relation.glob('fold_*_seed_*/*.npz'))
    files += [current, annotation, data / 'manifest.json']
    before = fingerprints(files, root)
    now = datetime.now(ZoneInfo('Asia/Shanghai'))
    output = args.output_dir or (root / 'e-实验评估/20261116_布局与连通性复测' / now.strftime('run_%Y%m%d_%H%M%S_%f'))
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    print('OUTPUT_DIRECTORY=' + str(output), flush=True)
    write_json(output / 'status.json', {'status': 'running'})
    try:
        layout = evaluate_pilot(pilot, source, output)
        graphs = evaluate_graphs(relation, output)
        manifest = read_json(data / 'manifest.json')
        readiness = {'user_inputs': ['building_boundary', 'space_program'],
                     'plans': len(manifest['plans']),
                     'valid_room_geometry_nodes': sum(row['known_single_rooms'] for row in manifest['plans']),
                     'geometry_prediction_coverage_in_53_plan_run': 0,
                     'full_layout_evaluation_status': 'awaiting_generated_layout_coordinates_and_outlines',
                     'physical_navigation_status': graphs['physical_routes'],
                     'historical_layout_diagnostic_completed': True,
                     'heldout_candidate_graph_diagnostic_completed': True}
        write_json(output / 'readiness.json', readiness)
        write_report(output, layout, graphs, readiness)
        after = fingerprints(files, root)
        if before != after:
            raise RuntimeError('Source data changed during evaluation')
        snapshot = output / 'code_snapshot'
        snapshot.mkdir()
        for path in Path(__file__).parent.glob('*.py'):
            shutil.copy2(path, snapshot / path.name)
        shutil.copy2(Path(__file__).parents[1] / 'room_layout_pilot/evaluate.py', snapshot / 'pilot_evaluate.py')
        write_json(output / 'verification.json', {'created_at': now.isoformat(), 'input_files_unchanged': True,
                                                 'input_hashes': before})
        write_json(output / 'status.json', {'status': 'complete', 'evaluated_historical_rooms': layout['evaluated_rooms'],
                                           'heldout_plans': graphs['plans'],
                                           'full_53_plan_layout_metrics_available': False})
        print(json.dumps({'layout': layout['aggregates'], 'candidate_graphs': graphs['aggregates']},
                         ensure_ascii=False), flush=True)
    except BaseException as error:
        write_json(output / 'status.json', {'status': 'failed', 'error': repr(error)})
        raise


if __name__ == '__main__':
    main()
