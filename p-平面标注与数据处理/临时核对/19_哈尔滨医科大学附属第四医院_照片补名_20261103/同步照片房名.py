from pathlib import Path
import collections
import hashlib
import importlib.util
import json
import re
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon, box

ROOT = Path(__file__).resolve().parents[3]
SAMPLE = ROOT / 'p-平面标注与数据处理/标注试样/19_哈尔滨医科大学附属第四医院门诊外科楼'
OUT = Path(__file__).resolve().parent
BASELINE = json.loads((OUT / '本轮基线.json').read_text())
BACKUP = ROOT / BASELINE['backup']
DATA = json.loads((BACKUP / 'annotation.json').read_text())
MAPPING = json.loads((BACKUP / '本轮核对映射.json').read_text())
MD = (BACKUP / '标注说明.md').read_text()
FONT = '/System/Library/Fonts/STHeiti Medium.ttc'

# 只转录本轮第5—12张19号照片中能够直接辨读的文字。
# 前4张是20号；不作为本脚本的名称、范围或关系依据。
CLEAR = {
    'S005': ('休息区', 'hall', '05、11'),
    'S009': ('主任办公室', 'office', '05、11'),
    'S016': ('诊室', 'consultation', '07、08'),
    'S017': ('诊室', 'consultation', '07、08'),
    'S018': ('诊室', 'consultation', '07、08'),
    'S019': ('诊室', 'consultation', '07、08'),
    'S020': ('诊室', 'consultation', '07、08'),
    'S021': ('换药室', 'treatment', '07、08'),
    'S026': ('银行', 'retail_service', '05'),
    'S032': ('收款', 'registration', '07、08'),
    'S033': ('挂号', 'registration', '07、08'),
    'S034': ('护士站', 'nurse_station', '07、08'),
    'S037': ('诊室', 'consultation', '07、08'),
    'S038': ('商务中心', 'retail_service', '05'),
    'S049': ('儿童输液室', 'treatment', '07、08'),
    'S053': ('主任室', 'office', '07、08'),
    'S059': ('更衣室', 'staff_support', '07、08'),
    'S061': ('库房', 'storage', '07、08'),
    'S062': ('办公室', 'office', '07、08'),
    'S063': ('主任办公室', 'office', '05、09'),
    'S066': ('主任办公室', 'office', '05、09'),
    'S067': ('银行', 'retail_service', '06、12'),
    'S076': ('配药工作间', 'medication_preparation', '05、09'),
    'S077': ('医务', 'service_work_area', '08、10'),
    'S080': ('血型鉴定', 'laboratory', '07、08、10'),
    'S081': ('采血室', 'laboratory', '07、08、10'),
    'S082': ('配血室', 'laboratory', '07、08、10'),
    'S086': ('更衣室', 'staff_support', '07、08'),
    'S089': ('药库', 'storage', '05、09'),
    'S094': ('医护办公', 'office', '07、08、10'),
    'S095': ('洗涤', 'sterile_supply', '07、08、10'),
    'S096': ('消毒', 'sterile_supply', '07、08、10'),
    'S097': ('储血室', 'storage', '07、08、10'),
    'S100': ('储藏室', 'storage', '07、08'),
    'S103': ('诊室', 'consultation', '05、09'),
    'S104': ('诊室', 'consultation', '05、09'),
    'S105': ('收款', 'registration', '05、09'),
    'S106': ('挂号', 'registration', '05、09'),
    'S113': ('观察室', 'observation', '07、08、10'),
    'S116': ('无菌库房', 'storage', '07、08、10'),
    'S119': ('设备用房', 'building_services', '07、08'),
    'S124': ('治疗室', 'treatment', '05、09'),
    'S125': ('诊室', 'consultation', '05、09'),
    'S126': ('诊室', 'consultation', '05、09'),
    'S127': ('诊室', 'consultation', '05、09'),
    'S128': ('电井', 'building_services', '05、09'),
    'S133': ('电井', 'building_services', '07、08'),
    'S151': ('西药', 'pharmacy', '07、08、10'),
    'S152': ('配乳', 'service_work_area', '07、08、10'),
    'S153': ('诊室', 'consultation', '07、08、10'),
    'S154': ('处置室', 'treatment', '07、08、10'),
    'S166': ('更衣休息', 'staff_support', '09'),
    'S168': ('更衣休息', 'staff_support', '09'),
}

