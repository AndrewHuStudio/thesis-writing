"""Audit source groups and create reproducible provisional evaluation folds."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import random
import re


def write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2,
                                   allow_nan=False) + '\n', encoding='utf-8')
    temporary.replace(path)


def source_audit(directory, samples, folds=5, seed=20261116):
    directory = Path(directory)
    manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
    entries = {entry['plan_id']: entry for entry in manifest['plans']}
    parent = {sample['plan_id']: sample['plan_id'] for sample in samples}

    def find(plan):
        while parent[plan] != plan:
            parent[plan] = parent[parent[plan]]
            plan = parent[plan]
        return plan

    def merge(left, right):
        parent[find(right)] = find(left)

    matches, evidence, records = {}, [], []
    scopes = defaultdict(lambda: {'nodes': 0, 'plans': set()})
    total_nodes, duplicate_nodes = 0, 0
    for sample in samples:
        plan = sample['plan_id']
        source = json.loads((directory / entries[plan]['sample']).read_text(encoding='utf-8'))
        provenance = source['provenance']
        title = plan.split('_', 1)[1]
        hospital_match = re.match(r'(.+?(?:医院|医疗中心|卫生院))', title)
        hospital = hospital_match.group(1) if hospital_match else title
        identifiers = [('hospital_title', hospital)]
        for field in ('source_image_sha256', 'source_annotation_sha256'):
            if provenance.get(field):
                identifiers.append((field, provenance[field]))
        for kind, value in identifiers:
            key = (kind, value)
            if key in matches:
                merge(matches[key], plan)
                evidence.append({'left': matches[key], 'right': plan,
                                 'basis': kind, 'value': value})
            matches[key] = plan
        counts = Counter(tuple(row) for row in source['inputs']['node_features'])
        duplicates = sum(count for count in counts.values() if count > 1)
        total_nodes += len(source['node_ids'])
        duplicate_nodes += duplicates
        for metadata in source['metadata']:
            scope = metadata.get('scope_original', '')
            scopes[scope]['nodes'] += 1
            scopes[scope]['plans'].add(plan)
        records.append({'plan_id': plan, 'hospital_title_candidate': hospital,
                        'nodes': len(source['node_ids']),
                        'unique_feature_patterns': len(counts),
                        'nodes_with_duplicate_features': duplicates,
                        'source_annotation': provenance['source_annotation'],
                        'source_image_sha256': provenance.get('source_image_sha256'),
                        'known_positive_pairs': len(sample['positive_pairs']),
                        'confirmed_negative_pairs': len(sample['negative_pairs'])})
    members = defaultdict(list)
    for row in records:
        members[find(row['plan_id'])].append(row['plan_id'])
    groups = []
    sizes = {row['plan_id']: row['nodes'] for row in records}
    for plans in members.values():
        plans.sort()
        groups.append({'group_id': 'source_' + '_'.join(p.split('_', 1)[0] for p in plans),
                       'plans': plans, 'nodes': sum(sizes[p] for p in plans),
                       'review_status': 'provisional_title_and_exact_source_hash_audit'})
    if folds < 3 or len(groups) < folds:
        raise ValueError('Need at least three folds and at least one source group per fold')
    random.Random(seed).shuffle(groups)
    groups.sort(key=lambda row: row['nodes'], reverse=True)
    loads = [0] * folds
    for group in groups:
        fold = min(range(folds), key=lambda i: (loads[i], i))
        group['fold'] = fold
        loads[fold] += group['nodes']
    groups.sort(key=lambda row: row['group_id'])
    lookup = {plan: group for group in groups for plan in group['plans']}
    for row in records:
        row['group_id'] = lookup[row['plan_id']]['group_id']
        row['fold'] = lookup[row['plan_id']]['fold']
    scope_rows = []
    for value, counts in sorted(scopes.items()):
        scope_rows.append({'scope_original': value, 'nodes': counts['nodes'],
                           'plans': sorted(counts['plans']),
                           'contains_uncertainty_marker': bool(re.search(
                               r'unknown|unconfirmed|undetermined|unclassified|未知|待核', value)),
                           'input_use': 'auxiliary_target_candidate_only'})
    return {'grouping_status': 'provisional_requires_source_identity_review',
            'split_seed': seed, 'fold_count': folds, 'plans': records,
            'groups': groups, 'merge_evidence': evidence, 'fold_node_counts': loads,
            'node_count': total_nodes, 'duplicate_feature_node_count': duplicate_nodes,
            'duplicate_feature_node_fraction': duplicate_nodes / total_nodes,
            'scope_vocabulary_count': len(scope_rows), 'scope_inventory': scope_rows,
            'user_inference_conditions': ['building_boundary', 'space_program'],
            'scope_is_confirmed_inference_input': False}


def partitions(samples, audit, test_fold):
    count = audit['fold_count']
    if not 0 <= test_fold < count:
        raise ValueError('Invalid test fold')
    validation_fold = (test_fold + 1) % count
    by_plan = {row['plan_id']: row for row in audit['plans']}
    result = {'train': [], 'validation': [], 'test': []}
    for sample in samples:
        fold = by_plan[sample['plan_id']]['fold']
        role = 'train'
        if fold == test_fold:
            role = 'test'
        elif fold == validation_fold:
            role = 'validation'
        result[role].append(sample)
    group_sets = [{by_plan[s['plan_id']]['group_id'] for s in result[role]}
                  for role in ('train', 'validation', 'test')]
    if any(group_sets[i] & group_sets[j] for i in range(3) for j in range(i + 1, 3)):
        raise ValueError('Source group overlaps evaluation partitions')
    return result


def audit_digest(audit):
    return hashlib.sha256(json.dumps(audit, sort_keys=True).encode('utf-8')).hexdigest()
