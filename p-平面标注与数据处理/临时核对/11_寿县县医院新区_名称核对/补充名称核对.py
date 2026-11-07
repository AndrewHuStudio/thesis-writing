from pathlib import Path
import hashlib
import json
import re
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'p-平面标注与数据处理/标注试样/11_寿县县医院新区'
TMP = Path(__file__).resolve().parent
DATA = json.loads((OUT / 'annotation.json').read_text())
SP = {s['id']: s for s in DATA['spaces']}
SOURCE = Image.open(OUT / DATA['image']['file']).convert('RGB')
FONT = '/System/Library/Fonts/STHeiti Medium.ttc'
PALETTE = ['#b91c1c', '#0369a1', '#6d28d9', '#0f766e', '#a16207', '#be185d']


def font(size):
    return ImageFont.truetype(FONT, size)


def bounds(sid):
    p = SP[sid]['polygon_px']
    return min(x for x, y in p), min(y for x, y in p), max(x for x, y in p), max(y for x, y in p)


# Each item retains its stable S identifier. Candidates stay in the review material.
ROWS = [
    ('S001', '顶部弧形区域', '弧形门厅／平台', '室外平台／雨棚下区域', '仅见弧形外缘与入口相邻；无可靠用途文字。两候选共用形态依据，室内外属性不能据此判断。把握：低。'),
    ('S004', '住院药房北排，卫生间右侧', '暂无可靠候选', '—', '有短标签但字形模糊，无足够房间级功能依据。把握：低。'),
    ('S005', '住院药房北排，办公左侧', '主任办公室', '—', '放大文字疑似“主任办公室”，中部字形与门线相叠；依文字提出候选。把握：中。'),
    ('S007', '住院药房北排，办公右侧', '贵重药库', '贵重药房', '文字疑似“贵重药…”；两候选共用该文字线索，末字不清，药房位置只作背景。把握：低。'),
    ('S011', '上部西侧电梯前室北端小间', '暂无可靠候选', '—', '短标签不清，未见足以确定用途的设备；不能只按邻近电梯命名。把握：低。'),
    ('S015', '上部西侧通道南侧，男女卫左侧大间', '示教室', '—', '放大标签疑似“示教室”，前两字仍模糊；未用房间大小作为名称证据。把握：中。'),
    ('S020', '入院处置右侧，上方小间', '暂无可靠候选', '—', '标签很小，文字与墙线混合；仅知邻近出入院手续区，缺乏房间级证据。把握：低。'),
    ('S021', '入院处置右侧，中间小间', '暂无可靠候选', '—', '短标签无法可靠辨认，不能从相邻小间的配置推定名称。把握：低。'),
    ('S019', '入院处置下方大间', '暂无可靠候选', '—', '该轮廓内未见可可靠辨认的房名或专用设备。把握：低。'),
    ('S023', '出入院手续区内，南排左间', '财务室', '结算室', '短标签首字疑似财务相关但不清；两候选还仅依出入院背景推测，无法区分。把握：低。'),
    ('S024', '出入院手续区内，南排右间', '暂无可靠候选', '—', '虽有两字标签，当前像素不能可靠还原；仅依手续片区不足以命名。把握：低。'),
    ('S027', '职工餐厅西北辅助房，上排左间', '暂无可靠候选', '—', '标签疑含“餐厅”，后续字不清；仅依餐饮背景不能判定更衣、库房等用途。把握：低。'),
    ('S028', '职工餐厅西北辅助房，上排右间', '暂无可靠候选', '—', '与左邻并列，短标签模糊；不能据并列关系补成男女用房。把握：低。'),
    ('S029', '职工餐厅西北辅助房，下排左间', '暂无可靠候选', '—', '短标签不可可靠辨认；只知属于餐厅支持区域。把握：低。'),
    ('S030', '职工餐厅北侧，右列中间长间', '备餐间', '—', '文字疑似“备餐”，但原图缩印较重；餐厅邻接位置只提供背景。把握：低。'),
    ('S031', '职工餐厅北侧，右列最下小间', '仓库', '—', '短标签疑似“仓库”，字形不够稳定，缺乏可识别储藏设备。把握：低。'),
    ('S035', '职工餐厅东侧大面积开放区域', '室外食堂', '室外活动区', '中央文字疑含“室外”；两候选共用该线索与餐厅邻接背景，后续字不清，室外属性也需确认。把握：低。'),
    ('S036', '餐饮东北楼梯左侧，最上小间', '主食库', '—', '放大标签疑似“主食库”，首字边缘模糊。把握：中。'),
    ('S037', '餐饮东北楼梯左侧，第二小间', '副食库', '—', '放大标签疑似“副食库”，与上间相邻仅作背景。把握：中。'),
    ('S038', '餐饮东北楼梯左侧，第三小间', '调料库', '—', '放大标签疑似“调料库”，缩印导致笔画粘连。把握：低。'),
    ('S039', '餐饮东北楼梯左侧，第四小间', '冷库', '—', '短标签疑似“冷库”，但首字仍需确认，未见可独立证明冷库的设备。把握：低。'),
    ('S042', '餐饮东侧通道南侧，东南楼梯左上', '餐具洗涤间', '餐具消毒间', '标签疑含“餐具”；两候选共用该文字线索，洗涤或消毒字样不能可靠区分。把握：低。'),
    ('S044', '餐饮东南南排，最左小间', '餐厅办公', '—', '放大短标签疑似办公相关；餐饮片区本身不足以确定具体职能。把握：低。'),
    ('S045', '餐饮东南南排，中间小间', '暂无可靠候选', '—', '标签存在但字形不稳定；无可靠设施证据，不强补用途。把握：低。'),
    ('S046', '餐饮东南南排，东南楼梯左侧大间', '财务室', '—', '放大标签疑似“财务室”，前两字仍需人工核对。把握：低。'),
    ('S075', '影像中心北排，CR／DR组第一间', 'CR', '—', '放大图可辨“CR”字母；本次仅列候选供确认，不展开缩写或写入核心数据。把握：高。'),
    ('S076', '影像中心北排，CR／DR组第二间', 'CR', '—', '放大图可辨“CR”字母；与左邻相同不作为独立命名依据。把握：高。'),
    ('S079', '影像中心北排，牙片机右侧', '钼靶机', '—', '放大标签接近“钼靶机”，首字因缩印较模糊，尚待确认。把握：中。'),
    ('S089', '影像中心中排，病人准备及控制右侧大间', '胃肠透视', '—', '放大标签疑似“胃肠透视”，中部笔画粘连，依文字提出候选。把握：中。'),
    ('S131', '儿科南排，两间隔离诊室之间左小间', '隔离区卫生间', '—', '可见便器图形，标签与图形重叠；支持卫生间候选，男女及完整原名不能确定。把握：中。'),
    ('S132', '儿科南排，两间隔离诊室之间右小间', '隔离区卫生间', '—', '可见便器图形，文字压在设备及墙线上；支持卫生间候选，男女及完整原名待确认。把握：中。'),
    ('S135', '儿科门厅东侧，治疗室右侧座椅房间', '儿科输液室', '儿科留观室', '可见成排座椅，文字被座椅线条遮挡；两候选共用座椅及儿科背景依据，无法仅据此区分。把握：低。'),
    ('S180', '西药房西侧，公共卫生间与值班之间', '贵重药品库', '—', '放大图文字较清楚地接近“贵重药品库”；仍作为待确认候选保留。把握：高。'),
    ('S154', '急诊西侧床位组，最上房间', '留观室', '急诊诊室', '可见床位，标签似含“诊室”但前缀不清；两候选共用床位及急诊背景，不能据床位判定具体用途。把握：低。'),
    ('S160', '急诊西侧床位组，中间房间', '观察病房', '留观室', '文字疑似“观察病房”且可见床位；留观室共用床位依据，完整原名仍需核对。把握：中。'),
    ('S164', '急诊西侧床位组，EICU上方房间', '内科诊室', '—', '放大文字疑似“内科诊室”，字与床位线叠压；仅提出文字候选。把握：中。'),
    ('S167', '急诊手术室南侧，护士站右侧', '器械、药品', '—', '放大文字疑似“器械、药品”，末字边缘仍模糊；不据此扩展成未经确认的库房名称。把握：中。'),
]