# 字形尚不可靠，只进入本图MD；不写入核心JSON的name/type。
CANDIDATES = {
    'S007': ('理赔中心', '暂无其他可靠候选', '照片05、11的四字原注近似此名，第二字仍需核对', '中'),
    'S008': ('图像室', '暂无其他可靠候选', '照片05、11可见三字室名，字形不足以定名', '低'),
    'S010': ('医保账号录入办公室', '医保相关办公室', '照片05、11可见办公桌及长室名；只能较可靠辨出医保、录入、办公室等部分字形', '中'),
    'S011': ('暂无可靠候选', '—', '照片05、11字形仍模糊，不能仅凭相邻办公室命名', '低'),
    'S023': ('月票入口门厅', '暂无其他可靠候选', '照片07、08可读入口门厅；前两字似月票，尚不确定', '中'),
    'S028': ('终端室／交换机房', '暂无其他可靠候选', '照片05的两行室名及房间边界需要核对，不能确定是单间复合用途还是两个小间', '低'),
    'S035': ('配药', '暂无其他可靠候选', '照片07、08可见两字名称，第一字似配，暂不据此确定用途', '中'),
    'S040': ('用药咨询室', '暂无其他可靠候选', '照片05、09的长室名近似此名，仍有模糊字', '中'),
    'S050': ('暂无可靠候选', '—', '照片07、08可见跨近邻区域的长注记，尚不能可靠归属于这个S轮廓', '低'),
    'S054': ('复印室', '暂无其他可靠候选', '照片05的三字原注近似此名，但中间字不够清晰', '中'),
    'S055': ('杂务', '暂无其他可靠候选', '照片06、12的两字室名较小，需再核对字形', '低'),
    'S058': ('杂务', '暂无其他可靠候选', '照片06、12的两字室名较小，不能因交通核对称而套用西侧名称', '低'),
    'S060': ('储品室', '物品室', '照片07、08可辨后三字近似品室，首字仍模糊；两个候选共用此字形线索', '低'),
    'S065': ('保安室', '暂无其他可靠候选', '照片05、09的三字原注似保安室，需核实第二字', '中'),
    'S070': ('值班', '暂无其他可靠候选', '照片12的两字注记较小，暂留候选', '中'),
    'S073': ('财务室', '暂无其他可靠候选', '照片05、09两字尾部可辨为务室，首字仍模糊', '中'),
    'S074': ('副主任办公室', '暂无其他可靠候选', '照片05、09可读主任办公室，前缀字形仍需核对', '中'),
    'S075': ('制剂传递室／成药储存室', '暂无其他可靠候选', '照片05、09在现有轮廓内有上下两处文字，词形和空间是否应分开均未确定', '低'),
    'S079': ('输血前检验室', '输血前检查室', '照片07、08、10可见输血前及室字；检验、检查的末字仍需核对，两候选共用此线索', '中'),
    'S083': ('办公区／更衣室', '暂无其他可靠候选', '照片07、08显示现有S083轮廓内可能包含两个有名小间，名称及拆分范围需一并确认', '中'),
    'S084': ('财务办公室', '暂无其他可靠候选', '照片05、09可读办公室，科室前缀仍需核对', '中'),
    'S085': ('消毒器械房', '消毒供应用房', '照片06、12该房有长室名，字形不足以区分两个候选', '低'),
    'S087': ('财务办公室', '暂无其他可靠候选', '照片05、09有办公室字形，前缀模糊；不沿用上下相邻房名', '低'),
    'S090': ('中草药剂室', '中草药调剂室', '照片05、09可读中草药及室；中间字数和字形尚不可靠', '中'),
    'S092': ('贮存室', '贮管室', '照片07、08显示三字名称与22.5平方米原注，第二字不清；面积原注不录入JSON', '低'),
    'S098': ('医保办公室', '暂无其他可靠候选', '照片05、09可见办公室字形，医保二字仍不够清楚', '中'),
    'S099': ('暂无可靠候选', '—', '照片05、09为上下两行室名，仍不能完整可靠辨读', '低'),
    'S101': ('暂无可靠候选', '—', '照片05、09为独立小间，室名文字仍模糊', '低'),
    'S114': ('备血室', '暂无其他可靠候选', '照片07、08、10的三字名称似备血室，第二字仍需核对', '中'),
    'S115': ('集中供氧室', '暂无其他可靠候选', '照片07、08、10为长室名，当前只能提出字形候选，不能凭医院常规配置定名', '低'),
    'S117': ('暂无可靠候选', '—', '照片07、08、10可见较长室名，不能可靠辨出全名', '低'),
    'S118': ('洗白室', '暂无其他可靠候选', '照片07、08、10的三字字形近似此名，首二字仍不确定', '低'),
    'S137': ('设备井', '暂无其他可靠候选', '照片05、09可见小井道注记，字形需核对；不凭狭窄轮廓定名', '中'),
    'S138': ('设备井', '暂无其他可靠候选', '照片07、08可见小井道注记，字形需核对', '中'),
    'S139': ('观察、监护', '暂无其他可靠候选', '照片07、08、10在现有轮廓中可见两个用途字样，需确认是否整体记录及原文', '中'),
    'S140': ('预检急诊', '暂无其他可靠候选', '照片07、08、10为四字注记，首二字字形仍需确认', '中'),
    'S141': ('影像、值班', '暂无其他可靠候选', '照片05、09有两组文字，字形和功能范围仍不清晰', '低'),
    'S146': ('影像、值班', '暂无其他可靠候选', '照片09下缘仅有较小室名字样，不能可靠定名', '低'),
    'S147': ('暂无可靠候选', '—', '照片09下缘文字较小且模糊，维持unknown', '低'),
    'S174': ('暂无可靠候选', '—', '本轮19号照片没有清楚覆盖此房间；原图未提供可靠房名', '低'),
    'S175': ('暂无可靠候选', '—', '本轮19号照片没有清楚覆盖此房间；原图未提供可靠房名', '低'),
}

