"""Prepare boundary and program inputs separately from masked layout targets."""
from collections import defaultdict
import json
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import Polygon
from shapely.ops import unary_union
import torch

from relation_prediction.data import load_dataset, pair_set, pair_tensor


def prepare_inputs(source, resolution=32):
    features = torch.tensor(source['inputs']['node_features'], dtype=torch.float32)
    if features.ndim != 2 or features.shape[1] != 50 or len(features) < 2:
        raise ValueError('Expected at least two spaces with the existing 50-column vocabulary')
    if not torch.isfinite(features).all() or not torch.all((features == 0) | (features == 1)):
        raise ValueError('Expected finite binary program features')
    boundary = unary_union([Polygon(part['outer'], part.get('holes', []))
                            for part in source['inputs']['boundary']])
    if boundary.is_empty or not boundary.is_valid or boundary.area <= 0:
        raise ValueError('Known input boundary must have valid positive area')
    xmin, ymin, xmax, ymax = boundary.bounds
    if not np.allclose([xmin, ymin], 0, atol=1e-6) or not np.isclose(max(xmax, ymax), 1, atol=1e-6):
        raise ValueError('Normalize the provided boundary to origin zero and longest side one')
    if resolution < 8:
        raise ValueError('Boundary grid resolution must be at least eight')
    xs = (np.arange(resolution) + .5) / resolution * xmax
    ys = (np.arange(resolution) + .5) / resolution * ymax
    xx, yy = np.meshgrid(xs, ys)
    inside = shapely.contains_xy(boundary, xx, yy)
    if not inside.any():
        raise ValueError('Boundary grid has no interior points, increase resolution')
    distances = shapely.distance(shapely.points(xx, yy), boundary.boundary)
    signed = np.where(inside, -distances, distances).astype(np.float32)
    channels = np.stack((inside.astype(np.float32), signed))
    encoded_grid = torch.nn.functional.interpolate(torch.tensor(channels).unsqueeze(0),
                                                   size=(32, 32), mode='bilinear', align_corners=False)
    return {'x': features, 'boundary_channels': encoded_grid,
            'distance_field': torch.tensor(signed).reshape(1, 1, resolution, resolution),
            'extent': torch.tensor([xmax, ymax], dtype=torch.float32),
            'interior_points': torch.tensor(np.column_stack((xx[inside], yy[inside])), dtype=torch.float32),
            'room_constraint_mask': (features[:, 43] > .5) & (features[:, 49] > .5)}


def prepare_layout(source, resolution=32):
    inputs = prepare_inputs(source, resolution)
    target = torch.tensor(source['targets']['boxes'], dtype=torch.float32)
    masks = source['masks']
    valid = np.asarray(masks['layout'], dtype=bool) & np.asarray(masks['function'], dtype=bool)
    rooms = np.asarray(masks['known_single_room'], dtype=bool) & valid
    if target.shape != (len(inputs['x']), 4) or not torch.isfinite(target[valid]).all():
        raise ValueError('Invalid masked box targets')
    if not valid.any() or torch.any(target[valid, 2:] <= 0):
        raise ValueError('Layout supervision needs positive-area eligible targets')
    groups = defaultdict(list)
    for index in np.flatnonzero(valid):
        groups[tuple(inputs['x'][index].tolist())].append(int(index))
    levels = inputs['x'][:, 43:49].argmax(dim=1).numpy()
    return {'plan_id': source['plan_id'], 'node_ids': source['node_ids'],
            'inputs': inputs, 'target': target, 'valid_mask': torch.tensor(valid),
            'room_mask': rooms, 'match_groups': list(groups.values()),
            'level_groups': [np.flatnonzero(valid & (levels == level)).tolist() for level in np.unique(levels[valid])],
            'polygons': source['targets']['polygons'], 'metadata': source['metadata'],
            'reference_access_pairs': pair_tensor(pair_set(source['targets'].get('relations', []),
                                                          len(inputs['x']), positive=True)),
            'boundary_parts': source['inputs']['boundary'],
            'coordinate_frame': source['coordinate_frame']}


def load_layouts(directory, resolution=32):
    samples, paths, vocabulary = load_dataset(directory)
    result = []
    for sample in samples:
        source = json.loads(Path(sample['source_path']).read_text(encoding='utf-8'))
        prepared = prepare_layout(source, resolution)
        prepared['source_path'] = sample['source_path']
        result.append(prepared)
    return result, paths, vocabulary


def move_sample(sample, device):
    sample['inputs'] = {key: value.to(device) for key, value in sample['inputs'].items()}
    sample['target'] = sample['target'].to(device)
    sample['valid_mask'] = sample['valid_mask'].to(device)


class ProgramMeanBaseline:
    def fit(self, samples):
        groups, all_targets = defaultdict(list), []
        for sample in samples:
            normalized = (sample['target'] / sample['inputs']['extent'].repeat(2)).cpu().numpy()
            features = sample['inputs']['x'].cpu().numpy()
            for index in np.flatnonzero(sample['valid_mask'].cpu().numpy()):
                groups[tuple(features[index])].append(normalized[index])
                all_targets.append(normalized[index])
        self.means = {key: np.mean(values, axis=0) for key, values in groups.items()}
        self.default = np.mean(all_targets, axis=0)
        return self

    def predict(self, inputs):
        rows = [self.means.get(tuple(row), self.default) for row in inputs['x'].cpu().numpy()]
        return torch.tensor(np.asarray(rows), dtype=torch.float32,
                            device=inputs['x'].device) * inputs['extent'].repeat(2)
