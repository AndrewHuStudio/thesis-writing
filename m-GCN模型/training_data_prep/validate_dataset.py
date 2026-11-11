"""Validate source integrity, masks, normalized tensors and review provenance."""
from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np
from shapely.geometry import Polygon
from shapely.ops import unary_union

from build import ROOT, AUDIT, OUT, digest, save, to_arrays
from geometry import domain_from_rings, denormalize_points
from export import apply_training_scope


def assert_tensor_matches(sample, arrays):
    expected = to_arrays(sample)
    assert set(expected) == set(arrays), 'Tensor field set differs from JSON contract'
    for name, value in expected.items():
        np.testing.assert_array_equal(arrays[name], value, err_msg='Tensor/JSON mismatch: '+name)


def validate():
    manifest = json.loads((OUT/'manifest.json').read_text())
    vocab = json.loads((OUT/'vocabulary.json').read_text())
    controls = json.loads((OUT/'boundary_controls.json').read_text())
    expected = json.loads((AUDIT/'原文件哈希_检查前.json').read_text())
    changed = [p for p, h in expected.items() if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h]
    assert not changed, changed
    assert len(manifest['plans'])==53
    counts = Counter()
    errors, roundtrip = [], 0.0
    for entry in manifest['plans']:
        plan = entry['plan_id']
        try:
            sample=json.loads((OUT/entry['sample']).read_text())
            br=json.loads((OUT/entry['boundary_record']).read_text())
            original=json.loads((ROOT/sample['provenance']['source_annotation']).read_text())
            source=apply_training_scope(original,br)
            tensor=dict(np.load(OUT/entry['tensor'],allow_pickle=False))
            assert_tensor_matches(sample, tensor)
            n=len(sample['node_ids'])
            assert sample['node_ids']==[s['id'] for s in source['spaces']]
            assert tensor['node_ids'].tolist()==sample['node_ids']
            assert tensor['x'].shape==(n,len(vocab['node_feature_order']))
            assert tensor['y_bbox'].shape==(n,4)
            assert all(np.isfinite(v).all() for v in tensor.values() if np.issubdtype(v.dtype,np.number))
            assert 'edge_index' not in sample['inputs'] and 'edge_index' not in tensor
            assert sample['inputs']['provided_constraint_edges']==[]
            assert all(not p['holes'] for p in sample['inputs']['boundary'])
            assert not sample['masks']['full_domain_partition']
            assert not tensor['full_domain_partition_mask']
            assert set(sample['inputs'])=={'node_features','boundary','provided_constraint_edges','metric_scale_known'}
            assert br['boundary_reviewed'] and br['review_evidence']['method']=='assistant_visual_source_overlay_review'
            assert controls[plan[:2]]['reviewed_shape_sha256']==digest(br['outer_shells_and_holes_px'])
            assert br['geometry_sha256']==sample['provenance']['boundary_geometry_sha256']
            evidence=sample['provenance'].get('review_evidence_snapshot')
            if evidence:
                snapshot=OUT/evidence['file']
                assert hashlib.sha256(snapshot.read_bytes()).hexdigest()==evidence['sha256']
            feedback=sample['provenance'].get('user_feedback')
            if feedback:
                assert hashlib.sha256((OUT/feedback['file']).read_bytes()).hexdigest()==feedback['sha256']
            assert bool(tensor['boundary_condition_mask'])==entry['boundary_condition_eligible']
            domain=domain_from_rings(br['outer_shells_and_holes_px'])
            assert domain.is_valid and domain.area>0
            assert br['uncovered_indoor_area_fraction']<1e-8
            for s in br['explicit_exclusions_px']:
                assert domain.intersection(Polygon(s['polygon_px'])).area<1e-6
            frame=sample['coordinate_frame']
            for i,s in enumerate(source['spaces']):
                assert sample['metadata'][i]['name']==s['name']
                assert sample['metadata'][i]['type']==s['type']
                assert tensor['y_type'][i]==vocab['types'].index(s['type'])
                if s['type']=='unknown':assert not tensor['function_mask'][i]
                if s['id'] in br['uncertain_space_ids']:assert not tensor['geometry_mask'][i]
                if s['type'] in ['landscape','courtyard'] or s['level']=='landscape':assert not tensor['layout_mask'][i]
                restored=np.asarray(denormalize_points(sample['targets']['polygons'][i],frame))
                roundtrip=max(roundtrip,float(np.max(np.abs(restored-np.asarray(s['polygon_px'])))))
                bounds=Polygon(s['polygon_px']).bounds
                center=denormalize_points([sample['targets']['boxes'][i][:2]],frame)[0]
                np.testing.assert_allclose(center,[(bounds[0]+bounds[2])/2,(bounds[1]+bounds[3])/2],atol=1e-9,rtol=0)
                a,b=tensor['y_polygon_offsets'][i:i+2]
                np.testing.assert_allclose(tensor['y_polygon_vertices'][a:b],sample['targets']['polygons'][i],atol=0,rtol=0)
            r=sample['targets']['relations']
            assert len(r)==len([x for x in source['relations'] if x['type']!='entrance'])
            assert tensor['relation_label_index'].shape==(2,len(r))
            assert (tensor['relation_label_index']>=0).all() and (tensor['relation_label_index']<n).all()
            positive_access={frozenset([x['source_index'],x['target_index']]) for x in r if x['type']=='access'}
            for negative in sample['targets']['negative_relations']:
                assert frozenset([negative['source_index'],negative['target_index']]) not in positive_access
            assert all(not op['position_loss_mask'] for x in r for op in x['openings'])
            assert not tensor['entrance_position_loss_mask'].any()
            counts['plans']+=1;counts['nodes']+=n
            counts['boundary_condition_plans']+=entry['boundary_condition_eligible']
            counts['geometry_available']+=int(tensor['geometry_mask'].sum())
            counts['layout_nodes']+=int(tensor['layout_mask'].sum())
            counts['function_known']+=int(tensor['function_mask'].sum())
            counts['known_single_rooms']+=int(tensor['known_single_room_mask'].sum())
            counts['relation_targets']+=len(r)
            counts['relation_targets_masked']+=int((~tensor['relation_loss_mask']).sum())
            counts['entrance_targets']+=len(sample['targets']['entrances'])
            counts['confirmed_negative_access']+=len(sample['targets']['negative_relations'])
            counts['auxiliary_regions']+=len(sample['targets']['regions'])
            assert all(set(region['member_space_ids'])<=set(sample['node_ids']) for region in sample['targets']['regions'])
            if entry['boundary_condition_eligible']:
                counts['boundary_condition_layout_nodes']+=int(tensor['layout_mask'].sum())
        except Exception as error:
            errors.append({'plan':plan,'error':str(error)})
    partial=[e['plan_id'][:2] for e in manifest['plans'] if not e['boundary_condition_eligible']]
    result={'valid':not errors,'counts':dict(counts),'errors':errors,'source_files_unchanged':len(expected),
            'coordinate_roundtrip_max_error_px':roundtrip,
            'all_53_split':'train','test_split':None,
            'precision':'reviewed_conceptual_outer_envelopes_not_surveyed_walls',
            'partial_boundary_condition_masked':partial}
    save(OUT/'validation_report.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    assert not errors, 'Dataset validation failed'
    assert counts['nodes']==sum(e['nodes'] for e in manifest['plans']) and counts['plans']==53
    assert roundtrip<1e-8
    return result


if __name__=='__main__':validate()
