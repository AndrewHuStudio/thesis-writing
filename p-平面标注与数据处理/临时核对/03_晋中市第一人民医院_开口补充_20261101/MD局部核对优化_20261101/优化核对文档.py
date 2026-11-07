"""从当前成果制作局部阅读图，并将原有问题与填写栏移到对应图旁。"""

from pathlib import Path
import hashlib
import json
import re
import shutil

from PIL import Image, ImageDraw, ImageFont
from markdown_it import MarkdownIt


OUT = Path(__file__).resolve().parent
REVIEW = OUT.parent
ROOT = REVIEW.parents[1]
PROJECT = ROOT / '标注试样/03_晋中市第一人民医院迁建项目'
MD = PROJECT / '标注说明.md'
FONT = '/System/Library/Fonts/Supplemental/Arial Unicode.ttf'
DATA = json.loads((PROJECT / 'annotation.json').read_text())
SPACES = {s['id']: s for s in DATA['spaces']}
GROUPS = json.loads((REVIEW / '本轮核对映射.json').read_text())['groups']
SOURCE = Image.open(PROJECT / DATA['image']['file']).convert('RGB')
BASE = SOURCE.transpose(Image.Transpose.ROTATE_90)
WIDTH, HEIGHT = BASE.size
ORIGINAL = MD.read_text()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def upright(sid):
    return [(y, SOURCE.width - x) for x, y in SPACES[sid]['polygon_px']]


def bounds(points):
    xs, ys = zip(*points)
    return min(xs), min(ys), max(xs), max(ys)


def group_rows():
    rows = {}
    for line in ORIGINAL.splitlines():
        if re.match(r'^\| \d{2} \|', line):
            cells = [x.strip() for x in line.strip('|').split('|')]
            assert len(cells) == 6, cells
            rows[cells[0]] = cells
    assert len(rows) == 13
    return rows


def make_picture(code, title, box, target_ids):
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(WIDTH, x1), min(HEIGHT, y1)
    crop = BASE.crop((x0, y0, x1, y1))
    raw = OUT / f'{code}_原图细节.png'
    crop.save(raw)
    # 显示放大仅方便阅读，不重建原图中缺失的字迹或门位。
    zoom = max(1.25, min(3.0, 1200 / crop.width))
    image = crop.resize((round(crop.width * zoom), round(crop.height * zoom)))
    header = 82
    canvas = Image.new('RGB', (max(640, image.width), image.height + header), 'white')
    offset = (canvas.width - image.width) // 2
    canvas.paste(image, (offset, header))
    draw = ImageDraw.Draw(canvas)
    draw.text((18, 8), f'{code}｜{title}', font=ImageFont.truetype(FONT, 25), fill='#16324f')
    draw.text((18, 45), '蓝框与 S 编号用于定位；门向仍以原图和人工确认为准。',
              font=ImageFont.truetype(FONT, 17), fill='#526172')
    labels = []
    for sid in sorted(target_ids):
        pts = upright(sid)
        bx0, by0, bx1, by1 = bounds(pts)
        if min(bx1, x1) <= max(bx0, x0) or min(by1, y1) <= max(by0, y0):
            continue
        local = [((x-x0)*zoom, (y-y0)*zoom) for x, y in pts]
        layer = Image.new('RGB', image.size, 'white')
        ld = ImageDraw.Draw(layer)
        ld.polygon(local, outline='#1976b9', width=2)
        # 独立图层先裁剪，避免轮廓线画到标题区域。
        mask = Image.new('1', image.size)
        ImageDraw.Draw(mask).line(local + [local[0]], fill=1, width=2)
        image.paste(layer, (0, 0), mask)
        interior = Image.new('1', image.size)
        ImageDraw.Draw(interior).polygon(local, fill=1)
        visible = interior.getbbox()
        if not visible:
            continue
        vx0, vy0, vx1, vy1 = visible
        cx, cy = (vx0+vx1)/2, (vy0+vy1)/2
        if not interior.getpixel((int(cx), int(cy))):
            candidates = [(x, y) for y in range(vy0+2, vy1, 4)
                          for x in range(vx0+2, vx1, 4) if interior.getpixel((x, y))]
            if not candidates:
                continue
            cx, cy = min(candidates, key=lambda p: (p[0]-cx)**2+(p[1]-cy)**2)
        font = ImageFont.truetype(FONT, max(14, min(23, int((vx1-vx0)/3.5))))
        labels.append((sid, cx, cy, font))
    canvas.paste(image, (offset, header))
    draw = ImageDraw.Draw(canvas)
    for sid, cx, cy, font in labels:
        draw.text((cx+offset, cy+header), sid, anchor='mm', font=font,
                  fill='#073eab', stroke_width=2, stroke_fill='white')
    path = OUT / f'{code}_编号局部.png'
    canvas.save(path)
    return {
        'code': code, 'title': title, 'image': str(path), 'raw': str(raw),
        'bbox_upright_px': [x0, y0, x1, y1],
        'visible_target_ids': [item[0] for item in labels],
    }


