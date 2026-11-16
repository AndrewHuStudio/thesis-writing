"""Checks for target isolation, slot equivariance, matching and boundary constraints."""
from pathlib import Path
import sys
import unittest

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from boundary_layout.data import prepare_inputs, prepare_layout, ProgramMeanBaseline
from boundary_layout.evaluation import score_layout
from boundary_layout.loss import constraint_terms, generate, supervised_loss
from boundary_layout.model import BoundaryLayoutModel, spatial_slots


def fixture():
    features = np.zeros((2, 50))
    features[:, [0, 43, 49]] = 1
    polygons = [[[.15, .15], [.35, .15], [.35, .35], [.15, .35]],
                [[.65, .65], [.85, .65], [.85, .85], [.65, .85]]]
    return {'plan_id': 'fixture', 'node_ids': ['A', 'B'],
            'inputs': {'node_features': features.tolist(),
                       'boundary': [{'outer': [[0, 0], [1, 0], [1, 1], [0, 1]]}]},
            'targets': {'boxes': [[.25, .25, .2, .2], [.75, .75, .2, .2]], 'polygons': polygons},
            'masks': {'layout': [True, True], 'function': [True, True], 'known_single_room': [True, True]},
            'metadata': [{'name': 'A'}, {'name': 'B'}], 'coordinate_frame': {}}


class LayoutChecks(unittest.TestCase):
    def test_targets_names_and_ids_do_not_enter_inputs(self):
        source = fixture()
        first = prepare_inputs(source)
        source['targets'] = {'boxes': [[999] * 4] * 2}
        source['node_ids'] = ['changed', 'also_changed']
        source['metadata'] = [{'name': 'changed'}] * 2
        second = prepare_inputs(source)
        for key in first:
            torch.testing.assert_close(first[key], second[key])

    def test_identical_input_slots_are_matched_for_supervision_and_evaluation(self):
        sample = prepare_layout(fixture())
        swapped = sample['target'].flip(0)
        self.assertAlmostEqual(float(supervised_loss(sample, swapped)), 0., places=6)
        scored = score_layout(sample, swapped)
        self.assertAlmostEqual(scored['metrics']['fine_rooms_box_iou'], 1., places=6)
        self.assertEqual(scored['prediction_index_for_reference'], [1, 0])

    def test_model_is_equivariant_given_permuted_slots(self):
        inputs = prepare_inputs(fixture())
        model = BoundaryLayoutModel(hidden=16)
        with torch.no_grad():
            model.output.weight.normal_(std=.02)
        anchors, noise = spatial_slots(inputs, torch.Generator().manual_seed(7))
        expected = model(inputs, anchors, noise)
        changed = dict(inputs, x=inputs['x'].flip(0))
        result = model(changed, anchors.flip(0), noise.flip(0))
        torch.testing.assert_close(expected.flip(0), result)
        bounds_min, bounds_max = expected[:, :2] - expected[:, 2:] / 2, expected[:, :2] + expected[:, 2:] / 2
        self.assertTrue((bounds_min >= 0).all() and (bounds_max <= inputs['extent']).all())

    def test_holes_and_overlapping_rooms_receive_positive_penalties(self):
        source = fixture()
        source['inputs']['boundary'][0]['holes'] = [[[.4, .4], [.6, .4], [.6, .6], [.4, .6]]]
        inputs = prepare_inputs(source)
        prediction = torch.tensor([[.5, .5, .1, .1], [.5, .5, .1, .1]], requires_grad=True)
        outside, overlap = constraint_terms(inputs, prediction)
        self.assertGreater(float(outside.detach()), 0)
        self.assertGreater(float(overlap.detach()), 0)
        (outside + overlap).backward()
        self.assertTrue(torch.isfinite(prediction.grad).all())

    def test_generation_works_with_inputs_only_and_fixed_seed(self):
        source = fixture()
        source.pop('targets')
        inputs = prepare_inputs(source)
        model = BoundaryLayoutModel(hidden=16)
        first, selection = generate(model, inputs, candidates=2)
        second, repeated = generate(model, inputs, candidates=2)
        torch.testing.assert_close(first, second)
        self.assertEqual(selection, repeated)
        self.assertFalse(selection['selection_uses_reference_layout'])

    def test_invalid_geometry_mask_is_respected(self):
        source = fixture()
        source['masks']['layout'][1] = False
        sample = prepare_layout(source)
        prediction = sample['target'].clone()
        prediction[1] = torch.tensor([.01, .01, .001, .001])
        self.assertAlmostEqual(float(supervised_loss(sample, prediction)), 0., places=6)
        baseline = ProgramMeanBaseline().fit([sample])
        self.assertTrue(torch.isfinite(baseline.predict(sample['inputs'])).all())


if __name__ == '__main__':
    torch.set_num_threads(2)
    unittest.main()
