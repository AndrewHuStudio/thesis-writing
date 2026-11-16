"""Checks for source leakage, fixed budgets and reusable MLP training."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import torch

from benchmark_groups import partitions, source_audit
from benchmark_metrics import aggregate, sample_metrics
from benchmark_models import ObservedDensity, PairMLP
from data import prepare_sample
from model import graph_loss
import test_relations


class BenchmarkChecks(unittest.TestCase):
    def sample(self, plan='01_A医院门诊楼'):
        source = test_relations.RelationChecks().example()
        source['plan_id'] = plan
        return prepare_sample(source)

    def test_source_partitions_keep_hospital_groups_together(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plans = ['01_A医院门诊楼', '02_A医院住院楼', '03_B医院', '04_C医院', '05_D医院']
            samples, entries = [], []
            for index, plan in enumerate(plans):
                sample = self.sample(plan)
                samples.append(sample)
                source = test_relations.RelationChecks().example()
                source.update({'plan_id': plan, 'provenance': {
                    'source_annotation': f'{index}/annotation.json',
                    'source_image_sha256': str(index)},
                    'metadata': [{'scope_original': 'ordinary_outpatient'}] * 4})
                path = f'{index}.json'
                (root / path).write_text(json.dumps(source), encoding='utf-8')
                entries.append({'plan_id': plan, 'sample': path})
            (root / 'manifest.json').write_text(json.dumps({'plans': entries}), encoding='utf-8')
            audit = source_audit(root, samples, folds=3)
            self.assertEqual(len(audit['groups']), 4)
            by_plan = {row['plan_id']: row for row in audit['plans']}
            self.assertEqual(by_plan[plans[0]]['fold'], by_plan[plans[1]]['fold'])
            for fold in range(3):
                split = partitions(samples, audit, fold)
                roles = {s['plan_id']: role for role, rows in split.items() for s in rows}
                self.assertEqual(roles[plans[0]], roles[plans[1]])
                self.assertEqual(set(roles), set(plans))

    def test_density_predictions_are_independent_of_heldout_labels(self):
        train = self.sample()
        heldout = self.sample('02_B医院')
        model = ObservedDensity().fit([train])
        expected = model.predict(heldout)
        heldout['positive_pairs'] = torch.tensor([[0, 2], [0, 3]])
        heldout['pair_labels'][:] = 1
        np.testing.assert_array_equal(expected, model.predict(heldout))

    def test_density_unseen_feature_pairs_use_training_fallback(self):
        train = self.sample()
        heldout = deepcopy(train)
        heldout['x'] = torch.roll(heldout['x'], shifts=10, dims=1)
        density = ObservedDensity().fit([train])
        np.testing.assert_allclose(density.predict(heldout), np.full(6, 1 / 6))

    def test_fixed_budget_uses_node_count_and_fractional_ties(self):
        sample = self.sample()
        row = sample_metrics(sample, np.ones(6), 'group')
        self.assertAlmostEqual(row['recall_at_n'], 4 / 6)
        self.assertAlmostEqual(row['recall_at_observed_positive_budget'], 1 / 6)
        self.assertEqual(row['unlabeled_pairs'], 4)

    def test_aggregation_weights_source_groups_equally(self):
        sample = self.sample()
        first = sample_metrics(sample, np.ones(6), 'one')
        second = dict(first, plan_id='second', group_id='two', recall_at_n=1.)
        third = dict(second, plan_id='third')
        summary = aggregate([first, second, third])
        self.assertAlmostEqual(summary['group_macro_recall_at_n'], (4 / 6 + 1) / 2)
        self.assertEqual(summary['source_groups'], 2)

    def test_mlp_preserves_symmetry_and_supports_pu_backpropagation(self):
        sample = self.sample()
        model = PairMLP(hidden=16)
        pairs = torch.tensor([[0, 1], [1, 0]])
        scores = model.score_pairs(sample['x'], pairs)
        torch.testing.assert_close(scores[0], scores[1])
        loss = graph_loss(model, sample, sample['all_pairs'], 2.)
        loss.backward()
        self.assertTrue(all(parameter.grad is not None for parameter in model.parameters()))
        self.assertTrue(all(torch.isfinite(parameter.grad).all() for parameter in model.parameters()))


if __name__ == '__main__':
    torch.set_num_threads(2)
    unittest.main()
