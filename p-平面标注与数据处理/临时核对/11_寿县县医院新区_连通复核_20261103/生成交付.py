from pathlib import Path
from collections import Counter
import html
import importlib.util
import json
import shutil
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[2]
PROJECT = ROOT / 'p-平面标注与数据处理/标注试样/11_寿县县医院新区'
BACKUP = sorted(WORK.glob('修改前备份_*'))[0]
STAGE = WORK / '待核验成果'
STAGE.mkdir(exist_ok=True)
DATA = json.loads((WORK / '连通复核后.json').read_text())
SPACES = {s['id']: s for s in DATA['spaces']}
SOURCE = Image.open(PROJECT / DATA['image']['file']).convert('RGB')
FONT_PATH = '/System/Library/Fonts/STHeiti Medium.ttc'
REL = '../../临时核对/' + WORK.name + '/'


def review_crop(filename, bounds, sids, highlight):
    z = 3
    x0, y0, x1, y1 = bounds
    image = SOURCE.crop(bounds).resize(((x1 - x0) * z, (y1 - y0) * z))
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(FONT_PATH, 42 if x1-x0 > 600 else 30)
    for sid in sids:
        space = SPACES[sid]
        polygon = Polygon(space['polygon_px'])
        pts = [((x - x0) * z, (y - y0) * z) for x, y in space['polygon_px']]
        color = '#d97706' if sid in highlight else '#0369a1'
        draw.line(pts + pts[:1], fill=color, width=4)
        p = polygon.intersection(Polygon([(x0,y0),(x1,y0),(x1,y1),(x0,y1)])).representative_point()
        x, y = (p.x - x0) * z, (p.y - y0) * z
        aliases = {'S168':'楼梯', 'S169':'化验', 'S170':'药房', 'S171':'挂号',
                   'S174':'卫生间', 'S010':'', 'S012':'', 'S026':'',
                   'S040':'交通核', 'S041':'通道', 'S195':'医街'}
        label = sid + ' ' + aliases.get(sid, space['name'])
        # Thin passage labels use the lower edge to preserve nearby door leaves.
        if sid == 'S173':
            x, y = 650, image.height - 45
            label = 'S173 候诊区'
        width = draw.textlength(label, font=font)
        x = max(8, min(image.width - width - 8, x - width/2))
        half = font.size/2 + 4
        draw.rectangle((x-4, y-half, x+width+4, y+half), fill='white', outline=color, width=2)
        draw.text((x, y-font.size/2-2), label, font=font, fill=color)
    image.save(WORK / filename)


review_crop('A01_门厅面积属性.png', (790, 40, 1660, 490), ['S001','S010','S012','S026','S195'], {'S001'})
review_crop('A02_营养食堂面积属性.png', (1260, 255, 2120, 690), ['S032','S035','S040','S041'], {'S035'})
review_crop('K01_急诊西楼梯连接.png', (320, 2620, 620, 2910), ['S168','S169','S170','S171','S173','S174'], {'S168','S171'})

shutil.copy2(PROJECT / DATA['image']['file'], STAGE / DATA['image']['file'])
json_path = STAGE / 'annotation.json'
json_path.write_text(json.dumps(DATA, ensure_ascii=False, indent=2) + '\n')
skill_script = Path('/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts/annotation_tools.py')
spec = importlib.util.spec_from_file_location('annotation_tools', skill_script)
tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tools)
original_place = tools.place_label


def place_label(polygon, space):
    if space['id'] in {'S001', 'S035'}:
        p = polygon.representative_point()
        lines = [space['id'], space['name'], '〔面积属性待确认〕']
        font = 14
        width = max(tools.visual_width(row, font) for row in lines) + 8
        height = len(lines) * (font+2) + 5
        return p.x-width/2, p.y-height/2, width, height, font, lines
    return original_place(polygon, space)


tools.place_label = place_label
tools.render(DATA, json_path, STAGE / '标注.svg')
tree = ET.parse(STAGE / '标注.svg')
root = tree.getroot()
ns = {'s':'http://www.w3.org/2000/svg'}
texts = root.findall('s:text', ns)
texts[1].text = '房名已同步；2项室内外属性、1项关键连通待核对'
texts[-1].text = '标签：S编号＋具体名称＋〔标准功能类别〕；P红点：门洞／无门开口；E粉圈：建筑入口；黄色：面积属性待核。'
# Put the paired gallery entrance captions on their respective outside edges.
for relation in DATA['relations']:
    if relation['id'] not in {'E22','E23','E24','E25','E26'}:
        continue
    group = root.find('.//s:g[@id="' + relation['id'] + '"]', ns)
    rect = group.find('s:rect', ns)
    label = group.find('s:text', ns)
    leader = group.find('s:line', ns)
    x,y = relation['position_px']
    width,height = float(rect.get('width')),float(rect.get('height'))
    bx = x-width-35 if '西侧' in relation['name'] else x+35
    by = y-height/2
    rect.set('x',str(bx)); rect.set('y',str(by))
    label.set('x',str(bx+7)); label.set('y',str(by+float(label.get('font-size'))+3))
    leader.set('x2',str(bx+width/2)); leader.set('y2',str(by+height/2))
