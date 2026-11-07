"""Draw review crops with stable numbers and audited, separate leader paths."""
from collections import defaultdict
from pathlib import Path
import heapq
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import LineString, Point, Polygon


FONT = '/System/Library/Fonts/STHeiti Medium.ttc'
COLORS = ['#b44021', '#2163a3', '#8048a4', '#008375', '#ad3962',
          '#80601f', '#4152a5', '#8a512b', '#267545', '#a12a64']


def font(size):
    return ImageFont.truetype(FONT, max(8, round(size)))


def wrap(text, width):
    return [text[i:i + width] for i in range(0, len(text), width)]


def route(items, width, height):
    step = 5
    nx, ny = math.ceil(width / step) + 1, math.ceil(height / step) + 1
    endpoints = {q['id']: (tuple(round(z / step) for z in q['start']),
                            tuple(round(z / step) for z in q['target']))
                 for q in items}
    for attempt in range(18):
        occupied = np.zeros((ny, nx), dtype=bool)
        reserved = np.zeros_like(occupied)
        for pairs in endpoints.values():
            for x, y in pairs:
                reserved[max(0, y - 2):y + 3, max(0, x - 2):x + 3] = True
        order = items[attempt % len(items):] + items[:attempt % len(items)]
        if attempt >= len(items):
            order = list(reversed(order))
        paths = {}
        for q in order:
            start, end = endpoints[q['id']]
            allowed = ~occupied & ~reserved
            for x, y in [start, end]:
                allowed[max(0, y - 2):y + 3, max(0, x - 2):x + 3] = (
                    ~occupied[max(0, y - 2):y + 3, max(0, x - 2):x + 3])
            if not allowed[start[1], start[0]] or not allowed[end[1], end[0]]:
                break
            heap = [(0, 0, start)]
            costs, prev = {start: 0}, {}
            found = False
            while heap:
                _, cost, node = heapq.heappop(heap)
                if cost != costs[node]:
                    continue
                if node == end:
                    found = True
                    break
                x, y = node
                for xx, yy in [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]:
                    if not (3 <= xx < nx - 3 and 18 <= yy < ny - 3):
                        continue
                    if not allowed[yy, xx]:
                        continue
                    nxt = xx, yy
                    nc = cost + 1
                    if nc < costs.get(nxt, float('inf')):
                        costs[nxt], prev[nxt] = nc, node
                        heuristic = abs(xx - end[0]) + abs(yy - end[1])
                        heapq.heappush(heap, (nc + heuristic, nc, nxt))
            if not found:
                break
            nodes = [end]
            while nodes[-1] != start:
                nodes.append(prev[nodes[-1]])
            nodes.reverse()
            for x, y in nodes:
                occupied[max(0, y - 1):y + 2, max(0, x - 1):x + 2] = True
            pts = [q['start']] + [(x * step, y * step) for x, y in nodes]
            pts += [q['target']]
            simple = [pts[0]]
            for a, b, c in zip(pts, pts[1:], pts[2:]):
                if abs((b[0]-a[0])*(c[1]-b[1]) - (b[1]-a[1])*(c[0]-b[0])) > 0.01:
                    simple.append(b)
            simple.append(pts[-1])
            paths[q['id']] = simple
        if len(paths) != len(items):
            continue
        lines = [LineString(paths[q['id']]) for q in items]
        if any(a.intersects(b) for i, a in enumerate(lines) for b in lines[:i]):
            continue
        return paths
    raise RuntimeError('Leader routing failed: ' + ','.join(q['id'] for q in items))


