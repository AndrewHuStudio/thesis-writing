from pathlib import Path
from collections import Counter, deque
import json, sys, math, copy, os, re
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon, Point, box, LineString

WORK = Path(__file__).resolve().parent
SAMPLE = WORK.parent.parent / '标注试样' / WORK.name
sys.path.insert(0, '/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts')
import annotation_tools as at

data = json.loads((SAMPLE / 'annotation.json').read_text())
state = json.loads((WORK / 'review_state.json').read_text())
if '--rebuild-before-user-review' not in sys.argv:
    raise SystemExit('仅首轮恢复脚本。用户填写后须增量同步JSON、SVG、MD；本脚本会重建空白表，不可直接重跑。')
meta = json.loads((WORK / '空间工作索引.json').read_text())
pending = json.loads((WORK / '核对号对应.json').read_text())
byid = {m['id']: m for m in meta}
polys = {m['id']: Polygon(m['shape']) for m in meta}
source = Image.open(WORK / '转正原图.png').convert('RGB')
FONT = '/System/Library/Fonts/STHeiti Medium.ttc'
COLORS = {'A': '#b45309', 'B': '#6d28d9', 'C': '#0369a1', 'D': '#be185d',
          'E': '#4338ca', 'F': '#0f766e', 'G': '#a16207', 'H': '#b91c1c'}


def font(size):
    return ImageFont.truetype(FONT, max(9, int(size)))


def graph_report(d):
    nodes = {s['id'] for s in d['spaces']}
    adj = {s: set() for s in nodes}
    for r in d['relations']:
        if r['type'] == 'access':
            adj[r['source']].add(r['target'])
            adj[r['target']].add(r['source'])

    def reach(start):
        seen = {start}
        todo = [start]
        while todo:
            for v in adj[todo.pop()]:
                if v not in seen:
                    todo.append(v)
                    seen.add(v)
        return sorted(seen)

    unseen = set(nodes)
    components = []
    while unseen:
        cc = reach(min(unseen))
        components.append(cc)
        unseen.difference_update(cc)
    components.sort(key=lambda c: (-len(c), c[0]))
    entrances = {r['id']: {'name': r['name'], 'target': r['target'], 'reachable': reach(r['target'])}
                 for r in d['relations'] if r['type'] == 'entrance'}
    return {'spaces': len(nodes), 'access': sum(r['type'] == 'access' for r in d['relations']),
            'components_count': len(components), 'components': components,
            'isolated': sorted(s for s in nodes if not adj[s]),
            'main_entry_reachable_count': len(reach('S082')), 'main_entry_reachable': reach('S082'),
            'entrances': entrances, 'outside_is_not_shared_node': True,
            'interpretation': '只计算access。service不通行，null不互连外门；孤立不视为不相通或训练负例。'}


baseline = json.loads((WORK / '20261107_接续前备份/annotation.json').read_text())
report = {'before': graph_report(baseline), 'after': graph_report(data)}
(WORK / '连通性测试.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')


def upright_svg():
    d = copy.deepcopy(data)
    d['image']['width'], d['image']['height'] = 3260, 2444
    for s in d['spaces']:
        s['polygon_px'] = [[y, 2444 - x] for x, y in s['polygon_px']]
    for r in d['relations']:
        if 'position_px' in r:
            x, y = r['position_px']
            r['position_px'] = [y, 2444 - x]
        for o in r.get('openings', []):
            x, y = o['position_px']
            o['position_px'] = [y, 2444 - x]
    out = SAMPLE / '标注.svg'
    at.render(d, SAMPLE / 'annotation.json', out)
    tree = ET.parse(out)
    ns = {'s': at.NS}
    im = tree.find('.//s:image', ns)
    im.set('width', '2444')
    im.set('height', '3260')
    im.set('transform', 'translate(0 2444) rotate(-90)')
    original = {o['id']: o for r in data['relations'] for o in r.get('openings', [])}
    for e in tree.iter():
        oid = e.get('data-opening-id')
        if oid:
            c = e.find('s:circle', ns)
            x, y = original[oid]['position_px']
            c.set('cx', str(x))
            c.set('cy', str(y))
            c.set('transform', 'matrix(0 -1 1 0 0 2444)')
            label = e.find('s:text', ns)
            label.set('x', str(y - 40))
            label.set('y', str(2444 - x - 10))
            label.set('font-size', '11')
            label.set('stroke-width', '.8')
    tree.write(out, encoding='unicode')


