"""Recover historical questions as metadata; never execute historical file writes."""
import ast
import json
import re
from pathlib import Path
from shapely.geometry import Polygon

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1] / '标注试样'
HIST = BASE / '历史取证'
BUILD = {31: '31_81_build31.py', 32: '32_86_build.py',
         33: '33_73_build_annotation.py', 34: '34_66_build_annotation.py',
         35: '35_build_annotation.py'}
SUFFIX = {31: 'ddf9b803', 32: '7cebf018', 33: '59403464', 34: 'e7332f80'}


def final_source(number):
    source = (HIST / BUILD[number]).read_text()
    if number in SUFFIX and number != 34:
        commands = sorted(HIST.glob(SUFFIX[number] + '_*_command.txt'),
                          key=lambda p: int(p.name.split('_')[1]))
        for command in commands:
            text = command.read_text()
            if not any(x in text for x in [f'/build{number}.py', '/build.py', '/build_annotation.py']):
                continue
            for fragment in re.findall(r"python(?:3)? - <<'PY'\n(.*?)\nPY", text, re.S):
                try:
                    tree = ast.parse(fragment)
                except SyntaxError:
                    continue
                for node in tree.body:
                    if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                        continue
                    if not isinstance(node.targets[0], ast.Name) or node.targets[0].id != 's':
                        continue
                    class Reads(ast.NodeTransformer):
                        def visit_Call(self, call):
                            if isinstance(call.func, ast.Attribute) and call.func.attr == 'read':
                                return ast.copy_location(ast.Constant(source), call)
                            return self.generic_visit(call)
                    expr = ast.Expression(Reads().visit(node.value))
                    source = eval(compile(ast.fix_missing_locations(expr), 'historical_replace', 'eval'),
                                  {'s': source, '__builtins__': {}})
    return source


for number in range(31, 36):
    project = next(ROOT.glob(f'{number}_*'))
    current = json.loads((project / 'annotation.json').read_text())
    source = final_source(number)
    # Only declarations and room metadata preceding relation/file generation.
    cuts = {31: 'rels=[]', 32: '# 所有现有房间及中庭轮廓',
            33: '# 可达关系只录', 34: "data={'image':", 35: '# Inspect geometry'}
    if number == 34:
        source = source.split("(T/'review-map.json')")[0]
    else:
        source = source.split(cuts[number])[0]
    source = source.replace('p-写作过程/标注试样', 'p-平面标注与数据处理/标注试样')
    tree = ast.parse(source)
    tree.body = [n for n in tree.body if not (
        isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
        and isinstance(n.value.func, ast.Attribute) and n.value.func.attr == 'write_text')]
    context = {}
    exec(compile(tree, f'metadata_{number}', 'exec'), context)
    if number == 31:
        metadata = [dict(m, polygon_px=next(s['polygon_px'] for s in context['spaces']
                    if s['id'] == m['id'])) for m in context['meta'] if 'candidate' in m]
    elif number == 32:
        metadata = sorted((dict(m, polygon_px=list(m['geom'].exterior.coords)[:-1])
                          for m in context['items'] if m['type'] == 'unknown'),
                          key=lambda q: (q['group'], round(q['geom'].bounds[1]/18),
                                         q['geom'].bounds[0], q['geom'].bounds[1]))
    elif number in [33, 34]:
        metadata = context['review']
        lookup = {s['id']: s for s in context['spaces']}
        for m in metadata:
            m['polygon_px'] = lookup[m['id']]['polygon_px']
    else:
        metadata = []
        for key, candidate, basis, confidence, anchor, side, ly in context['review']:
            old = next(s for s in context['spaces'] if s['id'] == context['meta'][key]['id'])
            metadata.append(dict(key=key, candidate=candidate, basis=basis, confidence=confidence,
                                 polygon_px=[[2444-y, x] for x,y in old['polygon_px']]))
    rows = []
    for item in metadata:
        polygon = Polygon(item['polygon_px'])
        scores = sorted((polygon.intersection(Polygon(s['polygon_px'])).area /
                         polygon.union(Polygon(s['polygon_px'])).area, s['id'])
                        for s in current['spaces'] if s['type'] == 'unknown')
        score, sid = scores[-1]
        assert score > .75, (number, item['key'], score, sid)
        space = next(s for s in current['spaces'] if s['id'] == sid)
        candidates = item.get('candidates', item.get('candidate', '暂无可靠候选'))
        if isinstance(candidates, str):
            candidates = re.split(r'\s*[/／]\s*', candidates)
        rows.append(dict(id=sid, key=item['key'], group=item.get('group', space['scope']),
                         candidates=candidates, evidence=item.get('basis', item.get('evidence', '依据不足')),
                         confidence=item.get('confidence', '低'), polygon_px=space['polygon_px']))
        for field in ['side', 'anchor_y', 'upright_polygon']:
            if field in item:
                rows[-1][field] = item[field]
    if number == 33:
        rows.sort(key=lambda r: r['id'])
    for i, row in enumerate(rows, 1):
        row['number'] = f'{i:02d}'
    assert len(rows) == len({r['id'] for r in rows})
    assert {r['id'] for r in rows} == {s['id'] for s in current['spaces'] if s['type'] == 'unknown'}
    target = BASE / project.name
    target.mkdir(exist_ok=True)
    (target / '固定核对映射.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n')
    print(number, 'recovered', len(rows), flush=True)