def make_panel(source, items, spaces, title, color, output):
    polys = {q['id']: Polygon(spaces[q['id']]['polygon_display']) for q in items}
    bounds = [p.bounds for p in polys.values()]
    crop = (max(0, math.floor(min(b[0] for b in bounds)) - 40),
            max(0, math.floor(min(b[1] for b in bounds)) - 45),
            min(source.width, math.ceil(max(b[2] for b in bounds)) + 45),
            min(source.height, math.ceil(max(b[3] for b in bounds)) + 45))
    scale = min(3.5, 1700 / (crop[2] - crop[0]))
    cw, ch = round((crop[2]-crop[0])*scale), round((crop[3]-crop[1])*scale)
    sidebar, top = 540, 100
    width, height = sidebar + cw + 90, max(ch + 160, len(items)*92 + 180)
    ox, oy = sidebar + 25, top + (height - top - ch - 40) // 2
    canvas = Image.new('RGB', (width, height), '#f8fafc')
    canvas.paste(source.crop(crop).resize((cw, ch), Image.Resampling.LANCZOS), (ox, oy))
    draw = ImageDraw.Draw(canvas)
    draw.text((20, 20), title, font=font(27), fill='#172b4d')
    draw.text((20, 60), '核对号与S编号固定；候选待确认。彩线止于对应空间边界。',
              font=font(19), fill='#475569')
    targets = []
    used = []
    for i, q in enumerate(items):
        p = polys[q['id']]
        x1, y1, x2, y2 = p.bounds
        # Stagger equal-height rooms, keeping every anchor on its own boundary.
        y = y1 + min(12 + 7*i, (y2-y1)*0.7)
        while any(abs(y-z) < 3 for z in used) and y < y2-3:
            y += 3
        used.append(y)
        cut = p.intersection(LineString([(-1, y), (source.width+1, y)]))
        parts = list(cut.geoms) if hasattr(cut, 'geoms') else [cut]
        coords = [v for part in parts if part.geom_type == 'LineString' for v in part.coords]
        if not coords:
            a = p.representative_point()
            target = p.exterior.interpolate(p.exterior.project(a))
            x, y = target.x, target.y
        else:
            x = min(v[0] for v in coords)
        assert p.boundary.distance(Point(x, y)) < 0.1
        ly = top + 20 + i * (height-top-80) / max(1, len(items))
        targets.append(dict(id=q['id'], start=(sidebar-40, ly+15),
                            target=(ox+(x-crop[0])*scale, oy+(y-crop[1])*scale),
                            ly=ly))
    paths = route(targets, width, height)
    for q in targets:
        draw.line(paths[q['id']], fill='white', width=7)
        draw.line(paths[q['id']], fill=color, width=3)
        x, y = q['target']
        draw.ellipse((x-4, y-4, x+4, y+4), fill=color)
    for q, target in zip(items, targets):
        p = polys[q['id']]
        pts = [(ox+(x-crop[0])*scale, oy+(y-crop[1])*scale) for x, y in p.exterior.coords]
        draw.line(pts, fill=color, width=3)
        ly = target['ly']
        draw.text((20, ly), f"{q['number']}｜{q['id']}", font=font(27), fill=color)
        for j, line in enumerate(wrap(q['candidate'], 18)[:2]):
            draw.text((20, ly+34+j*25), line, font=font(21), fill='#334155')
    canvas.save(output, quality=94, subsampling=0)
    return {'crop': crop, 'scale': scale, 'paths': paths, 'width': width, 'height': height}


def make_master(source, items, spaces, panels, title, output):
    side = 1050
    center = min(3400, max(2300, source.width))
    scale = center/source.width
    ih = round(source.height*scale)
    columns = [[], []]
    heights = [0, 0]
    for panel in panels:
        with Image.open(panel) as im:
            h = round(im.height*side/im.width)
        index = 0 if heights[0] <= heights[1] else 1
        columns[index].append((panel, h))
        heights[index] += h + 22
    height = max(heights + [ih + 220]) + 150
    width = center + side*2 + 160
    ox, oy = side+80, max(160, (height-ih)//2)
    canvas = Image.new('RGB', (width, height), '#f1f5f9')
    canvas.paste(source.resize((center, ih), Image.Resampling.LANCZOS), (ox, oy))
    draw = ImageDraw.Draw(canvas)
    draw.text((ox, 24), title, font=font(37), fill='#172b4d')
    draw.text((ox, 78), f'{len(items)}项名称待确认｜中间完整原图；左右连续编号局部与引线。',
              font=font(25), fill='#475569')
    for q in items:
        points = [(ox+x*scale, oy+y*scale) for x, y in spaces[q['id']]['polygon_display']]
        draw.line(points+[points[0]], fill=q['color'], width=3)
        p = Polygon(points)
        x1, y1, x2, y2 = p.bounds
        pt = p.representative_point()
        x, y = (x1+15, y1+12) if p.covers(Point(x1+15, y1+12)) else (pt.x, pt.y)
        text = q['number']
        size = max(10, min(22, int((y2-y1)*0.5)))
        box = draw.textbbox((x, y), text, font=font(size), anchor='mm')
        draw.rectangle((box[0]-3, box[1]-2, box[2]+3, box[3]+2), fill='white', outline=q['color'])
        draw.text((x, y), text, font=font(size), anchor='mm', fill=q['color'])
    for ci, column in enumerate(columns):
        x, y = (20 if ci == 0 else ox+center+35), 145
        for panel, h in column:
            with Image.open(panel) as im:
                canvas.paste(im.resize((side, h), Image.Resampling.LANCZOS), (x, y))
            y += h + 22
    canvas.save(output, quality=91, subsampling=0)
    canvas.thumbnail((1700, 2000))
    canvas.save(Path(output).with_name('总图目检.jpg'), quality=90)