# Prevent label backgrounds from hiding openings: opening groups render above space labels.
tree.write(STAGE / '标注.svg', encoding='unicode')

records = json.loads((WORK / '关系处理记录.json').read_text())
types = Counter(s['type'] for s in DATA['spaces'])
relations = Counter(r['type'] for r in DATA['relations'])
opening_list = [o for r in DATA['relations'] for o in r.get('openings', [])]
located = sum(bool(r.get('openings')) for r in DATA['relations'] if r['type']=='access')
original = (BACKUP / '标注说明.md').read_text()
# Preserve every original table row, answer, candidate, evidence and picture reference verbatim.
start = original.index('### 顶部弧形区域')
end = original.index('**类型与数量：**')
original_tables = original[start:end]
type_summary = '、'.join(f'{tools.TYPE_NAMES[k]} {v}个' for k,v in types.items())
lines = [
    '# 11_寿县县医院新区｜房名同步与连通复核', '',
    '**当前状态（2026-11-03）：**房名填写已读取并同步；37项填写中36项落实到保留空间，14／S029按“直接和下面餐厅打通”并入S032职工餐厅。保留194个空间／区域，稳定S编号不重排。', '',
    '**尚未完成：**1个关键连通问题（K01），2个室内外／面积属性问题（A01、A02）。全部房名均已有明确文字；S001和S035因属性未明暂保留unknown及原草稿面积口径，所以正式检查仍报告names_complete=false。这不表示仍有37项房名待填。', '',
    f'[查看原图]({DATA["image"]["file"]})｜[查看当前具名标注及红点](标注.svg)｜[原始填写及四文件备份]({REL}{BACKUP.name}/标注说明.md)', '',
    '## 需要你填写的位置', '',
    '请直接填写下方3处“我的确认／备注”；已填过的房名无需重复填写。', '',
    '### A01｜S001 门厅：面积属性', '',
    f'![A01：弧形门厅及相邻交通核]({REL}A01_门厅面积属性.png)', '',
    '**问题：**S001门厅属于室内可步入空间，还是露天／雨棚下且不计室内面积？', '',
    '**我的判断：**你已确认名称“门厅”；弧线和入口能定位该空间，但这张平面不能可靠证明其上盖及室内外属性。暂保留原面积口径，不自动按名称分类。', '',
    '**我的确认／备注：**待填写（室内可步入，计室内面积；或露天／雨棚下，不计室内面积）', '',
    '### A02｜S035 营养食堂：面积属性', '',
    f'![A02：营养食堂与职工餐厅及东北交通核]({REL}A02_营养食堂面积属性.png)', '',
    '**问题：**S035营养食堂是否属于室内可步入、计入室内面积的空间？', '',
    '**我的判断：**名称以你的“营养食堂”为准；原“室外食堂”候选已撤回，但名称确认并未同时确认室内外属性，不能据此自动调整面积分母。', '',
    '**我的确认／备注：**待填写（室内，计室内面积；或露天／挑空，不计室内面积）', '',
    '### K01｜S168 急诊西楼梯与S173候诊区', '',
    f'![K01：急诊西楼梯S168、挂号S171及候诊区S173]({REL}K01_急诊西楼梯连接.png)', '',
    '**问题：**S168楼梯的室内出口连接S171挂号，还是经未画清的前室直接连接S173候诊区（或该核一层仅对外出入）？', '',
    '**我的判断：**原图能确认该核西侧对外入口E15；S168与S173之间隔着S169—S171，未见可证明直接连通的门。因此撤下旧R174，不跨过挂号编造直达边。其他急诊房间与门厅的主要通行已按可见门口保留。', '',
    '**我的确认／备注：**待填写（写S168实际直接相连的S编号；也可说明仅对外出入）', '',
    '## 本轮落实与连通复核结果', '',
    '**房名以你的填写为准：**S015=消防控制室、S019=入院处理、S027=餐车停放、S028=餐车清洗、S042=营养液配置、S044=管理办公、S045=主任办等均覆盖旧候选。未把候选或最右侧重复编号当作答案。', '',
    '**合并与面积：**S029并入S032，原S029编号停用，不复用于其他房间；相关R037改接保留的S032。原始填写完整保留在后文及备份。合并只补齐两片之间原有4像素概念边界缝隙，不扩张其他房间。三个内院S137—S139仍按courtyard排除面积，未添加穿越内院的人员边。S001、S035属性确认前继续按草稿口径归一化。', '',
    '**范围与精度：**仅本图一层；住院药房及手续、餐饮、感染门诊、影像、儿科、输液／急诊、药房与公共医街分别复核。共墙及服务窗口不自动构成人员通行；无记录不作为不连通负例。', '',
    '| 片区 | 本轮处理 |',
    '| --- | --- |',
    '| 北侧药房及手续 | 补药房与西北交通核实际门；电梯前室先接S014，再进入医街；将S014延伸到图上连续的电梯前区。手续区东墙不直连医街。 |',
    '| 餐饮 | 按填写合并S029；营养食堂经职工餐厅、餐饮东侧通道组织通行，不跨餐厅直接连中轴医街；东北楼梯南端与S041按布局推断连接。 |',
    '| 感染门诊 | 按两侧诊室实际前后门分别连候诊通道及工作人员通道；化验、检查室入口按图改接S062，不把X光与控制共墙记为门。 |',
    '| 影像 | CR／DR未见北门的共墙边撤下；小机房可见北门保留；修正准备区卫生间门向及片库北入口。东北楼梯经办公门厅连接，阅片经S109而非跨房直连医街。 |',
    '| 儿科 | 保留诊室、隔离观察、治疗／输液的可见前后门；卫生设施不改变隔离观察整体名称；候诊与西侧通道按连续布局连接。 |',
    '| 输液与急诊 | 核对肌注、诊室、注射配液、观察诊室、手术及抢救室的实际门；补急诊输液接西侧后通道；急诊西核仅留K01关键疑点。 |',
    '| 药房 | 贵重物品库门改向西药房；补药房与取药后场的实际门，服务界面继续独立记service；未从柜台窗口推断患者穿行。 |', '',
    '**建筑入口：**原E01—E16保持编号，E06/E07污物出口中心按原图略作校正；补E17北侧门厅入口、E18上部西侧通道西入口、E19消防控制室西入口、E20餐饮东侧通道东入口、E21营养食堂北入口，以及E22—E26连廊北段两侧、中段西侧、南段两侧的可见对外／内院门组。连续多扇的同一入口按门组近似中心保存。入口分别接各自空间，不建立共享室外节点，也不通过内院节点虚构室内捷径。', '',
    f'**标注规模：**194个空间／区域；{type_summary}。', '',
    f'**关系及红点：**{len(DATA["relations"])}条关系，其中access {relations["access"]}条、entrance {relations["entrance"]}条、service {relations["service"]}条、shared_wall {relations["shared_wall"]}条。已定位{len(opening_list)}个开口（door {sum(o["kind"]=="door" for o in opening_list)}个、open_passage {sum(o["kind"]=="open_passage" for o in opening_list)}个），对应{located}条access；另有{relations["access"]-located}条概念access无定位红点。P编号在本轮首次建立，后续保持稳定。', '',
    '**本轮不细究的内部细节：**餐车清洗S028的内部小门、药房更衣区卫生间S185与相邻更衣间的具体开门、各核内部电梯／楼梯细分及半开放柜台的小缺口不逐项追问。证据不足的内部连接暂不记录，不代表已确认不相通。', '',
    '### 未定位门位的概念连接及依据', '',
]
for item in records['concepts']:
    r = item['relation']
    lines.append(f'- {r["id"]}｜{r["source"]}—{r["target"]}：{item["note"]}')
lines += ['', '### 核验口径', '',
    '本轮核验包括JSON结构、多边形与面积、稳定编号、原图哈希、用户填写保留、红点和空间对一一对应及实际渲染复核。正式validate --check-dir的结果另记在本节；K01和A01/A02未解决前不宣布整图完成。', '',
    '## 已处理的房名填写（原始内容保留）', '',
    '下方37项为你本轮的原始填写，逐行保留候选、依据、答案和旧核对图，供追溯；旧候选及“名称待确认”的图中侧栏不代表当前结果。以“我的确认／备注”原文及上方当前状态为准，已同步项无需再填。14／S029已并入S032。', '',
    original_tables,
]
(STAGE / '标注说明.md').write_text('\n'.join(lines))
print('Prepared staged JSON/SVG/MD; original tables preserved; 1 key connectivity and 2 area questions.')