upright_svg()


def overview():
    W, H, sc = 6600, 4500, 2.2
    ox, oy = 1100, 600
    canvas = Image.new('RGB', (W, H), '#f8fafc')
    canvas.paste(source.resize((4400, 3300), Image.Resampling.LANCZOS), (ox, oy))
    draw = ImageDraw.Draw(canvas)
    draw.text((40, 25), '36 南雄市中医院医共体总院｜113项名称核对总图', font=font(42), fill='#18314c')
    draw.text((40, 85), '固定01—113号；核心JSON尚为unknown。请以同一MD中的清晰局部图填写。', font=font(27), fill='#9a3412')
    paths = json.loads((WORK / '36_高清核对总图_引线检查.json').read_text())['paths']
    sides = [[m for m in pending if m['group'][0] in {'A', 'B', 'D', 'E', 'G'}],
             [m for m in pending if m['group'][0] not in {'A', 'B', 'D', 'E', 'G'}]]
    for sid, pts in paths.items():
        color = COLORS[byid[sid]['group'][0]]
        draw.line([tuple(p) for p in pts], fill=color, width=1)
    for side, items in enumerate(sides):
        gap = min(140, (H - 220) / len(items))
        sy = max(140, (H - gap * len(items)) / 2)
        bx = 25 if side == 0 else W - 1040 - 25
        for j, m in enumerate(items):
            y = sy + j * gap
            color = COLORS[m['group'][0]]
            draw.rounded_rectangle((bx, y, bx + 1040, y + gap - 5), radius=5, fill='white', outline=color, width=2)
            draw.text((bx + 12, y + 3), f"{m['review']}｜{m['id']}  名称未确认", font=font(21), fill=color)
            label = '候选：' + m['candidate']
            draw.text((bx + 12, y + 30), label, font=font(19), fill='#334155')
            pts = [(ox + x * sc, oy + yy * sc) for x, yy in m['shape']]
            draw.line(pts + [pts[0]], fill=color, width=2)
            ax, ay = paths[m['id']][-1]
            badge_font = font(14)
            width = draw.textlength(m['review'], font=badge_font) + 6
            draw.rectangle((ax - width / 2, ay - 9, ax + width / 2, ay + 10), fill='white', outline=color)
            draw.text((ax - width / 2 + 3, ay - 8), m['review'], font=badge_font, fill=color)
    canvas.save(WORK / '36_高清核对总图.png')
    canvas.resize((2200, 1500)).save(WORK / '36_核对总图_预览.png')


overview()
badge_audit = []


