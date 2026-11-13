"""Training-only diagnostics with explicit unknown labels and fractional ties."""
import numpy as np
import torch

from model import assumed_prior, pu_risk


def budget_recall(scores, labels, budget):
    positives = labels == 1
    if not positives.any() or budget <= 0:
        return None
    budget = min(budget, len(scores))
    threshold = np.partition(scores, len(scores) - budget)[len(scores) - budget]
    above, tied = scores > threshold, scores == threshold
    fraction = (budget - above.sum()) / tied.sum()
    recovered = (above & positives).sum() + fraction * (tied & positives).sum()
    return float(recovered / positives.sum())


@torch.no_grad()
def score_sample(model, sample, chunk_size=4096):
    embeddings = model.encode(sample['x'])
    result = []
    for start in range(0, len(sample['all_pairs']), chunk_size):
        pairs = sample['all_pairs'][start:start + chunk_size]
        result.append(model.decode(embeddings, pairs))
    return torch.cat(result)


@torch.no_grad()
def diagnostics(model, samples, multiplier):
    model.eval()
    rows, predictions = [], []
    for sample in samples:
        logits = score_sample(model, sample)
        labels = sample['pair_labels']
        positive_logits = logits[torch.from_numpy(labels == 1)]
        prior = assumed_prior(sample, multiplier)
        risk = pu_risk(positive_logits, logits, prior)
        negative_logits = logits[torch.from_numpy(labels == 0)]
        if negative_logits.numel():
            risk += torch.nn.functional.softplus(negative_logits).mean()
        scores = logits.sigmoid().numpy()
        rows.append({
            'plan_id': sample['plan_id'], 'nodes': len(sample['x']),
            'candidate_pairs': len(scores), 'known_positives': int((labels == 1).sum()),
            'known_negatives': int((labels == 0).sum()),
            'unlabeled_pairs': int((labels == -1).sum()), 'assumed_prior': prior,
            'pu_risk_plus_known_negatives': float(risk),
            'recall_at_observed_edge_budget': budget_recall(scores, labels, int((labels == 1).sum())),
            'mean_known_positive_score': float(scores[labels == 1].mean()),
            'known_negative_scores': scores[labels == 0].tolist(),
            'distinct_scores': len(np.unique(scores)),
        })
        predictions.append(scores)
    summary = {
        'evaluation_scope': 'all_53_training_plans',
        'macro_pu_risk_plus_known_negatives': float(np.mean([
            row['pu_risk_plus_known_negatives'] for row in rows])),
        'macro_recall_at_observed_edge_budget': float(np.mean([
            row['recall_at_observed_edge_budget'] for row in rows])),
        'plans': len(rows), 'known_positive_pairs': sum(row['known_positives'] for row in rows),
        'known_negative_pairs': sum(row['known_negatives'] for row in rows),
    }
    return summary, rows, predictions
