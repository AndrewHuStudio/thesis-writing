"""Append stable name review tables and local figures to existing Markdown."""
import hashlib
import json
import math
import os
import re
import shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1] / '标注试样'
FONT = '/System/Library/Fonts/STHeiti Medium.ttc'
COLORS = ['#2563eb', '#0f766e', '#be123c', '#7c3aed', '#c2410c', '#0369a1']
OVERVIEWS = {21: '21_高清核对总图.png', 22: '22_名称核对总图.png',
             23: '23_西安经开医院_高清核对总图.png', 24: '24_名称核对总图.png',
             25: '25_名称核对总图.png'}


def bounds(rows):
    points = [point for row in rows for point in row['polygon_px']]
    return (min(x for x,y in points), min(y for x,y in points),
            max(x for x,y in points), max(y for x,y in points))


def chunks(rows):
    result = []
    for row in rows:
        if result:
            trial = result[-1] + [row]
            x0,y0,x1,y1 = bounds(trial)
            if len(trial) <= 6 and trial[0]['group'] == row['group'] and x1-x0 < 650 and y1-y0 < 650:
                result[-1].append(row)
                continue
        result.append([row])
    return result


def field(value):
    return str(value).replace('|', '／').replace('\n', ' ')


results = []
for number in range(21, 26):
    project = next(ROOT.glob(f'{number}_*'))
    target = BASE / project.name
    rows = json.loads((target / '固定核对映射.json').read_text())
    data = json.loads((project / 'annotation.json').read_text())
    backup = target / '续作前备份'
    backup.mkdir(exist_ok=True)
    manifest = {}
    for file in project.iterdir():
        if file.is_file():
            dest = backup / file.name
            if not dest.exists():
                shutil.copy2(file, dest)
            manifest[file.name] = hashlib.sha256(dest.read_bytes()).hexdigest()
    (target / '续作前SHA256.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    mdfile = project / '标注说明.md'
    original = mdfile.read_text()
    assert '## 房名与范围核对（2026-11-05）' not in original, 'Do not overwrite existing user answers'
    image = Image.open(project / data['image']['file']).convert('RGB')
    def rel(file):
        return os.path.relpath(file, project)
    lines = ['## 房名与范围核对（2026-11-05）', '',
             f'本轮 {len(rows)} 项待确认。沿用历史核对号与当前 S 编号；下列候选来自旧稿，尚未视为本轮确认。', '',
             '可直接修改“预估名称（可改）”，再把“我的确认／备注”改成“已确认”；也可直接在确认栏填写实际名称，或在聊天中按 `21号 01=名称` 回复。未回答项保留 unknown。', '',
             '先核对名称、类别和空间范围；名称确认后，再逐张复核人员连通与可定位门洞。当前五图均无门洞红点，既有关系仍需复核。', '',
             f'![{number}号完整原图核对总图]({rel(target / OVERVIEWS[number])})', '',
             f'[原图]({data["image"]["file"]}) · [现有标注 SVG](标注.svg)', '']
    if number in [22, 23]:
        ids = ['S024'] if number == 22 else ['S092','S096','S133','S146','S150','S197','S202']
        lines += ['**范围属性重点：**' + '、'.join(ids) + ' 请同时说明“露天／挑空”或“室内可步入”，用于确定是否计入室内相对面积。', '']
    previews = []
    groups = chunks(rows)
    for index, group in enumerate(groups, 1):
        start,end = group[0]['number'],group[-1]['number']
        title = start if start == end else start + '—' + end
        x0,y0,x1,y1 = bounds(group)
        crop = (max(0, math.floor(x0)-75), max(0, math.floor(y0)-75),
                min(image.width, math.ceil(x1)+75), min(image.height, math.ceil(y1)+75))
        raw = image.crop(crop)
        marked = raw.copy()
        draw = ImageDraw.Draw(marked)
        for j,row in enumerate(group):
            points = [(x-crop[0], y-crop[1]) for x,y in row['polygon_px']]
            draw.line(points + [points[0]], fill=COLORS[j], width=3)
        if number in [21,24,25]:
            raw = raw.rotate(90, expand=True)
            marked = marked.rotate(90, expand=True)
        scale = max(1, min(3, 1900 / max(marked.size)))
        size = tuple(round(v*scale) for v in marked.size)
        marked = marked.resize(size, Image.Resampling.LANCZOS)
        # Put the number legend outside the drawing so room names remain visible.
        header = Image.new('RGB', (size[0], 55 + size[1]), '#f8fafc')
        header.paste(marked, (0,55))
        label = ImageDraw.Draw(header)
        for j,row in enumerate(group):
            label.text((12+j*max(115, size[0]//len(group)), 12), row['number']+'｜'+row['id'],
                       font=ImageFont.truetype(FONT, 23), fill=COLORS[j])
        png = target / f'局部_{index:02d}_核对{start}-{end}.png'
        rawfile = target / f'局部_{index:02d}_无标记原图.png'
        header.save(png)
        raw.resize(size, Image.Resampling.LANCZOS).save(rawfile)
        previews.append((title, header.copy()))
        lines += [f'### {title}｜' + '、'.join(r['id'] for r in group), '',
                  f'![核对{title}局部图；彩框与上方同色编号对应]({rel(png)})', '',
                  f'[查看同范围无标记原图]({rel(rawfile)})', '',
                  '| 核对号 | S编号 | 预估名称（可改） | 备选名称 | 依据与把握 | 我的确认／备注 | 核对号（重复） |',
                  '| --- | --- | --- | --- | --- | --- | --- |']
        for row in group:
            candidates = re.split(r'\s+/\s+', ' / '.join(row['candidates']))
            first = candidates[0] if candidates else '暂无可靠候选'
            other = '；'.join(candidates[1:]) or '—'
            evidence = row['evidence']
            if len(candidates) > 1:
                evidence = '各候选共用依据：' + evidence + '；现有证据不能可靠区分。'
            evidence += ' 把握：' + row['confidence'] + '（旧稿预估，待本轮核对）。'
            lines.append('| ' + ' | '.join(map(field, [row['number'],row['id'],first,other,evidence,'待确认',row['number']])) + ' |')
        lines.append('')
    original = re.sub(r'\*\*核对方式：\*\*.*?(?=\n\n|\Z)',
                      '**核对方式：**见下方同一文档中的固定核对号、局部图和填写栏；材料已持久保存于工作区。', original, flags=re.S)
    original = original.replace('候选及本轮核对号仅保存在临时核对图和清单', '候选及本轮核对号见下方填写区和工作区核对图')
    original = original.replace('候选名称与连续核对号仅放临时材料', '候选名称与连续核对号见下方填写区')
    mdfile.write_text(original.rstrip() + '\n\n' + '\n'.join(lines) + '\n')
    # Review sheets help inspect all crops without opening dozens of files.
    for batch in range(0, len(previews), 8):
        selected = previews[batch:batch+8]
        sheet = Image.new('RGB', (1440, math.ceil(len(selected)/2)*620), 'white')
        for i,(title, thumbnail) in enumerate(selected):
            thumbnail.thumbnail((700,560))
            x,y=(i%2)*720,(i//2)*620
            ImageDraw.Draw(sheet).text((x+10,y+5),f'{number}号 核对{title}',font=ImageFont.truetype(FONT,24),fill='black')
            sheet.paste(thumbnail,(x,y+45))
        sheet.save(target / f'目检页_{batch//8+1:02d}.jpg', quality=92)
    results.append(dict(project=project.name, spaces=len(data['spaces']), pending=len(rows),
                        local_groups=len(groups), markdown=str(mdfile)))
    print(number, 'tables',len(rows),'local groups',len(groups),flush=True)
(BASE / '材料清单.json').write_text(json.dumps(results, ensure_ascii=False, indent=2))
