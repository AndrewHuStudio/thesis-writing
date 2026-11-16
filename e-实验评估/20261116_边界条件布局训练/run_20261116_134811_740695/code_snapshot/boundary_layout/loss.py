"""Input-class matching, level-balanced geometry supervision and soft constraints."""
import numpy as np
from scipy.optimize import linear_sum_assignment
import torch
from torch.nn import functional as functional

from boundary_layout.model import spatial_slots


def matching_indices(sample, prediction):
    proposed = prediction.detach().cpu().numpy()
    target = sample['target'].detach().cpu().numpy()
    permutation = np.arange(len(target))
    weights = np.asarray([1., 1., .5, .5])
    for group in sample['match_groups']:
        indexes = np.asarray(group)
        cost = (np.abs(target[indexes, None, :] - proposed[indexes][None, :, :]) * weights).mean(axis=2)
        rows, columns = linear_sum_assignment(cost)
        permutation[indexes[rows]] = indexes[columns]
    return torch.tensor(permutation, dtype=torch.long, device=prediction.device)


def supervised_loss(sample, prediction):
    permutation = matching_indices(sample, prediction)
    aligned = prediction[permutation]
    values = []
    for group in sample['level_groups']:
        target, predicted = sample['target'][group], aligned[group]
        coordinate = functional.smooth_l1_loss(predicted, target, beta=.05)
        target_area = target[:, 2:].prod(dim=1).clamp_min(1e-8)
        predicted_area = predicted[:, 2:].prod(dim=1).clamp_min(1e-8)
        area = (predicted_area.log() - target_area.log()).abs().mean()
        values.append(coordinate + .02 * area)
    return torch.stack(values).mean()


def constraint_terms(inputs, prediction):
    offsets = prediction.new_tensor([[-.5, -.5], [0, -.5], [.5, -.5],
                                     [-.5, 0], [0, 0], [.5, 0],
                                     [-.5, .5], [0, .5], [.5, .5]])
    points = prediction[:, None, :2] + offsets[None, :, :] * prediction[:, None, 2:]
    field = inputs['distance_field'][0, 0]
    height, width = field.shape
    coordinates = points / inputs['extent'] * prediction.new_tensor([width, height]) - .5
    x = coordinates[..., 0].clamp(0, width - 1)
    y = coordinates[..., 1].clamp(0, height - 1)
    x0, y0 = x.floor().long(), y.floor().long()
    x1, y1 = (x0 + 1).clamp_max(width - 1), (y0 + 1).clamp_max(height - 1)
    fraction_x, fraction_y = x - x0, y - y0
    distances = ((1 - fraction_x) * (1 - fraction_y) * field[y0, x0] +
                 fraction_x * (1 - fraction_y) * field[y0, x1] +
                 (1 - fraction_x) * fraction_y * field[y1, x0] +
                 fraction_x * fraction_y * field[y1, x1])
    outside = distances.relu().mean()
    rooms = prediction[inputs['room_constraint_mask']]
    if len(rooms) < 2:
        return outside, prediction.sum() * 0
    minimum, maximum = rooms[:, :2] - rooms[:, 2:] / 2, rooms[:, :2] + rooms[:, 2:] / 2
    overlap = (torch.minimum(maximum[:, None], maximum[None, :]) -
               torch.maximum(minimum[:, None], minimum[None, :])).clamp_min(0).prod(dim=2)
    overlap = torch.triu(overlap, diagonal=1).sum() / rooms[:, 2:].prod(dim=1).sum().clamp_min(1e-8)
    return outside, overlap


def objective(sample, prediction, outside_weight=2., overlap_weight=.05):
    outside, overlap = constraint_terms(sample['inputs'], prediction)
    return supervised_loss(sample, prediction) + outside_weight * outside + overlap_weight * overlap


@torch.no_grad()
def generate(model, inputs, candidates=4, seed=10000):
    if candidates < 1:
        raise ValueError('Candidate count must be positive')
    model.eval()
    best = None
    scores = []
    for index in range(candidates):
        generator = torch.Generator(device=inputs['x'].device).manual_seed(seed + index)
        anchors, noise = spatial_slots(inputs, generator)
        prediction = model(inputs, anchors, noise)
        outside, overlap = constraint_terms(inputs, prediction)
        score = float(2 * outside + .05 * overlap)
        scores.append(score)
        if best is None or score < best[0]:
            best = (score, prediction, index)
    return best[1], {'candidates': candidates, 'seed': seed,
                     'selected_candidate': best[2], 'constraint_scores': scores,
                     'selection_uses_reference_layout': False}
