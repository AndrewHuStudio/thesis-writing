"""Tests for leakage, graph equivariance, geometry, and analytical gradients."""
import copy
import unittest

import numpy as np

try:
    from data import build_sample, indistinguishable_groups
    from model import GraphRegressor
    from evaluate import layout_metrics
except ImportError:
    build_sample = indistinguishable_groups = GraphRegressor = layout_metrics = None


def fixture():
    spaces = []
    for sid, name, typ, x in [
        ('A', '北侧诊室', 'consultation', 10),
        ('B', '南侧诊室', 'consultation', 30),
        ('C', '通道', 'corridor', 0),
    ]:
        spaces.append(dict(id=sid, name=name, type=typ,
                           level='room' if sid != 'C' else 'open_space',
                           scope='unit', area_ratio=1 / 3,
                           polygon_px=[[x, 0], [x+10, 0], [x+10, 10], [x, 10]]))
    return dict(image=dict(file='source.jpg', width=100, height=100),
                spaces=spaces,
                relations=[dict(id='R1', source='A', target='C', type='access'),
                           dict(id='R2', source='B', target='C', type='access')])


class PilotTests(unittest.TestCase):
    def test_features_ignore_geometry_area_and_names(self):
        self.assertIsNotNone(build_sample, 'Data adapter is not implemented')
        first = fixture()
        second = copy.deepcopy(first)
        for s in second['spaces']:
            s['name'] = '答案方位不得入模'
            s['area_ratio'] = 0.91
            s['polygon_px'] = [[2*x+9, 2*y+17] for x, y in s['polygon_px']]
        a, b = build_sample(first, 'unit'), build_sample(second, 'unit')
        np.testing.assert_array_equal(a['x'], b['x'])
        np.testing.assert_array_equal(a['adjacency'], b['adjacency'])
        np.testing.assert_allclose(a['y'], b['y'], atol=1e-12)

    def test_combined_node_is_context_only(self):
        self.assertIsNotNone(build_sample, 'Data adapter is not implemented')
        sample = build_sample(fixture(), 'unit', excluded_ids={'B'})
        self.assertEqual(sample['supervised_mask'].tolist(), [True, False, True])
        self.assertEqual(sample['room_mask'].tolist(), [True, False, False])

    def test_symmetric_rooms_are_reported(self):
        self.assertIsNotNone(indistinguishable_groups, 'Symmetry audit is missing')
        sample = build_sample(fixture(), 'unit')
        groups = indistinguishable_groups(sample['x'], sample['adjacency'])
        self.assertIn([0, 1], groups)

    def test_gcn_forward_is_permutation_equivariant(self):
        self.assertIsNotNone(GraphRegressor, 'GCN is not implemented')
        sample = build_sample(fixture(), 'unit')
        model = GraphRegressor(sample['x'].shape[1], seed=3, hidden=(7, 5))
        perm = np.array([2, 0, 1])
        original = model.forward(sample['x'], sample['adjacency'])
        shuffled = model.forward(sample['x'][perm], sample['adjacency'][perm][:, perm])
        np.testing.assert_allclose(original[perm], shuffled, atol=1e-12)
        np.testing.assert_allclose(original[0], original[1], atol=1e-12)

    def test_gradients_match_finite_differences(self):
        self.assertIsNotNone(GraphRegressor, 'GCN is not implemented')
        sample = build_sample(fixture(), 'unit')
        model = GraphRegressor(sample['x'].shape[1], seed=8, hidden=(5, 4))
        loss, grads = model.loss_and_grad(sample['x'], sample['adjacency'],
                                         sample['y'], sample['supervised_mask'])
        self.assertTrue(np.isfinite(loss))
        rng = np.random.default_rng(9)
        for key, param in model.params.items():
            for _ in range(3):
                index = tuple(rng.integers(n) for n in param.shape)
                old = param[index]
                param[index] = old + 1e-5
                plus = model.loss_and_grad(sample['x'], sample['adjacency'],
                                           sample['y'], sample['supervised_mask'])[0]
                param[index] = old - 1e-5
                minus = model.loss_and_grad(sample['x'], sample['adjacency'],
                                            sample['y'], sample['supervised_mask'])[0]
                param[index] = old
                self.assertAlmostEqual(grads[key][index], (plus-minus)/2e-5,
                                       delta=2e-7, msg=key)

    def test_metrics_catch_collapsed_rooms(self):
        self.assertIsNotNone(layout_metrics, 'Layout metrics are missing')
        sample = build_sample(fixture(), 'unit')
        exact = layout_metrics(sample, sample['y'])
        bad = sample['y'].copy()
        bad[1] = bad[0]
        collapsed = layout_metrics(sample, bad)
        self.assertAlmostEqual(exact['room_mean_box_iou'], 1.0)
        self.assertEqual(exact['overlap_pairs'], 0)
        self.assertGreater(collapsed['overlap_pairs'], 0)
        self.assertGreater(collapsed['room_center_mae_px'], 0)

    def test_matching_does_not_penalize_identical_type_instance_swaps(self):
        self.assertIsNotNone(layout_metrics, 'Layout metrics are missing')
        sample = build_sample(fixture(), 'unit')
        swapped = sample['y'].copy()
        swapped[[0, 1]] = swapped[[1, 0]]
        metrics = layout_metrics(sample, swapped)
        self.assertAlmostEqual(metrics['room_mean_box_iou'], 0.0)
        self.assertAlmostEqual(metrics['room_matched_mean_box_iou'], 1.0)

    def test_training_reduces_a_real_box_loss(self):
        self.assertIsNotNone(GraphRegressor, 'GCN is not implemented')
        from model import train
        sample = build_sample(fixture(), 'unit')
        result = train(sample, seed=11, epochs=250)
        self.assertLess(result['best_train_mse'], result['history'][0]['normalized_box_mse']/2)


if __name__ == '__main__':
    unittest.main()