ITEMS = []
for n, row in enumerate(ROWS, 1):
    sid, location, candidate, alternative, evidence = row
    ITEMS.append(dict(number=f'{n:02d}', sid=sid, location=location,
                      candidate=candidate, alternative=alternative, evidence=evidence))
BY_ID = {i['sid']: i for i in ITEMS}
assert len(ITEMS) == len(BY_ID) == 37
assert set(BY_ID) == {s['id'] for s in DATA['spaces'] if s['type'] == 'unknown'}

GROUPS = [
    ('顶部弧形区域', (770, 25, 1660, 300), ['S001'], [160], 'left'),
    ('住院药房北排', (320, 250, 1230, 485), ['S004', 'S005', 'S007', 'S011'], [295, 308, 322, 335], 'left'),
    ('出入院支持用房', (310, 480, 1110, 695), ['S015', 'S020', 'S021', 'S019', 'S023', 'S024'], [540, 552, 596, 635, 650, 661], 'left'),
    ('职工餐厅西北辅助房', (1270, 255, 1640, 580), ['S027', 'S028', 'S029', 'S030', 'S031'], [300, 330, 365, 400, 500], 'right'),
    ('餐厅东侧开放区域', (1610, 260, 1980, 685), ['S035'], [510], 'right'),
    ('餐饮东侧及南排辅助房', (1730, 260, 2120, 685), ['S036', 'S037', 'S038', 'S039', 'S042', 'S044', 'S045', 'S046'], [300, 350, 400, 450, 560, 605, 630, 655], 'right'),
    ('影像中心', (1390, 1030, 1970, 1470), ['S075', 'S076', 'S079', 'S089'], [1110, 1150, 1190, 1320], 'right'),
    ('儿科南排', (490, 1715, 1160, 1855), ['S131', 'S132', 'S135'], [1760, 1788, 1835], 'left'),
    ('药房支持用房', (1250, 2200, 1450, 2380), ['S180'], [2270], 'left'),
    ('急诊', (310, 2340, 760, 2660), ['S154', 'S160', 'S164', 'S167'], [2400, 2470, 2535, 2610], 'left'),
]


