"""Regression checks for input isolation, incomplete labels and graph symmetry."""
import importlib
import math
from pathlib import Path
import unittest

import numpy as np
import torch


class RelationChecks(unittest.TestCase):
    def api(self, name):
        path = Path(__file__).with_name(name + '.py')
        self.assertTrue(path.exists(), f'Missing relation-training module: {name}')
        return importlib.import_module(name)

    def example(self):
        features = np.zeros((4, 50)).tolist()
        for i in range(4):
            features[i][i] = 1.0
            features[i][43] = 1.0
            features[i][49] = 1.0
        return {
            'plan_id': 'fixture', 'node_ids': ['S1', 'S2', 'S3', 'S4'],
            'inputs': {'node_features': features, 'provided_constraint_edges': []},
            'targets': {'relations': [
                {'source_index': 0, 'target_index': 1, 'type': 'access', 'loss_mask': True},
                {'source_index': 1, 'target_index': 2, 'type': 'access', 'loss_mask': False},
                {'source_index': 2, 'target_index': 3, 'type': 'service', 'loss_mask': True}],
                'negative_relations': [{'source_index': 0, 'target_index': 3, 'type': 'access'}]}}

    def test_unknown_and_masked_pairs_remain_unlabeled(self):
        data = self.api('data')
        sample = data.prepare_sample(self.example())
        self.assertEqual(sample['positive_pairs'].tolist(), [[0, 1]])
        self.assertEqual(sample['negative_pairs'].tolist(), [[0, 3]])
        self.assertEqual(sample['pair_labels'].tolist(), [1, -1, 0, -1, -1, -1])

    def test_geometry_and_labels_do_not_enter_features(self):
        data = self.api('data')
        source = self.example()
        first = data.prepare_sample(source)['x'].clone()
        source['targets']['boxes'] = [[999] * 4] * 4
        source['targets']['relations'] = []
        second = data.prepare_sample(source)['x']
        torch.testing.assert_close(first, second)
        source['inputs']['node_features'][0][0] = float('nan')
        with self.assertRaises(ValueError):
            data.prepare_sample(source)

    def test_conflicting_labels_are_rejected(self):
        source = self.example()
        source['targets']['negative_relations'].append(
            {'source_index': 1, 'target_index': 0, 'type': 'access'})
        with self.assertRaises(ValueError):
            self.api('data').prepare_sample(source)

    def test_prediction_is_symmetric_and_permutation_equivariant(self):
        module = self.api('model')
        torch.manual_seed(7)
        model = module.SpaceRelationGCN(50, 16).eval()
        x = torch.tensor(self.example()['inputs']['node_features'])
        pairs = torch.tensor([[0, 1], [1, 0], [0, 2]])
        score = model.score_pairs(x, pairs)
        torch.testing.assert_close(score[0], score[1])
        order = torch.tensor([2, 0, 3, 1])
        inverse = torch.argsort(order)
        changed = model.score_pairs(x[order], inverse[pairs])
        torch.testing.assert_close(score, changed)
        x[2] = x[1]
        same = model.score_pairs(x, torch.tensor([[0, 1], [0, 2]]))
        torch.testing.assert_close(same[0], same[1])

    def test_pu_risk_and_gradients(self):
        module = self.api('model')
        positive = torch.zeros(4, requires_grad=True)
        population = torch.zeros(12, requires_grad=True)
        risk = module.pu_risk(positive, population, .2)
        self.assertAlmostEqual(float(risk.detach()), math.log(2), places=6)
        risk.backward()
        self.assertTrue(torch.isfinite(positive.grad).all())
        self.assertTrue(torch.isfinite(population.grad).all())
        clipped = module.pu_risk(torch.tensor([20.]), torch.tensor([-20.]), .2)
        self.assertGreaterEqual(float(clipped), 0)
        with self.assertRaises(ValueError):
            module.pu_risk(positive, population, 0)

    def test_tied_ranking_has_fractional_credit(self):
        metrics = self.api('metrics')
        result = metrics.budget_recall(np.ones(6), np.array([1, -1, 0, -1, -1, -1]), 1)
        self.assertAlmostEqual(result, 1 / 6)
        result = metrics.budget_recall(np.array([.8, .7, .6]), np.array([1, 1, -1]), 2)
        self.assertEqual(result, 1)


if __name__ == '__main__':
    torch.set_num_threads(2)
    unittest.main()