spaces = {s['id']: s for s in DATA['spaces']}
assert set(CLEAR).isdisjoint(CANDIDATES)
assert set(CLEAR) | set(CANDIDATES) == {m['id'] for m in MAPPING}
for sid, (name, kind, _) in CLEAR.items():
    spaces[sid]['name'] = name
    spaces[sid]['type'] = kind

module_path = Path('/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts/annotation_tools.py')
spec = importlib.util.spec_from_file_location('annotation_tools', module_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.normalize(DATA)

source = SAMPLE / DATA['image']['file']
assert hashlib.sha256(source.read_bytes()).hexdigest() == BASELINE['hashes'][source.name]
image = Image.open(source).convert('RGB')
polys = {sid: Polygon(s['polygon_px']) for sid, s in spaces.items()}
audit = []


def badge_location(sid, number):
    poly = polys[sid]
    minx, miny, maxx, maxy = poly.bounds
    for size in [16, 14, 12, 10, 8]:
        f = ImageFont.truetype(FONT, size)
        bounds = f.getbbox(number)
        bw, bh = bounds[2] - bounds[0] + 6, size + 5
        # 在内部四角和网格中寻找少遮字的位置，优先上方空白。
        options = []
        for fy in [.08, .82, .22, .65, .4]:
            for fx in [.06, .72, .38, .18, .56]:
                x = minx + fx * max(0, maxx - minx - bw)
                y = miny + fy * max(0, maxy - miny - bh)
                rect = box(x, y, x + bw, y + bh)
                if not poly.buffer(-1).covers(rect):
                    continue
                grey = image.crop((int(x), int(y), int(x + bw), int(y + bh))).convert('L')
                dark = sum(v < 110 for v in grey.getdata()) / max(1, grey.width * grey.height)
                options.append((dark + fy * .015, x, y))
        if options:
            _, x, y = min(options)
            return x, y, bw, bh, size
    raise RuntimeError('内部无法放入核对数字: ' + sid)


badges = {m['id']: badge_location(m['id'], m['number']) for m in MAPPING}


def render_crop(records, crop, filename, scale):
    canvas = image.crop(crop).resize((round((crop[2] - crop[0]) * scale), round((crop[3] - crop[1]) * scale)))
    draw = ImageDraw.Draw(canvas)
    for m in records:
        sid = m['id']
        color = '#167044' if sid in CLEAR else '#b66a00'
        points = [((x - crop[0]) * scale, (y - crop[1]) * scale) for x, y in spaces[sid]['polygon_px']]
        draw.line(points + [points[0]], fill=color, width=max(2, round(scale)))
        x, y, bw, bh, fs = badges[sid]
        rect = [(x - crop[0]) * scale, (y - crop[1]) * scale, (x + bw - crop[0]) * scale, (y + bh - crop[1]) * scale]
        draw.rounded_rectangle(rect, radius=2 * scale, fill='white', outline=color, width=max(2, round(scale)))
        f = ImageFont.truetype(FONT, round(fs * scale))
        draw.text((rect[0] + 3 * scale, rect[1]), m['number'], font=f, fill=color)
        audit.append({'file': filename, 'number': m['number'], 'id': sid, 'badge_px': [x, y, bw, bh], 'inside': polys[sid].covers(box(x, y, x + bw, y + bh))})
    canvas.save(OUT / filename, quality=94)


render_crop(MAPPING, (0, 0, image.width, image.height), '名称核对总图_室内编号.jpg', 2)

rows_by_id = {}
for line in MD.splitlines():
    if re.match(r'^\|\s*\d+\s*\|', line):
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        rows_by_id[cells[1]] = cells

sections = re.split(r'(?=^### )', MD.split('## 名称核对填写表', 1)[1], flags=re.M)[1:]
review_sections = []
for index, section in enumerate(sections, 1):
    heading = section.splitlines()[0]
    ids = re.findall(r'^\|\s*\d+\s*\|\s*(S\d+)\s*\|', section, flags=re.M)
    records = [m for m in MAPPING if m['id'] in ids]
    # 远隔区域拆成独立局部；核对号及表格对应关系始终不变。
    clusters = []
    for record in records:
        found = next((c for c in clusters if any(polys[x['id']].distance(polys[record['id']]) < 165 for x in c)), None)
        if found is None:
            clusters.append([record])
        else:
            found.append(record)
    lines = [heading, '']
    for part, cluster in enumerate(clusters, 1):
        bounds = [polys[x['id']].bounds for x in cluster]
        crop = (max(0, int(min(b[0] for b in bounds) - 35)), max(0, int(min(b[1] for b in bounds) - 45)), min(image.width, int(max(b[2] for b in bounds) + 45)), min(image.height, int(max(b[3] for b in bounds) + 50)))
        scale = min(4, 1900 / (crop[2] - crop[0]))
        filename = f'局部_{index:02d}_{part}_室内编号.jpg'
        render_crop(cluster, crop, filename, scale)
        numbers = '、'.join(m['number'] for m in cluster)
        relative = '../../临时核对/' + OUT.name + '/' + filename
        lines += [f'![固定核对号{numbers}，数字在对应轮廓内部]({relative})', '']
    lines += ['| 核对号 | S编号 | 预估名称（可改） | 备选名称 | 依据与把握 | 我的确认／备注 | 核对号（重复） |', '| --- | --- | --- | --- | --- | --- | --- |']
    for m in records:
        sid = m['id']
        old = rows_by_id[sid]
        if sid in CLEAR:
            name, kind, photos = CLEAR[sid]
            cells = [m['number'], sid, name, '—', f'本轮照片{photos}的本房原注可辨为“{name}”，并与19号原图位置对应。类别：{module.TYPE_NAMES[kind]}。把握：高。已据图同步JSON/SVG；这不表示用户已经确认。', old[5], m['number']]
        else:
            candidate, alternative, basis, confidence = CANDIDATES[sid]
            cells = [m['number'], sid, candidate, alternative, basis + f'。把握：{confidence}。JSON保持unknown。', old[5], m['number']]
        # 若基线中有用户修改，则不覆盖填写或其修改后的候选。
        if old[5] not in {'待确认', ''}:
            cells[2:6] = old[2:6]
        lines.append('| ' + ' | '.join(cells) + ' |')
    review_sections.append('\n'.join(lines))

pending = [s['id'] for s in DATA['spaces'] if s['type'] == 'unknown']
types = collections.Counter(s['type'] for s in DATA['spaces'])
overview = MD.split('## 名称核对填写表', 1)[0]
overview = re.sub(r'94 个空间名称尚未确认', f'{len(pending)} 个空间名称尚未确认', overview)
overview = re.sub(r'\*\*类型与数量：\*\*[^\n]+', '**类型与数量：**' + '、'.join(f'{module.TYPE_NAMES[k]} {v} 个' for k, v in types.items()) + '。', overview)
overview = re.sub(r'\*\*名称待确认：\*\*[^\n]+', '**名称待确认：**' + '、'.join(pending) + '。此图尚不能宣布打标完成。', overview)
overview = re.sub(r'\*\*当前核验：\*\*[^\n]+', '**当前核验：**本轮先开展房名、类别与范围核对；正式结构校验和目检结果见下方本轮状态。连通性尚未开始全面复核。', overview)
intro = f'''## 名称核对填写表

本轮整理：2026-11-03。沿用原固定核对号01—94及S编号。{len(CLEAR)}项按照片清晰原文同步名称和类别，剩余{len(pending)}项保持unknown。表中保留全部94行，便于继续修改与回查；“我的确认／备注”保留原填写，图面辨读不冒充用户确认。

**照片归属：**本轮聊天按发送顺序共12张照片，前4张与20号底图一致，不参与本图判断；第5—12张与19号底图一致，作为本轮辨字依据。原始JPG不替换，核对局部使用19号原图叠加固定数字；照片自身未作为本地文件保存。

**填写方式：**可修改预估名称，并在“我的确认／备注”中写“已确认”或实际名称、合并/排除意见。仅空白、待确认或候选仍不视为用户确认。聊天请写“19号：核对号=名称”。

**图示：**数字在对应空间内部；绿色为本轮已据图同步，橙色为仍待确认。无外侧标签和长引线。相邻片区局部与填写表相邻；同一表中远隔的房间拆为多张局部图，编号不重排。图上边框为现有概念轮廓，不代表每条线均为实体墙。

[查看原图]({DATA['image']['file']})｜[查看标注](标注.svg)｜[打开室内编号总图](../../临时核对/{OUT.name}/名称核对总图_室内编号.jpg)

![19号固定01—94核对总图](../../临时核对/{OUT.name}/名称核对总图_室内编号.jpg)

**范围待核：**15/S028、40/S075、47/S083、83/S140需结合房名字样与隔墙确认现有单元的功能范围。其中47/S083可能包含办公区与更衣室两个小间。43—46/S079—S082的既有轮廓包含北侧附间，主体房名与附间用途分开核对。现阶段保留既有S编号与轮廓，未拆分、合并或排除。

**连通性：**保留既有159条关系作为待复核草稿，当前室内定位开口0个；名称更新不表示这些关系已经核实。待用户说“房间标注完毕”后，读取最新填写，落实明确的范围修正，再开始连通性复核。

'''
(SAMPLE / 'annotation.json').write_text(json.dumps(DATA, ensure_ascii=False, indent=2) + '\n')
module.render(DATA, SAMPLE / 'annotation.json', SAMPLE / '标注.svg')
(SAMPLE / '标注说明.md').write_text(overview + intro + '\n\n'.join(review_sections) + '\n')
(OUT / '固定核对映射.json').write_text(json.dumps(MAPPING, ensure_ascii=False, indent=2) + '\n')
(OUT / '内部编号核验.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n')
(OUT / '名称同步记录.json').write_text(json.dumps({'updated': CLEAR, 'pending': pending, 'scope_review': ['S028', 'S075', 'S083', 'S140'], 'photos_used': list(range(5, 13)), 'photos_excluded_as_sample20': list(range(1, 5))}, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'synced': len(CLEAR), 'unknown': len(pending), 'spaces': len(DATA['spaces']), 'relations': len(DATA['relations']), 'local_images': len(list(OUT.glob('局部_*_室内编号.jpg'))), 'all_badges_inside': all(x['inside'] for x in audit)}, ensure_ascii=False))