def mark(draw, item, xy, scale):
    pts = [xy(x, y) for x, y in SP[item['sid']]['polygon_px']]
    color = item['color']
    draw.line(pts + [pts[0]], fill=color, width=max(3, round(scale * 2)))
    x1, y1, x2, y2 = bounds(item['sid'])
    # Badges use a corner, leaving original central room lettering visible.
    x, y = xy(x1 + 10, y1 + 10)
    if item['sid'] == 'S001':
        x, y = xy(1200, 120)
    size = max(22, round(scale * 13))
    f = font(size)
    w = draw.textlength(item['number'], font=f) + 10
    draw.rounded_rectangle((x - 4, y - 3, x + w, y + size + 5), radius=4, fill='white', outline=color, width=2)
    draw.text((x, y), item['number'], font=f, fill=color)


for g, (title, box, sids, ys, side) in enumerate(GROUPS):
    for sid in sids:
        BY_ID[sid].update(group=title, color=PALETTE[g % len(PALETTE)])

# Preserve the entire original in a single high-resolution overview.
z = 2
im = Image.new('RGB', (SOURCE.width * z + 120, SOURCE.height * z + 180), '#f8fafc')
im.paste(SOURCE.resize((SOURCE.width * z, SOURCE.height * z)), (60, 130))
dr = ImageDraw.Draw(im)
dr.text((60, 25), '11号 寿县县医院新区｜37项名称待确认｜核对号01—37', font=font(42), fill='#0f172a')
dr.text((60, 82), '完整原图与彩框总览；逐项S编号、引线及原字放大见标注说明中的各片区图。', font=font(27), fill='#475569')
for item in ITEMS:
    mark(dr, item, lambda x, y: (60 + x * z, 130 + y * z), z)
im.save(TMP / '11号_名称核对总图.png')
im.resize((1252, 1675)).save(TMP / '11号_名称核对总图_预览.jpg', quality=92)

# Local views add ordered sidebar labels and horizontal leaders; no pair crosses.
for g, (title, box, sids, ys, side) in enumerate(GROUPS, 1):
    scale, bar, gap, top = 3, 900, 100, 110
    x1, y1, x2, y2 = box
    w, h = (x2 - x1) * scale, (y2 - y1) * scale
    final_y = top - 80
    for sy in ys:
        final_y = max(top + (sy - y1) * scale, final_y + 100)
    ih = max(h + top + 50, final_y + 100)
    img = Image.new('RGB', (w + bar + gap + 60, ih), '#f8fafc')
    ox = bar + gap if side == 'left' else 30
    img.paste(SOURCE.crop(box).resize((w, h)), (ox, top))
    dd = ImageDraw.Draw(img)
    dd.text((30, 25), f'{g:02d} {title}｜沿用总图核对号', font=font(30), fill='#0f172a')
    xy = lambda x, y: (ox + (x - x1) * scale, top + (y - y1) * scale)
    last_y = top - 80
    for sid, sy in zip(sids, ys):
        item = BY_ID[sid]
        a, b, c, e = bounds(sid)
        sx = a if side == 'left' else c
        if sid == 'S001':
            sx = 995  # Actual arc boundary at y=160 is checked below.
            poly = SP[sid]['polygon_px']
            intersections = []
            for (ax, ay), (bx, by) in zip(poly, poly[1:] + poly[:1]):
                if min(ay, by) <= sy < max(ay, by):
                    intersections.append(ax + (sy - ay) * (bx - ax) / (by - ay))
            sx = min(intersections)
        if sid == 'S035':
            sx = 1958
        px, py = xy(sx, sy)
        port_x = ox - 30 if side == 'left' else ox + w + 30
        label_y = max(py, last_y + 100)
        last_y = label_y
        end_x = bar - 25 if side == 'left' else ox + w + gap
        item['leader'] = [[px, py], [port_x, py], [end_x, label_y]]
        dd.line([tuple(p) for p in item['leader']], fill=item['color'], width=2)
        lx = 25 if side == 'left' else end_x + 20
        dd.text((lx, label_y - 30), f'{item["number"]}｜{sid} 名称待确认', font=font(31), fill=item['color'])
        dd.text((lx, label_y + 14), f'候选：{item["candidate"]}', font=font(27), fill='#334155')
        mark(dd, item, xy, scale)
    assert last_y + 60 < ih, title
    name = f'{g:02d}_{title}_核对放大.png'
    for sid in sids:
        BY_ID[sid]['detail_image'] = name
    img.save(TMP / name)

