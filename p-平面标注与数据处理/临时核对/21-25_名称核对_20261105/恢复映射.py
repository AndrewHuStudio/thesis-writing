"""Read historical builders as metadata only; discard all file writes and prints."""
import ast
import json
from pathlib import Path
from shapely.geometry import Polygon

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1] / '标注试样'
HIST = BASE / '历史取证'
SCRIPTS = {21: '21_59_build_annotation.py', 22: '22_66_build_annotation.py',
           23: '23_65_build_draft.py', 24: '24_65_build_draft.py',
           25: '25_70_build_annotation.py'}


def read_metadata(filename):
    source = (HIST / filename).read_text().replace('p-写作过程/标注试样', 'p-平面标注与数据处理/标注试样')
    if filename.startswith('23_'):
        source = '\n'.join(source.splitlines()[:265])
    tree = ast.parse(source)
    tree.body = [node for node in tree.body if not (
        isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) and (
            isinstance(node.value.func, ast.Attribute) and node.value.func.attr == 'write_text'
            or isinstance(node.value.func, ast.Name) and node.value.func.id == 'print'))]
    context = {}
    exec(compile(tree, filename, 'exec'), context)
    return context


for number, script in SCRIPTS.items():
    context = read_metadata(script)
    directory = next(ROOT.glob(f'{number}_*'))
    current = json.loads((directory / 'annotation.json').read_text())
    spaces = {s['id']: s for s in current['spaces']}
    if number == 21:
        bykey = {i['key']: i for i in context['items']}
        keys = [f'acute_bed{i}' for i in range(1, 6)] + [
            'multi_bed', 'med2', 'med1', 'preop', 'acute_top', 'stor2',
            'orth_side', 'derm', 'lab_side', 'physio', 'ecg', 'eeg', 'file', 'elect_east']
        review = [bykey[k].copy() for k in keys]
        review[12].update(candidate='烧伤 / 皮肤', evidence='旧稿候选；两字字形有歧义，须结合局部图核对', confidence='中')
    elif number == 23:
        review = [dict(o, polygon_px=list(o['geom'].exterior.coords)[:-1])
                  for o in context['items'] if o['type'] == 'unknown']
        for row in review:
            scores = sorted((row['geom'].intersection(Polygon(s['polygon_px'])).area /
                             row['geom'].union(Polygon(s['polygon_px'])).area, s['id'])
                            for s in current['spaces'] if s['type'] == 'unknown')
            assert scores[-1][0] > 0.8, (row['key'], scores[-1])
            row['id'] = scores[-1][1]
        ordered = []
        for group in dict.fromkeys(r['group'] for r in review):
            members = sorted((r for r in review if r['group'] == group),
                             key=lambda r: (min(y for x,y in r['polygon_px']), min(x for x,y in r['polygon_px'])))
            bands = []
            for row in members:
                y = min(y for x,y in row['polygon_px'])
                if not bands or y - bands[-1][0] > 20:
                    bands.append([y, []])
                bands[-1][1].append(row)
            for _, band in bands:
                ordered.extend(sorted(band, key=lambda r: min(x for x,y in r['polygon_px'])))
        review = ordered
    else:
        review = context['review' if number == 24 else 'questions']
    if number == 24:
        for row in review:
            polygon = Polygon(row['polygon_px'])
            scores = sorted((polygon.intersection(Polygon(s['polygon_px'])).area /
                             polygon.union(Polygon(s['polygon_px'])).area, s['id'])
                            for s in current['spaces'] if s['type'] == 'unknown')
            assert scores[-1][0] > 0.8, (row['key'], scores[-1])
            row['id'] = scores[-1][1]
    result = []
    for index, item in enumerate(review, 1):
        sid = item['id']
        assert sid in spaces and spaces[sid]['type'] == 'unknown', (number, sid)
        candidates = item.get('candidates') or [item.get('candidate', '暂无可靠候选')]
        result.append(dict(number=f'{index:02d}', id=sid, key=item['key'],
                           group=item.get('group', spaces[sid]['scope']),
                           candidates=candidates, evidence=item.get('evidence') or item.get('basis', ''),
                           confidence=item.get('confidence', '低'), polygon_px=spaces[sid]['polygon_px']))
    assert {r['id'] for r in result} == {s['id'] for s in current['spaces'] if s['type'] == 'unknown'}
    output = BASE / directory.name
    output.mkdir(exist_ok=True)
    (output / '固定核对映射.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(number, 'recovered', len(result))
