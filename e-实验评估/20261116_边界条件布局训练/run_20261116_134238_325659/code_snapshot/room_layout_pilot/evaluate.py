"""Box-level diagnostics; no claim of door, polygon, or physical compliance."""
from itertools import combinations

import numpy as np


def boxes(values):
    return np.column_stack((values[:, :2] - values[:, 2:] / 2,
                            values[:, :2] + values[:, 2:] / 2))


def paired_iou(a, b):
    overlap = np.maximum(np.minimum(a[:, 2:], b[:, 2:]) -
                         np.maximum(a[:, :2], b[:, :2]), 0).prod(axis=1)
    area_a = np.maximum(a[:, 2:] - a[:, :2], 0).prod(axis=1)
    area_b = np.maximum(b[:, 2:] - b[:, :2], 0).prod(axis=1)
    return overlap / np.maximum(area_a + area_b - overlap, 1e-15)


def assignment(cost):
    """Square minimum-cost matching (Hungarian shortest augmenting paths)."""
    n = len(cost)
    u, v = np.zeros(n+1), np.zeros(n+1)
    p, way = np.zeros(n+1, dtype=int), np.zeros(n+1, dtype=int)
    for i in range(1, n+1):
        p[0] = i
        j0 = 0
        minimum = np.full(n+1, np.inf)
        used = np.zeros(n+1, dtype=bool)
        while True:
            used[j0] = True
            i0, delta, j1 = p[j0], np.inf, 0
            for j in range(1, n+1):
                if not used[j]:
                    current = cost[i0-1, j-1] - u[i0] - v[j]
                    if current < minimum[j]:
                        minimum[j], way[j] = current, j0
                    if minimum[j] < delta:
                        delta, j1 = minimum[j], j
            for j in range(n+1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minimum[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while j0:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
    match = np.empty(n, dtype=int)
    for j in range(1, n+1):
        match[p[j]-1] = j-1
    return match


def layout_metrics(sample, prediction):
    target = sample['y']
    mask, rooms = sample['supervised_mask'], sample['room_mask']
    scale = sample['reference_frame']['scale_px']
    a, b = boxes(prediction), boxes(target)
    difference = prediction[rooms] - target[rooms]
    distance = np.linalg.norm(difference[:, :2], axis=1)
    overlaps = []
    indices = np.flatnonzero(mask)
    for i, j in combinations(indices, 2):
        intersection = np.maximum(np.minimum(a[i, 2:], a[j, 2:]) -
                                  np.maximum(a[i, :2], a[j, :2]), 0).prod()
        if intersection * scale**2 > 1.0:
            overlaps.append([sample['ids'][i], sample['ids'][j],
                             float(intersection * scale**2)])
    extent = np.asarray(sample['reference_frame']['extent_normalized'])
    outside = np.any((a[:, :2] < -1e-6) | (a[:, 2:] > extent + 1e-6), axis=1)
    # Same-function swaps are also evaluated by minimum center-distance matching.
    remapped = prediction.copy()
    room_indices = np.flatnonzero(rooms)
    keys = {(sample['nodes'][i]['type'], sample['nodes'][i]['level'])
            for i in room_indices}
    for key in keys:
        group = [i for i in room_indices if
                 (sample['nodes'][i]['type'], sample['nodes'][i]['level']) == key]
        cost = np.linalg.norm(target[group, None, :2] - prediction[group][None, :, :2],
                              axis=2)
        remapped[group] = prediction[np.asarray(group)[assignment(cost)]]
    area = prediction[rooms, 2:].prod(axis=1)
    true_area = target[rooms, 2:].prod(axis=1)
    return dict(
        normalized_box_mse=float(np.mean((prediction[mask]-target[mask])**2)),
        room_center_mae_px=float(np.abs(difference[:, :2]).mean() * scale),
        room_center_distance_mean_px=float(distance.mean() * scale),
        room_center_distance_pct_long_side=float(distance.mean() * 100),
        room_size_mae_px=float(np.abs(difference[:, 2:]).mean() * scale),
        room_mean_box_iou=float(paired_iou(a[rooms], b[rooms]).mean()),
        room_matched_mean_box_iou=float(paired_iou(boxes(remapped)[rooms], b[rooms]).mean()),
        room_box_area_relative_error=float(np.mean(np.abs(area-true_area) / true_area)),
        overlap_pairs=len(overlaps), overlap_details_px2=overlaps,
        outside_reference_frame_nodes=[sample['ids'][i] for i in indices if outside[i]],
        evaluation_nodes=int(mask.sum()), room_evaluation_nodes=int(rooms.sum()),
        note='Same-graph box fitting; overlap includes circulation. Frame is not a building outline.')
