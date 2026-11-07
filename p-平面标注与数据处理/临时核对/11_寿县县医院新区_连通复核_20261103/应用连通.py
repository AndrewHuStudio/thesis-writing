from pathlib import Path
from collections import Counter, defaultdict
import json
import importlib.util

from shapely.geometry import Point, Polygon

WORK = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('readings', WORK / '连通判读.py')
readings = importlib.util.module_from_spec(spec)
spec.loader.exec_module(readings)
data = json.loads((WORK / '已同步房名.json').read_text())
spaces = {s['id']: s for s in data['spaces']}
# Include the visible continuous forecourt south of the west elevator lobby.
spaces['S014']['polygon_px'] = [[338, 486], [886, 486], [886, 456], [1090, 456], [1090, 526], [338, 526]]
relations = [r for r in data['relations'] if r['id'] not in readings.REMOVE]
lookup = {r['id']: r for r in relations}
lookup['E06']['position_px'] = [338, 325]
lookup['E07']['position_px'] = [2104, 325]
opening_counter = 0


def openings(relation, coordinates, kind='door'):
    global opening_counter
    for x, y in coordinates:
        opening_counter += 1
        relation.setdefault('openings', []).append({
            'id': f'P{opening_counter:03}', 'kind': kind, 'position_px': [x, y],
        })


for line in readings.OPENING_READINGS.splitlines():
    tokens = line.split()
    if not tokens:
        continue
    rid = f'R{int(tokens[0]):03}'
    kind = 'open_passage' if tokens[-1] == 'o' else 'door'
    nums = list(map(int, tokens[1:-1] if kind == 'open_passage' else tokens[1:]))
    assert len(nums) % 2 == 0 and lookup[rid]['type'] == 'access'
    openings(lookup[rid], list(zip(nums[::2], nums[1::2])), kind)

rid_counter = max(int(r['id'][1:]) for r in data['relations'] if r['id'].startswith('R'))
added = []
for source, target, coordinates in readings.EXTRA:
    rid_counter += 1
    relation = {'id': f'R{rid_counter:03}', 'source': source, 'target': target, 'type': 'access'}
    assert not any(r['type'] == 'access' and {r['source'], r['target']} == {source, target} for r in relations)
    openings(relation, coordinates)
    relations.append(relation)
    lookup[relation['id']] = relation
    added.append(relation)

# The left face of the long registration counter is a service interface.
rid_counter += 1
relations.append({'id': f'R{rid_counter:03}', 'source': 'S091', 'target': 'S195', 'type': 'service'})
eid_counter = max(int(r['id'][1:]) for r in relations if r['type'] == 'entrance')
for name, kind, target, position in readings.NEW_ENTRANCES:
    eid_counter += 1
    relations.append({'id': f'E{eid_counter:02}', 'source': None, 'target': target, 'type': 'entrance', 'name': name, 'entrance_type': kind, 'position_px': list(position)})

denominator = sum(Polygon(s['polygon_px']).area for s in data['spaces'] if s['type'] not in {'courtyard', 'landscape'})
for s in data['spaces']:
    if s['type'] not in {'courtyard', 'landscape'}:
        s['area_ratio'] = round(Polygon(s['polygon_px']).area / denominator, 8)
data['relations'] = relations
(WORK / '连通复核后.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')

distances = []
for relation in relations:
    for opening in relation.get('openings', []):
        point = Point(opening['position_px'])
        ds = [round(Polygon(spaces[relation[key]]['polygon_px']).boundary.distance(point), 2) for key in ['source', 'target']]
        if max(ds) > 6:
            distances.append({'r': relation['id'], 'pair': [relation['source'], relation['target']], 'p': opening['id'], 'xy': opening['position_px'], 'dist': ds})

concepts = []
for relation in relations:
    if relation['type'] == 'access' and not relation.get('openings'):
        key = '-'.join([relation['source'], relation['target']])
        assert relation['id'] in readings.CONCEPT_NOTES or key in readings.CONCEPT_NOTES, relation
        concepts.append({'relation': relation, 'note': readings.CONCEPT_NOTES.get(relation['id'], readings.CONCEPT_NOTES.get(key))})
report = {'space_count': len(spaces), 'relations': dict(Counter(r['type'] for r in relations)), 'opening_count': opening_counter, 'removed': readings.REMOVE, 'added_access': added, 'concepts': concepts, 'opening_boundary_review': distances}
(WORK / '关系处理记录.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({k: v for k, v in report.items() if k not in ['removed', 'added_access', 'concepts']}, ensure_ascii=False, indent=2))

# Find functional units without a path to an architectural entrance.
graph = defaultdict(set)
for relation in relations:
    if relation['type'] == 'access':
        graph[relation['source']].add(relation['target'])
        graph[relation['target']].add(relation['source'])
reachable = {r['target'] for r in relations if r['type'] == 'entrance'}
frontier = list(reachable)
while frontier:
    sid = frontier.pop()
    for adjacent in graph[sid] - reachable:
        reachable.add(adjacent)
        frontier.append(adjacent)
print('No entrance path:', [(s['id'], s['name'], s['type']) for s in data['spaces'] if s['id'] not in reachable and s['type'] not in {'landscape', 'courtyard'}])