def rel(path):
    return '../../临时核对/' + str(Path(path).relative_to(ROOT / '临时核对'))


def main():
    backup = OUT / '修改前备份'
    backup.mkdir(exist_ok=True)
    assert not (backup / '标注说明.md').exists(), '已有备份，避免覆盖用户后续填写'
    shutil.copy2(MD, backup / '标注说明.md')
    before = {p.name: digest(p) for p in PROJECT.iterdir() if p.is_file()}
    rows = group_rows()
    details = {}
    for match in re.finditer(r'^### (\d{2})｜.*?\n(.*?)(?=^### |^## |\Z)', ORIGINAL, re.M | re.S):
        details[match[1]] = re.sub(r'^\[同号局部\].*?\n', '', match[2], flags=re.M).strip()
    assert len(details) == 13
    images = {}
    inventory = []
    for group in GROUPS:
        num = group['number']
        ids = set(re.findall(r'S\d{3}', rows[num][1] + rows[num][3]))
        ids &= SPACES.keys()
        if num == '08':
            ids.add('S344')
        main_ids = ids - {'S029', 'S076'} if num == '09' else ids
        reference = group['bbox_upright_reference']
        sx, sy = WIDTH/1725, HEIGHT/1440
        box = [reference[0]*sx, reference[1]*sy, reference[2]*sx, reference[3]*sy]
        # 走廊可保留相关片段，房间与交通核完整保留，避免漏裁门向线索。
        for sid in main_ids:
            if SPACES[sid]['type'] in {'corridor', 'hall'}:
                continue
            bx0, by0, bx1, by1 = bounds(upright(sid))
            box = [min(box[0], bx0), min(box[1], by0), max(box[2], bx1), max(box[3], by1)]
        box = [box[0]-35, box[1]-35, box[2]+35, box[3]+35]
        code = '09-A' if num == '09' else num
        item = make_picture(code, group['title'], box, main_ids)
        images[num] = [item]
        inventory.append(item)
        if num == '09':
            for code, sid in [('09-B', 'S029'), ('09-C', 'S076')]:
                bx0, by0, bx1, by1 = bounds(upright(sid))
                box = [bx0-95, by0-70, bx1+100, by1+70]
                item = make_picture(code, f'{sid} 西侧交通核入口', box, {sid})
                images[num].append(item)
                inventory.append(item)
    head = ORIGINAL.split('## 13 组固定编号核对')[0]
    tail = '## 保留的人工内容与精度说明' + ORIGINAL.split('## 保留的人工内容与精度说明', 1)[1]
    lines = [head.rstrip(), '', '## 如何直接看图填写', '',
             '本页保留 01—13 固定核对号。每组依次展示编号局部图、需要确认的问题、旧边明细及填写表；第 09 组另有 A／B／C 三张图，仍只用核对号 09。', '',
             '**填写方式：**在对应局部图下方修改“我的确认／备注”中的“待确认”。同组可逐项写，例如 `Sxxx 与 Syyy 直接相通；入口在图中左侧`、`Rxxx 不相通` 或 `仍看不清，待确认`；多项用分号分隔。这里的左右上下以局部图显示方向为准。保存 MD 后可继续补充，也可聊天回复 `01=……，02=……`。', '',
             '蓝色轮廓与 S 编号仅用于定位，不代表门洞已确认。各图附有未叠加编号的原图细节链接；放大不会恢复原图缺失的信息。已确认名称和原有备注保留，未答项继续待确认。', '',
             '<a id="review-index"></a>', '', '## 总图与片区索引', '',
             '总图用于查找片区，具体判断与填写请使用下方局部图。', '',
             '![完整原图连通疑点核对总图](../../临时核对/03_晋中市第一人民医院_开口补充_20261101/连通疑点_完整原图核对总图.png)', '',
             '| 核对号 | 片区 | 核对号（重复） |', '| --- | --- | --- |']
    for group in GROUPS:
        num = group['number']
        lines.append(f'| {num} | [跳到{group["title"]}](#review-{num}) | {num} |')
    lines += ['', '## 逐组局部图与填写区', '']
    for group in GROUPS:
        num, title = group['number'], group['title']
        row = rows[num]
        lines += [f'<a id="review-{num}"></a>', '', f'### {num}｜{title}', '',
                  f'**相关空间：**{row[1]}。', '']
        for item in images[num]:
            lines += [f'![{item["code"]} {item["title"]} S编号局部图]({rel(item["image"])})', '',
                      f'[打开原尺寸编号图]({rel(item["image"])}) · [查看未叠加编号的原图细节]({rel(item["raw"])})', '']
        lines += ['**需要确认：**' + row[3], '', '**待核旧边明细：**', '',
                  details[num], '', '**本组填写区（直接修改下表）：**', '',
                  '| 核对号 | 我的确认／备注 | 核对号（重复） |',
                  '| --- | --- | --- |', f'| {num} | {row[4]} | {num} |', '',
                  '[返回片区索引](#review-index)', '', '---', '']
    lines += [tail.rstrip(), '']
    new = re.sub(r'(\*\*[^*\n]+\*\*)(?=\S)', r'\1 ', '\n'.join(lines))
    MD.write_text(new)
    # 只改变 MD 与外部阅读图，数据、具名 SVG、原图以哈希核对。
    after = {p.name: digest(p) for p in PROJECT.iterdir() if p.is_file()}
    for name in before:
        if name != MD.name:
            assert before[name] == after[name], name
    for num, row in rows.items():
        assert f'| {num} | {row[4]} | {num} |' in new
        assert row[3] in new
    pending = json.loads((REVIEW / '本轮核对映射.json').read_text())['pending_access_ids']
    for rid in pending:
        assert len(re.findall(rf'^- {rid}：', new, re.M)) == 1, rid
    for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', new):
        if not target.startswith('#'):
            assert (MD.parent / target).resolve().exists(), target
    assert len(list(PROJECT.iterdir())) == 4
    engine = MarkdownIt('commonmark', {'html': True}).enable('table')
    html = engine.render(new)
    style = ('body{font:16px/1.7 -apple-system,sans-serif;color:#26364a;max-width:980px;margin:36px auto;padding:0 24px}'
             'img{max-width:100%;height:auto;border:1px solid #d7e1ec}table{border-collapse:collapse;width:100%;margin:14px 0 24px}'
             'td,th{border:1px solid #cbd5e1;padding:10px;text-align:left}th{background:#edf3f9}'
             'h3{border-bottom:2px solid #1b668f;padding-bottom:8px}a{color:#15648e}hr{margin:40px 0}')
    prefix = f'<meta charset="utf-8"><base href="{MD.parent.as_uri()}/"><style>{style}</style>'
    (OUT / 'MD阅读预览.html').write_text(prefix + html)
    cards = []
    for group in GROUPS:
        num = group['number']
        section = new.split(f'<a id="review-{num}"></a>', 1)[1]
        section = section.split('<a id="review-', 1)[0].split('## 保留的人工内容', 1)[0]
        rendered = engine.render(section)
        cards.append((num, rendered))
        (OUT / f'预览_{num}.html').write_text(prefix + rendered)
    report = {'project_file_count': len(after), 'group_count': len(GROUPS),
              'local_image_count': len(inventory), 'pending_relation_count': len(pending),
              'all_existing_answers_preserved': True, 'all_local_links_exist': True,
              'unchanged_files': [n for n in before if n != MD.name],
              'hashes_before': before, 'hashes_after': after, 'images': inventory}
    (OUT / '文档优化核验.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k: v for k, v in report.items() if k not in {'images', 'hashes_before', 'hashes_after'}}, ensure_ascii=False))


if __name__ == '__main__':
    main()