def detail(name, ids, labels, crop=None, openings=False):
    if crop is None:
        bounds = [polys[s].bounds for s in ids]
        crop = [min(b[0] for b in bounds) - 22, min(b[1] for b in bounds) - 25,
                max(b[2] for b in bounds) + 22, max(b[3] for b in bounds) + 25]
    x0, y0, x1, y1 = crop
    sc = min(1460 / (x1 - x0), 940 / (y1 - y0))
    cw, ch = round((x1 - x0) * sc), round((y1 - y0) * sc)
    canvas = Image.new('RGB', (cw + 40, ch + 100), 'white')
    raw = source.crop(tuple(round(v * 1.63) for v in crop)).resize((cw, ch), Image.Resampling.LANCZOS)
    canvas.paste(raw, (20, 70))
    draw = ImageDraw.Draw(canvas)
    draw.text((20, 12), name.replace('_', ' '), font=font(27), fill='#18314c')
    avoid = []
    if openings:
        for r in data['relations']:
            for o in r.get('openings', []):
                xx, yy = o['position_px'][1] / 1.63, (2444 - o['position_px'][0]) / (2444 / 1500)
                if x0 <= xx <= x1 and y0 <= yy <= y1:
                    px, py = 20 + (xx - x0) * sc, 70 + (yy - y0) * sc
                    draw.ellipse((px - 5, py - 5, px + 5, py + 5), fill='#dc2626', outline='white', width=1)
                    draw.text((px + 6, py - 21), o['id'], font=font(16), fill='#b91c1c', stroke_width=2, stroke_fill='white')
                    avoid.append(Point(xx, yy).buffer(7 / sc))
    for sid in ids:
        p = polys[sid].intersection(box(x0, y0, x1, y1))
        color = COLORS[byid[sid]['group'][0]] if not name.startswith('K') else '#0369a1'
        pts = [(20 + (x - x0) * sc, 70 + (y - y0) * sc) for x, y in byid[sid]['shape']]
        draw.line(pts + [pts[0]], fill=color, width=2)
        label = labels[sid]
        bounds = p.bounds
        best = None
        for size in (25, 22, 19, 16, 13):
            ff = font(size)
            bw = draw.textlength(label, font=ff) + 10
            bh = size + 10
            ww, hh = bw / sc, bh / sc
            opts = []
            for fy in (.15, .8, .35, .6, .5, .92, .06):
                for fx in (.1, .7, .4, .55, .85, .94, .04):
                    xx = bounds[0] + (bounds[2] - bounds[0]) * fx - ww / 2
                    yy = bounds[1] + (bounds[3] - bounds[1]) * fy - hh / 2
                    rect = box(xx, yy, xx + ww, yy + hh)
                    if not p.covers(rect) or any(rect.intersects(a) for a in avoid):
                        continue
                    region = source.crop((round(xx * 1.63), round(yy * 1.63),
                                          round((xx + ww) * 1.63), round((yy + hh) * 1.63))).convert('L').resize((15, 9))
                    score = sum(v < 130 for v in region.getdata()) / 135
                    opts.append((score, xx, yy, bw, bh, ff, rect))
            if opts:
                best = min(opts, key=lambda z: z[0])
                if best[0] < .06:
                    break
        assert best is not None, (name, sid, '请拆分局部图')
        score, xx, yy, bw, bh, ff, rect = best
        px, py = 20 + (xx - x0) * sc, 70 + (yy - y0) * sc
        draw.rounded_rectangle((px, py, px + bw, py + bh), radius=3, fill='white', outline=color, width=2)
        draw.text((px + 5, py + 2), label, font=ff, fill=color)
        avoid.append(rect)
        badge_audit.append({'figure': name, 'space': sid, 'number': label,
                            'inside': p.covers(rect), 'inside_crop': box(x0, y0, x1, y1).covers(rect),
                            'dark_fraction': score})
    canvas.save(WORK / (name + '.png'))
    return name + '.png'


rel = Path(os.path.relpath(WORK, SAMPLE)).as_posix()
lines = ['# 36号首层平面标注与连通核对', '',
         '<!-- annotation:summary:start -->', '<!-- annotation:summary:end -->', '',
         '**本轮：**沿用170个空间及原固定核对号；113项名称／性质、7项关键连通待确认。', '',
         '**填写：**可改“预估名称（可改）”后将确认栏填“已确认”，或直接在确认栏写实际名称。'
         '也可回复`01=名称，02=名称`；分批填写后保留其余待确认项。', '',
         '**门位：**5个可辨门洞已记入JSON并显示红点；其余68条access为无定位的概念连接，'
         '含本轮布局推断。未画红点不等于不相通。', '',
         '**空间性质：**10=S016、38=S059、46=S079、51=S091仍需区分庭院／挑空、屋面或室内空间。'
         '若确认为庭院／挑空，直接移出室内面积分母；无需另答顶盖。', '',
         '**测试范围：**只按access测试，service不视为通行，各外门的null不互连。'
         f"主入口当前可达{report['after']['main_entry_reachable_count']}个节点，"
         f"全图有{report['after']['components_count']}个分量；辅助间和未确认区域的孤立不作为负例。", '',
         f'[完整高清核对总图]({rel}/36_高清核对总图.png)', '',
         f'![名称核对定位总图]({rel}/36_核对总图_预览.png)', '', '## 名称与空间性质', '']

