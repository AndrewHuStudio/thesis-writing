"""Fixed-budget observed-positive recall with fractional treatment of score ties."""
from collections import defaultdict

import numpy as np
import torch

from metrics import budget_recall, score_sample


METRICS = ('recall_at_half_n', 'recall_at_n', 'recall_at_2n',
           'recall_at_observed_positive_budget', 'random_recall_at_n')


def sample_metrics(sample, scores, group_id):
    if len(scores) != len(sample['all_pairs']) or not np.isfinite(scores).all():
        raise ValueError('Invalid evaluation scores')
    labels = sample['pair_labels']
    nodes = len(sample['x'])
    positives = int((labels == 1).sum())
    budgets = {'recall_at_half_n': max(1, nodes // 2), 'recall_at_n': nodes,
               'recall_at_2n': 2 * nodes,
               'recall_at_observed_positive_budget': positives}
    result = {'plan_id': sample['plan_id'], 'group_id': group_id,
              'nodes': nodes, 'candidate_pairs': len(scores), 'known_positives': positives,
              'confirmed_negatives': int((labels == 0).sum()),
              'unlabeled_pairs': int((labels == -1).sum())}
    for name, budget in budgets.items():
        result[name] = budget_recall(scores, labels, budget)
    result['random_recall_at_n'] = min(nodes, len(scores)) / len(scores)
    result['distinct_scores'] = len(np.unique(scores))
    return result


def aggregate(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[row['group_id']].append(row)
    result = {'plans': len(rows), 'source_groups': len(groups)}
    for metric in METRICS:
        values = [row[metric] for row in rows if row[metric] is not None]
        result['plan_macro_' + metric] = float(np.mean(values)) if values else None
        group_values = []
        for members in groups.values():
            scores = [row[metric] for row in members if row[metric] is not None]
            if scores:
                group_values.append(float(np.mean(scores)))
        result['group_macro_' + metric] = float(np.mean(group_values)) if group_values else None
    return result


@torch.no_grad()
def evaluate(model, samples, group_ids, keep_scores=False):
    model.eval()
    rows, predictions = [], {}
    for sample in samples:
        scores = score_sample(model, sample).sigmoid().cpu().numpy()
        rows.append(sample_metrics(sample, scores, group_ids[sample['plan_id']]))
        if keep_scores:
            predictions[sample['plan_id']] = scores
    return aggregate(rows), rows, predictions
