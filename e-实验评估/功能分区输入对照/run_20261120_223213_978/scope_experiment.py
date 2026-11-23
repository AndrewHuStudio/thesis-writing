"""Isolated pilot adding recorded functional zones to the existing GCN benchmark."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import shutil
import sys
from unittest.mock import patch

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('root', type=Path)
parser.add_argument('--device', default='cuda:1')
opts = parser.parse_args()
root = opts.root.resolve()
output = Path(__file__).resolve().parent
modules = root / 'm-GCN模型/relation_prediction'
sys.path.insert(0, str(modules))

import numpy as np
import torch
from torch import nn
import benchmark_run as benchmark
from benchmark_groups import audit_digest, partitions, source_audit, write_json
from data import fingerprints, load_dataset
from model import SpaceRelationGCN

AMBIGUOUS = re.compile(r'unknown|undetermined|unconfirmed|unclassified|待核|未知', re.IGNORECASE)
RECALL = 'group_macro_recall_at_n'

class ScopedGCN(SpaceRelationGCN):
    """Append zone one-hots to node input and zone equality to the symmetric decoder."""

    def __init__(self, features, hidden):
        super().__init__(features, hidden)
        self.decoder = nn.Sequential(nn.Linear(3 * hidden + 2, hidden), nn.ReLU(),
                                     nn.Linear(hidden, 1))

    def encode(self, x):
        nodes = super().encode(x)
        return torch.cat((nodes, x[:, 50:].to(nodes.device)), dim=1)

    def decode(self, embeddings, pairs):
        left, right = embeddings[pairs.to(embeddings.device)].unbind(dim=1)
        a, left_zone = left[:, :self.hidden], left[:, self.hidden:]
        b, right_zone = right[:, :self.hidden], right[:, self.hidden:]
        same_zone = (left_zone * right_zone).sum(dim=1, keepdim=True)
        both_known = left_zone.sum(dim=1, keepdim=True) * right_zone.sum(dim=1, keepdim=True)
        features = torch.cat((a + b, (a - b).abs(), a * b, same_zone, both_known), dim=1)
        return self.decoder(features).squeeze(-1)


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def read_scopes(sample):
    metadata = read(Path(sample['source_path']))['metadata']
    if [row['id'] for row in metadata] != sample['node_ids']:
        raise ValueError(f"Scope metadata order differs from node IDs in {sample['plan_id']}")
    values = [str(row.get('scope_original') or '').strip().lower() for row in metadata]
    return ['' if AMBIGUOUS.search(value) else value for value in values]


def add_scopes(sample, scopes, vocabulary):
    encoded = torch.zeros((len(scopes), len(vocabulary)), dtype=sample['x'].dtype)
    for index, scope in enumerate(scopes):
        if scope in vocabulary:
            encoded[index, vocabulary[scope]] = 1
    return {**sample, 'x': torch.cat((sample['x'], encoded), dim=1)}


def partition_metadata(split, scopes, vocabulary):
    return {role: {'nodes': sum(len(s['node_ids']) for s in plans),
                   'encoded_nodes': sum(tag in vocabulary for s in plans
                                        for tag in scopes[s['plan_id']])}
            for role, plans in split.items()}


def duplicated_nodes(x):
    _, counts = torch.unique(x, dim=0, return_counts=True)
    return int(counts[counts > 1].sum())


def ties_at_budget(path):
    with np.load(path) as data:
        scores = data['scores']
        k = min(len(data['node_ids']), len(scores))
        threshold = np.partition(scores, len(scores) - k)[len(scores) - k]
        higher = int(np.count_nonzero(scores > threshold))
        tied = int(np.count_nonzero(scores == threshold))
    return {'tied': tied, 'partial': tied > k - higher}


def calculate_ties(directory, plans):
    stats = [ties_at_budget(directory / f'{plan}.npz') for plan in plans]
    partial = [row['tied'] for row in stats if row['partial']]
    return {'plans': len(plans), 'partial_ties': len(partial),
            'sum_partial_tie_group_sizes': sum(partial)}


def example_scores(directory, plan_id):
    with np.load(directory / f'{plan_id}.npz') as data:
        ids = data['node_ids'].tolist()
        pairs = data['pairs']
        partner = ids.index('S033')
        return {node: float(data['scores'][np.flatnonzero(
                    np.all(pairs == sorted((ids.index(node), partner)), axis=1))[0]])
                for node in ('S005', 'S007', 'S023')}


def main():
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    if torch.device(opts.device).type == 'cuda':
        torch.cuda.set_device(torch.device(opts.device))
    old = root / 'e-实验评估/20261116_关系模型分组对照/run_20261116_111027_795796'
    directory = root / 'p-平面标注与数据处理/训练数据/单层医院_v1'
    config = read(old / 'config.json')
    config['device'] = opts.device
    args = argparse.Namespace(**config)
    samples, paths, _ = load_dataset(directory)
    before = fingerprints(paths, root)
    if before != read(old / 'input_hashes.json'):
        raise RuntimeError('Current data fingerprints differ from the previous benchmark')
    audit = source_audit(directory, samples, args.folds)
    if audit_digest(audit) != config['source_audit_sha256']:
        raise RuntimeError('Current source-group split differs from previous benchmark')
    group_ids = {r['plan_id']: r['group_id'] for r in audit['plans']}
    scopes = {s['plan_id']: read_scopes(s) for s in samples}
    snapshot = output / 'code_snapshot'
    snapshot.mkdir()
    for filename in ('benchmark_run.py', 'benchmark_groups.py', 'benchmark_metrics.py',
                     'benchmark_models.py', 'data.py', 'metrics.py', 'model.py'):
        shutil.copy2(modules / filename, snapshot / filename)
    write_json(output / 'configuration.json', {
        'baseline': str(old), 'source_audit_sha256': audit_digest(audit),
        'folds': args.folds, 'seeds': args.seeds, 'device': args.device,
        'torch': str(torch.__version__),
        'settings': {name: getattr(args, name) for name in (
            'epochs', 'hidden', 'learning_rate', 'prior_multiplier', 'population_pairs',
            'batch_graphs', 'patience_checks')},
        'zone_field': 'metadata.scope_original',
        'zone_encoding': 'train-fold vocabulary; absent, uncertain and unseen zones are zero',
        'decoder_inputs': ['same known zone', 'both zones known'],
        'evaluation': 'exploratory; retrospective zone annotations supplied for held-out floors',
        'labels': 'same original positive, unlabeled and confirmed-negative observations',
    })
    write_json(output / 'input_hashes.json', before)
    results, tie_stats, coverage = [], [], []
    example = next(s['plan_id'] for s in samples if s['plan_id'].startswith('44_'))
    for fold in range(args.folds):
        split = partitions(samples, audit, fold)
        train_tags = sorted({scope for s in split['train'] for scope in scopes[s['plan_id']] if scope})
        if not train_tags:
            raise RuntimeError(f'No training scopes in fold {fold}')
        vocabulary = {tag: i for i, tag in enumerate(train_tags)}
        extended = {role: [add_scopes(s, scopes[s['plan_id']], vocabulary) for s in plans]
                    for role, plans in split.items()}
        test_plans = [s['plan_id'] for s in split['test']]
        cov = partition_metadata(split, scopes, vocabulary)
        coverage.append({'fold': fold, 'vocabulary_size': len(vocabulary), **cov,
                         'test_duplicate_nodes_before': sum(duplicated_nodes(s['x']) for s in split['test']),
                         'test_duplicate_nodes_after': sum(duplicated_nodes(s['x']) for s in extended['test'])})
        write_json(output / f'fold_{fold}_vocabulary.json', {
            'vocabulary': vocabulary, 'node_feature_width': 50 + len(vocabulary)})
        for seed in args.seeds:
            name = f'fold_{fold}_gcn_seed_{seed}'
            baseline = old / name
            original = read(baseline / 'result.json')
            current = {role: [s['plan_id'] for s in plans] for role, plans in split.items()}
            if current != original['partitions']:
                raise RuntimeError(f'Plan partitions differ for {name}')
            target = output / name
            target.mkdir()
            write_json(output / 'status.json', {'status': 'running', 'current_run': name,
                                               'completed': len(results), 'total': args.folds * len(args.seeds)})
            with patch.object(benchmark, 'build_model', side_effect=lambda kind, hidden:
                              ScopedGCN(50 + len(vocabulary), hidden)):
                result = benchmark.fit_neural('gcn', extended, group_ids, seed, fold, args, target)
            results.append(result)
            tie = {'run': name, 'baseline': calculate_ties(baseline, test_plans),
                   'scoped': calculate_ties(target, test_plans)}
            if example in test_plans:
                tie['example'] = {'plan': example, 'baseline': example_scores(baseline, example),
                                  'scoped': example_scores(target, example)}
            tie_stats.append(tie)
            write_json(output / 'progress.json', {'coverage': coverage, 'tie_stats': tie_stats,
                       'scoped': benchmark.summarize(results, len(samples))})
            print(f'{name}  baseline={original["test_summary"][RECALL]:.4%}'
                  f'  scoped={result["test_summary"][RECALL]:.4%}', flush=True)
    if before != fingerprints(paths, root):
        raise RuntimeError('Source data were changed during training')
    summary = benchmark.summarize(results, len(samples))
    write_json(output / 'summary.json', {'scoped': summary, 'baseline': read(old / 'summary.json'),
               'scope_and_encoding': coverage, 'tie_stats': tie_stats, 'source_files_verified': len(paths)})
    write_json(output / 'status.json', {'status': 'complete', 'completed': len(results)})
    print(summary['comparisons'][0]['metrics'][RECALL], flush=True)


if __name__ == '__main__':
    try:
        main()
    except BaseException as error:
        write_json(output / 'status.json', {'status': 'failed', 'error': repr(error)})
        raise
