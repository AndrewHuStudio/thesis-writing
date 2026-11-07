"""Read annotations without mutation; keep model inputs apart from geometry."""
from collections import defaultdict

import numpy as np


def normalized_adjacency(raw):
    """Kipf-Welling propagation matrix, with one self-loop per node."""
    graph = (np.asarray(raw) > 0).astype(float)
    np.fill_diagonal(graph, 1.0)
    degree = graph.sum(axis=1)
    return graph / np.sqrt(degree[:, None] * degree[None, :])


def build_sample(data, scope, excluded_ids=()):
    nodes = [s for s in data['spaces'] if s['scope'] == scope]
    if not nodes:
        raise ValueError('No nodes in the requested scope')
    ids = [s['id'] for s in nodes]
    index = {sid: i for i, sid in enumerate(ids)}
    types = sorted({s['type'] for s in nodes})
    levels = sorted({s['level'] for s in nodes})
    feature_names = ['type:' + t for t in types] + ['level:' + v for v in levels]
    x = np.zeros((len(nodes), len(feature_names)))
    for i, s in enumerate(nodes):
        x[i, types.index(s['type'])] = 1.0
        x[i, len(types) + levels.index(s['level'])] = 1.0
    raw = np.zeros((len(nodes), len(nodes)))
    internal, interfaces = [], []
    for r in data['relations']:
        a, b = r.get('source'), r['target']
        if a in index and b in index:
            internal.append(r)
            if r['type'] == 'access':
                raw[index[a], index[b]] = raw[index[b], index[a]] = 1.0
        elif (a in index) != (b in index):
            interfaces.append(r)
    rects = []
    for s in nodes:
        points = np.asarray(s['polygon_px'], dtype=float)
        rects.append([*points.min(axis=0), *points.max(axis=0)])
    rects = np.asarray(rects)
    origin = rects[:, :2].min(axis=0)
    extent = rects[:, 2:].max(axis=0) - origin
    scale = float(extent.max())
    if scale <= 0:
        raise ValueError('Degenerate geometry')
    centers = (rects[:, :2] + rects[:, 2:]) / 2
    y = np.column_stack(((centers - origin) / scale,
                         (rects[:, 2:] - rects[:, :2]) / scale))
    supervised = np.array([sid not in set(excluded_ids) for sid in ids])
    room_mask = supervised & np.array([s['level'] == 'room' for s in nodes])
    return dict(nodes=nodes, ids=ids, feature_names=feature_names, x=x, y=y,
                adjacency=normalized_adjacency(raw), raw_adjacency=raw,
                supervised_mask=supervised, room_mask=room_mask,
                internal_relations=internal, boundary_interfaces=interfaces,
                reference_frame=dict(origin_px=origin.tolist(), scale_px=scale,
                                     extent_normalized=(extent / scale).tolist()))


def indistinguishable_groups(x, adjacency):
    """Stable 1-WL classes: identical classes cannot be split by this GCN."""
    _, colors = np.unique(np.asarray(x), axis=0, return_inverse=True)
    neighbors = np.asarray(adjacency) > 0
    for _ in range(len(x)):
        signatures = [(int(colors[i]), tuple(sorted(colors[neighbors[i]].tolist())))
                      for i in range(len(x))]
        mapping = {sig: k for k, sig in enumerate(sorted(set(signatures)))}
        updated = np.array([mapping[sig] for sig in signatures])
        unchanged = np.array_equal(colors[:, None] == colors[None, :],
                                   updated[:, None] == updated[None, :])
        colors = updated
        if unchanged:
            break
    groups = defaultdict(list)
    for i, color in enumerate(colors):
        groups[int(color)].append(i)
    return [v for v in groups.values() if len(v) > 1]


def feature_mean_baseline(sample):
    """Best squared-error constant for each identical node-feature vector."""
    x, y, mask = sample['x'], sample['y'], sample['supervised_mask']
    prediction = np.tile(y[mask].mean(axis=0), (len(y), 1))
    for row in np.unique(x, axis=0):
        group = np.all(x == row, axis=1)
        observed = group & mask
        if observed.any():
            prediction[group] = y[observed].mean(axis=0)
    return prediction


def json_sample(sample):
    converted = {}
    for key, value in sample.items():
        converted[key] = value.tolist() if isinstance(value, np.ndarray) else value
    converted['input_whitelist'] = ['x: function type and level',
                                    'adjacency: supplied conceptual access graph']
    converted['target_columns'] = ['center_x', 'center_y', 'box_width', 'box_height']
    converted['reference_frame_role'] = 'labels and display only, never a model input'
    return converted
