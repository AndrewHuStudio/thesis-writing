"""Node-only MLP and train-source-only observed-density comparison models."""
from collections import Counter

import numpy as np
from torch import nn

from model import SpaceRelationGCN


class PairMLP(SpaceRelationGCN):
    def __init__(self, features=50, hidden=32):
        super().__init__(features, hidden)
        self.first = nn.Sequential(nn.Linear(features, hidden), nn.ReLU())
        self.second = nn.Sequential(nn.Linear(hidden, hidden), nn.ReLU())

    def encode(self, x):
        device = self.first[0].weight.device
        return self.second(self.first(x.to(device)))


def feature_codes(sample):
    features = sample['x'].cpu().numpy()
    if features.shape[1] != 50 or not np.isin(features, [0, 1]).all():
        raise ValueError('Density baseline expects the existing 50 binary input columns')
    weights = np.left_shift(np.uint64(1), np.arange(50, dtype=np.uint64))
    return features.astype(np.uint64) @ weights


def pair_codes(sample, pairs):
    codes = feature_codes(sample)
    return np.sort(codes[pairs.cpu().numpy()], axis=1)


class ObservedDensity:
    """Estimate observed-label density, with pooled training density for unseen pairs."""
    def fit(self, samples):
        totals, positives = Counter(), Counter()
        for sample in samples:
            for pairs, counts in ((sample['all_pairs'], totals),
                                  (sample['positive_pairs'], positives)):
                keys, numbers = np.unique(pair_codes(sample, pairs), axis=0, return_counts=True)
                for key, number in zip(keys, numbers):
                    counts[tuple(key)] += int(number)
        if not totals:
            raise ValueError('Density baseline needs training samples')
        self.densities = {key: positives[key] / count for key, count in totals.items()}
        self.default = sum(positives.values()) / sum(totals.values())
        return self

    def predict(self, sample):
        return np.fromiter((self.densities.get(tuple(key), self.default)
                            for key in pair_codes(sample, sample['all_pairs'])), dtype=float)


def build_model(kind, hidden):
    constructors = {'gcn': SpaceRelationGCN, 'mlp': PairMLP}
    return constructors[kind](features=50, hidden=hidden)