# 连续片区内每组至多五项；大留白单独展示，避免小房间被压成缩略图。
groups = []
current = []
single_keys = {'roof', 'd_blank', 'e4', 'f_blank', 'h16'}
for m in pending:
    if current and (m['group'] != current[0]['group'] or len(current) == 5 or m['key'] in single_keys):
        groups.append(current)
        current = []
    current.append(m)
    if m['key'] in single_keys:
        groups.append(current)
        current = []
if current:
    groups.append(current)
for group in groups:
    nums = [m['review'] for m in group]
    name = f"名称_{nums[0]}-{nums[-1]}"
    image = detail(name, [m['id'] for m in group], {m['id']: m['review'] for m in group})
    lines += [f"### {nums[0]}—{nums[-1]}｜{group[0]['group']}", '',
              f'![{nums[0]}—{nums[-1]}：房内数字对应下表]({rel}/{image})', '',
              '| 核对号 | S编号 | 预估名称（可改） | 备选名称 | 依据与把握 | 我的确认／备注 | 核对号（重复） |',
              '| --- | --- | --- | --- | --- | --- | --- |']
    for m in group:
        choices = m['candidate'].split('／')
        candidate = choices[0] if choices else '暂无可靠候选'
        alternative = '／'.join(choices[1:]) or '—'
        reason = m['basis'] + '。把握：' + m['confidence'] + '；候选仅供核对'
        if len(choices) > 1:
            reason += '，各候选共用此依据，现图不能区分'
        lines.append(f"| {m['review']} | {m['id']} | {candidate} | {alternative} | {reason} | 待确认 | {m['review']} |")
    lines.append('')
lines += ['## 关键连通问题', '', '各题可填“同意”、实际相连S号，或“不直接相通”；只确定关系，无需给精确门位。', '']
for q in state['connectivity_items']:
    ids = [q['source'], q['target']]
    if q['review_id'] == 'K07':
        ids.append('S075')
    image = detail(q['review_id'] + '_连通核对', ids, {sid: sid[1:] for sid in ids}, q['crop_upright'], openings=True)
    lines += [f"### {q['review_id']}｜{q['source']} ↔ {q['target']}", '',
              f"![{q['review_id']}：空间内标稳定S号数字]({rel}/{image})", '',
              '**问题：**' + q['question'], '', '**我的判断：**' + q['judgement'], '',
              '**我的确认／备注：**待填写', '']
lines += ['**范围与坐标：**首层；保留门诊、急诊、输液、出入院和后勤的原scope。'
          '原图不改，JSON沿用2444×3260原图坐标，SVG及核对图仅转正显示。', '']
(SAMPLE / '标注说明.md').write_text('\n'.join(lines))
(WORK / '核对图数字审计.json').write_text(json.dumps(badge_audit, ensure_ascii=False, indent=2) + '\n')
at.summary(data, SAMPLE / '标注说明.md', SAMPLE / 'annotation.json', WORK / 'review_state.json')
print(json.dumps({'before': {k: report['before'][k] for k in ['access', 'components_count', 'main_entry_reachable_count']},
                  'after': {k: report['after'][k] for k in ['access', 'components_count', 'main_entry_reachable_count']},
                  'name_figures': len(groups), 'connection_figures': len(state['connectivity_items']),
                  'number_badges': len(badge_audit)}, ensure_ascii=False))
