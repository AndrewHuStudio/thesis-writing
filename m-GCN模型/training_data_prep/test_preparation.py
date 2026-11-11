"""Behavior tests for loss masking, boundary topology and coordinate integrity."""
import unittest

from shapely.geometry import box, Polygon, Point

try:
    from geometry import envelope, make_frame, normalize_points, denormalize_points
except ImportError:
    envelope = make_frame = normalize_points = denormalize_points = None
try:
    from export import convert_sample
except ImportError:
    convert_sample = None
try:
    from validate_dataset import assert_tensor_matches
except ImportError:
    assert_tensor_matches = None
try:
    from export import apply_training_scope
except ImportError:
    apply_training_scope = None


def space(sid, name, kind, bounds, level='room'):
    return {'id': sid, 'name': name, 'type': kind, 'level': level, 'scope': 'example',
            'polygon_px': list(box(*bounds).exterior.coords)[:-1]}


class PreparationTests(unittest.TestCase):
    def test_boundary_removes_internal_partition_without_filling_courtyard(self):
        self.assertIsNotNone(envelope, 'boundary implementation missing')
        rooms = [box(0, 0, 49, 100), box(51, 0, 100, 100)]
        result = envelope(rooms, box(30, 30, 70, 70), 2)
        self.assertAlmostEqual(result.area, 8400, places=5)
        self.assertFalse(result.covers(Point(50, 50)))
        self.assertTrue(result.covers(Point(50, 10)))

    def test_boundary_preserves_separate_wings(self):
        self.assertIsNotNone(envelope, 'boundary implementation missing')
        result = envelope([box(0, 0, 40, 100), box(80, 0, 120, 100)], None, 2)
        self.assertEqual(len(result.geoms), 2)
        self.assertFalse(result.covers(Point(60, 50)))

    def test_same_outer_shape_does_not_reveal_internal_subdivision(self):
        self.assertIsNotNone(envelope, 'boundary implementation missing')
        one = envelope([box(0, 0, 100, 100)], None, 2)
        two = envelope([box(0, 0, 49, 100), box(51, 0, 100, 100)], None, 2)
        self.assertLess(one.symmetric_difference(two).area, 1e-6)

    def test_isotropic_roundtrip_preserves_aspect_and_y_direction(self):
        self.assertIsNotNone(make_frame, 'coordinate implementation missing')
        frame = make_frame(box(10, 20, 110, 70))
        normalized = normalize_points([[10, 70], [110, 20]], frame)
        self.assertEqual(normalized, [[0, 0], [1, .5]])
        self.assertEqual(denormalize_points(normalized, frame), [[10, 70], [110, 20]])

    def sample(self):
        return {'image': {'file': 'example.jpg', 'width': 120, 'height': 120},
                'spaces': [space('S007', '名称未确认', 'unknown', (0, 0, 40, 100)),
                           space('S021', '诊室', 'consultation', (40, 0, 80, 100)),
                           space('S090', '候诊', 'hall', (80, 0, 100, 100), 'open_space')],
                'relations': [{'id': 'R005', 'source': 'S007', 'target': 'S021', 'type': 'access'}]}

    def record(self, reviewed=True):
        return {'domain': box(0, 0, 100, 100), 'boundary_reviewed': reviewed,
                'uncertain_space_ids': [], 'single_room_overrides': {}, 'masked_relation_ids': []}

    def test_unknown_function_keeps_geometry_but_masks_function(self):
        self.assertIsNotNone(convert_sample, 'export implementation missing')
        s = convert_sample(self.sample(), self.record(), ['unknown', 'consultation', 'hall'], ['room', 'open_space'])
        self.assertEqual(s['masks']['function'], [False, True, True])
        self.assertEqual(s['masks']['geometry'], [True, True, True])
        self.assertEqual(s['node_ids'], ['S007', 'S021', 'S090'])

    def test_targets_not_copied_into_default_inputs(self):
        self.assertIsNotNone(convert_sample, 'export implementation missing')
        s = convert_sample(self.sample(), self.record(), ['unknown', 'consultation', 'hall'], ['room', 'open_space'])
        self.assertNotIn('edge_index', s['inputs'])
        self.assertNotIn('boxes', s['inputs'])
        self.assertNotIn('polygons', s['inputs'])
        self.assertNotIn('area', s['inputs'])
        self.assertEqual(len(s['targets']['relations']), 1)
        self.assertEqual(s['targets']['relations'][0]['source_index'], 0)
        self.assertEqual(s['targets']['relations'][0]['target_index'], 1)

    def test_unrecorded_pairs_are_not_negative_labels(self):
        self.assertIsNotNone(convert_sample, 'export implementation missing')
        s = convert_sample(self.sample(), self.record(), ['unknown', 'consultation', 'hall'], ['room', 'open_space'])
        self.assertEqual(s['targets']['negative_relations'], [])
        self.assertEqual(len(s['targets']['relations']), 1)

    def test_unreviewed_boundary_disables_conditioned_supervision(self):
        self.assertIsNotNone(convert_sample, 'export implementation missing')
        s = convert_sample(self.sample(), self.record(False), ['unknown', 'consultation', 'hall'], ['room', 'open_space'])
        self.assertFalse(s['masks']['boundary_condition'])

    def test_courtyard_truth_is_not_default_input_condition(self):
        self.assertIsNotNone(convert_sample, 'export implementation missing')
        r = self.record()
        r['domain'] = box(0, 0, 100, 100).difference(box(45, 45, 55, 55))
        s = convert_sample(self.sample(), r, ['unknown', 'consultation', 'hall'], ['room', 'open_space'])
        self.assertEqual(s['inputs']['boundary'][0]['holes'], [])
        self.assertEqual(len(s['targets']['domain'][0]['holes']), 1)

    def test_landscape_is_context_and_not_indoor_layout_target(self):
        self.assertIsNotNone(convert_sample, 'export implementation missing')
        data = self.sample()
        data['spaces'].append(space('S099', '室外绿化', 'landscape', (105, 0, 115, 20), 'landscape'))
        s = convert_sample(data, self.record(), ['unknown', 'consultation', 'hall', 'landscape'], ['room', 'open_space', 'landscape'])
        self.assertIn('layout', s['masks'], 'indoor layout task mask missing')
        self.assertFalse(s['masks']['layout'][-1])
        self.assertTrue(s['masks']['geometry'][-1])

    def test_tensor_json_check_rejects_changed_box_value(self):
        self.assertIsNotNone(assert_tensor_matches, 'tensor parity validator missing')
        from build import to_arrays
        s = convert_sample(self.sample(), self.record(), ['unknown', 'consultation', 'hall'], ['room', 'open_space'])
        arrays = to_arrays(s)
        assert_tensor_matches(s, arrays)
        arrays['y_bbox'][0, 0] += .01
        with self.assertRaises(AssertionError):
            assert_tensor_matches(s, arrays)

    def test_scope_deletion_removes_incident_edges_without_bridging(self):
        self.assertIsNotNone(apply_training_scope, 'user scope adapter missing')
        data = self.sample()
        data['relations'].append({'id': 'R006', 'source': 'S021', 'target': 'S090', 'type': 'access'})
        modified = apply_training_scope(data, {'excluded_training_space_ids': ['S021']})
        self.assertEqual([s['id'] for s in modified['spaces']], ['S007', 'S090'])
        self.assertEqual(modified['relations'], [])
        self.assertEqual(len(data['spaces']), 3)

    def test_user_hall_confirmation_changes_only_explicit_training_fields(self):
        self.assertIsNotNone(apply_training_scope, 'user scope adapter missing')
        data = self.sample()
        modified = apply_training_scope(data, {'space_overrides': {'S007': {'name': '大厅局部', 'type': 'hall', 'level': 'open_space'}}})
        self.assertEqual(modified['spaces'][0]['type'], 'hall')
        self.assertEqual(modified['spaces'][0]['polygon_px'], data['spaces'][0]['polygon_px'])
        self.assertEqual(data['spaces'][0]['type'], 'unknown')


if __name__ == '__main__':
    unittest.main()
