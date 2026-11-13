"""Read the shared 53-plan export without using target geometry as input."""
import hashlib
import json
from pathlib import Path

import numpy as np
import torch


def pair_set(relations, size, positive=False):
    result = set()
    for row in relations:
        if row['type'] != 'access':
            continue
        if positive and not row.get('loss_mask', False):
            continue
        left, right = int(row['source_index']), int(row['target_index'])
        if not 0 <= left < size or not 0 <= right < size or left == right:
            raise ValueError('Invalid access endpoints')
        result.add(tuple(sorted((left, right))))
    return result


def pair_tensor(pairs):
    return torch.tensor(sorted(pairs), dtype=torch.long).reshape(-1, 2)


def prepare_sample(source):
    x = torch.tensor(source['inputs']['node_features'], dtype=torch.float32)
    if x.ndim != 2 or x.shape[1] != 50 or len(x) < 2:
        raise ValueError('Expected at least two nodes with the shared 50-column encoding')
    if not torch.isfinite(x).all():
        raise ValueError('Non-finite node features')
    size = len(x)
    ids = source['node_ids']
    if len(ids) != size or len(set(ids)) != size:
        raise ValueError('Node IDs and features disagree')
    if source['inputs'].get('provided_constraint_edges'):
        raise ValueError('This first model expects an inventory graph without provided edges')
    targets = source['targets']
    positives = pair_set(targets['relations'], size, positive=True)
    negatives = pair_set(targets.get('negative_relations', []), size)
    if positives & negatives:
        raise ValueError('Conflicting positive and negative access labels')
    pairs = torch.triu_indices(size, size, offset=1).T.contiguous()
    positive_pairs = pair_tensor(positives)
    negative_pairs = pair_tensor(negatives)
    labels = np.full(len(pairs), -1, dtype=np.int8)
    lookup = {tuple(pair): i for i, pair in enumerate(pairs.tolist())}
    for pair in positives:
        labels[lookup[pair]] = 1
    for pair in negatives:
        labels[lookup[pair]] = 0
    return {
        'plan_id': source['plan_id'], 'node_ids': ids,
        'names': [m.get('name', '') for m in source.get('metadata', [])],
        'x': x, 'all_pairs': pairs, 'positive_pairs': positive_pairs,
        'negative_pairs': negative_pairs, 'pair_labels': labels,
    }


def load_dataset(directory):
    directory = Path(directory).resolve()
    manifest_path = directory / 'manifest.json'
    vocabulary_path = directory / 'vocabulary.json'
    manifest = json.loads(manifest_path.read_text())
    vocabulary = json.loads(vocabulary_path.read_text())
    if len(vocabulary['node_feature_order']) != 50:
        raise ValueError('Unexpected feature vocabulary')
    samples, paths = [], [manifest_path, vocabulary_path]
    for entry in manifest['plans']:
        if entry['split'] != 'train':
            raise ValueError('This experiment is configured for all-plan training')
        path = (directory / entry['sample']).resolve()
        if not path.is_relative_to(directory):
            raise ValueError('Sample path leaves dataset directory')
        source = json.loads(path.read_text())
        if source['plan_id'] != entry['plan_id']:
            raise ValueError('Sample ID differs from manifest')
        sample = prepare_sample(source)
        sample['source_path'] = str(path)
        samples.append(sample)
        paths.append(path)
    ids = [sample['plan_id'] for sample in samples]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate plans in manifest')
    return samples, paths, vocabulary


def fingerprints(paths, root):
    root = Path(root).resolve()
    result = {}
    for path in sorted(set(Path(p).resolve() for p in paths)):
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(chunk)
        result[str(path.relative_to(root))] = digest.hexdigest()
    return result


def sample_training_pairs(sample, generator, maximum):
    population = sample['all_pairs']
    # Independent uniform draws from all pairs estimate the population marginal.
    selection = torch.randint(len(population), (maximum,), generator=generator)
    return population[selection]