path = OUT / '标注说明.md'
original = path.read_text()
backup = TMP / '修改前备份'
backup.mkdir(exist_ok=True)
if not (backup / path.name).exists():
    (backup / path.name).write_text(original)
assert '## 名称逐项核对表' not in original, 'Protect an existing review table.'
rel = '../../临时核对/11_寿县县医院新区_名称核对/'
parts = [
    '## 名称逐项核对表', '',
    '本表依据当前 annotation.json 的未确认清单逐项核对原图，共 **37项：35个房间、2个开放区域（S001、S035）**。其中部分原字放大后已有较可靠候选，仍列在表中供你确认；候选未写入 JSON 或 SVG。', '',
    '核对号按相邻片区组织并固定，保留原 S 编号：顶部弧形区→住院药房→出入院支持→餐厅及辅助房→影像→儿科→药房支持→急诊；每组先上后下，同排从左到右。旧说明引用的 /tmp/outpatient11-review/ 已不存在，本轮使用以下工作区核对图与固定映射。', '',
    '**填写方式：**直接修改“预估名称（可改）”，再将“我的确认／备注”改为“已确认”；或直接在确认栏填写实际名称。也可在聊天中回复 `01=名称，02=名称`，支持分批填写。最右一列只是重复核对号，不是答案栏。', '',
    '**开放区域请另填面积属性：**01／S001、17／S035 除名称外，还需注明“露天／挑空，不计室内面积”或“室内可步入，计室内面积”；目前沿用草稿面积口径，不凭候选名称调整。', '',
    '[查看原图](11_寿县县医院新区_原图.jpg)｜[查看具名标注](标注.svg)｜[打开高清核对总图](' + rel + '11号_名称核对总图.png)', '',
    '![完整原图名称核对总览](' + rel + '11号_名称核对总图.png)', '',
    '总览保留完整原图并显示全部37个框与核对号；下列片区图提供侧栏引线及放大原字，编号与表格一一对应。', '',
]
for title, box, sids, ys, side in GROUPS:
    parts += ['### ' + title + f'（{BY_ID[sids[0]]["number"]}—{BY_ID[sids[-1]]["number"]}）', '',
              '![' + title + '核对放大](' + rel + BY_ID[sids[0]]['detail_image'] + ')', '',
              '| 核对号 | S编号 | 位置 | 预估名称（可改） | 备选名称 | 依据与把握 | 我的确认／备注 | 核对号（重复） |',
              '| --- | --- | --- | --- | --- | --- | --- | --- |']
    for sid in sids:
        i = BY_ID[sid]
        status = '待确认；请另填室内外／面积属性' if sid in {'S001', 'S035'} else '待确认'
        vals = [i['number'], sid, i['location'], i['candidate'], i['alternative'], i['evidence'], status, i['number']]
        parts.append('| ' + ' | '.join(vals) + ' |')
    parts += ['']
overview = original.replace('候选用途、依据及把握程度仅放 /tmp/outpatient11-review/ 的临时核对总图与清单，不进入核心JSON。', '候选用途、逐项依据及填写栏见上方“名称逐项核对表”；核对图已保存于工作区临时核对目录，不进入核心JSON。')
anchor = '**类型与数量：**'
idx = overview.index(anchor)
path.write_text(overview[:idx] + '\n'.join(parts) + '\n' + overview[idx:])
(TMP / '核对号映射.json').write_text(json.dumps(ITEMS, ensure_ascii=False, indent=2) + '\n')
print('Wrote 37 review rows and 10 local review images:', path)
