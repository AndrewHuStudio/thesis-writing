"""Regression checks for boundary geometry, room masks and candidate graph ties."""
from pathlib import Path
import sys
import unittest

import numpy as np
from shapely.geometry import Polygon, box

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from layout_evaluation.metrics import geometry_metrics, graph_metrics, overlap_metrics
from layout_evaluation.run import boundary_in_pilot_frame


class GeometryChecks(unittest.TestCase):
    def sample(self):
        return {'reference_frame': {'origin_px': [0, 0], 'scale_px': 1},
                'y': [[.25, .25, .5, .5], [.75, .25, .5, .5], [.5, .5, 1, 1]],
                'room_mask': [True, True, False],
                'nodes': [{'id': 'A', 'name': 'A', 'polygon_px': [[0, 0], [.5, 0], [.5, .5], [0, .5]]},
                          {'id': 'B', 'name': 'B', 'polygon_px': [[.5, 0], [1, 0], [1, .5], [.5, .5]]},
                          {'id': 'C', 'name': 'C', 'polygon_px': [[0, 0], [1, 0], [1, 1], [0, 1]]}]}

    def test_exact_rooms_exclude_coarse_containing_node(self):
        sample = self.sample()
        result = geometry_metrics(sample, sample['y'], box(0, 0, 1, 1))
        self.assertEqual(result['evaluation_rooms'], 2)
        self.assertEqual(result['mean_polygon_iou'], 1.)
        self.assertEqual(result['room_overlap_pair_count'], 0)
        self.assertEqual(result['mean_polygon_area_relative_error'], 0)

    def test_collapsed_rooms_and_real_boundary_holes_are_detected(self):
        sample = self.sample()
        prediction = np.array(sample['y'])
        prediction[1] = prediction[0]
        boundary = Polygon([[0, 0], [1, 0], [1, 1], [0, 1]],
                           holes=[[[.1, .1], [.2, .1], [.2, .2], [.1, .2]]])
        result = geometry_metrics(sample, prediction, boundary)
        self.assertEqual(result['room_overlap_pair_count'], 1)
        self.assertAlmostEqual(result['room_overlap_area_fraction'], 1.)
        self.assertGreater(result['outside_building_area_fraction'], 0)

    def test_three_way_overlap_is_counted_by_area_once(self):
        result = overlap_metrics(['A', 'B', 'C'], [box(0, 0, 1, 1)] * 3)
        self.assertEqual(result['pair_count'], 3)
        self.assertEqual(result['overlap_area_fraction_of_union'], 1.)

    def test_nonfinite_and_negative_size_predictions_are_rejected(self):
        sample = self.sample()
        for invalid in (float('nan'), -1.):
            prediction = np.array(sample['y'])
            prediction[0, 2] = invalid
            with self.assertRaises(ValueError):
                geometry_metrics(sample, prediction, box(0, 0, 1, 1))

    def test_current_y_up_boundary_is_mapped_to_saved_y_down_coordinates(self):
        source = {'inputs': {'boundary': [{'outer': [[0, 0], [.2, 0], [.2, .3], [0, .3]]}]},
                  'coordinate_frame': {'origin_px': [10, 20], 'long_side_px': 10}}
        domain = boundary_in_pilot_frame(source, {'origin_px': [0, 0], 'scale_px': 10})
        np.testing.assert_allclose(domain.bounds, [1, 1.7, 1.2, 2])


class GraphChecks(unittest.TestCase):
    def test_isolated_nodes_are_included(self):
        result = graph_metrics([.9, .8, .7], [[0, 1], [1, 2], [0, 2]], 4)
        self.assertEqual(result['metrics']['component_count']['mean'], 2.)
        self.assertEqual(result['metrics']['isolated_node_fraction']['mean'], .25)
        self.assertFalse(result['physical_route_assessment_available'])

    def test_tie_trials_are_reproducible(self):
        pairs = np.array([[i, j] for i in range(5) for j in range(i + 1, 5)])
        first = graph_metrics(np.ones(10), pairs, 5)
        second = graph_metrics(np.ones(10), pairs, 5)
        self.assertEqual(first, second)
        self.assertEqual(first['ties_at_cutoff'], 10)

    def test_duplicate_candidate_pairs_are_rejected(self):
        with self.assertRaises(ValueError):
            graph_metrics([.9, .8], [[0, 1], [1, 0]], 3)


if __name__ == '__main__':
    unittest.main()
