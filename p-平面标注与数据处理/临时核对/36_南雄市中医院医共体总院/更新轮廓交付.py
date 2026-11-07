from pathlib import Path
import ast, json, sys, os, re
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon

WORK = Path(__file__).resolve().parent
SAMPLE = WORK.parent.parent / '标注试样' / WORK.name
sys.path.insert(0, '/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts')
import annotation_tools as at

data = json.loads((SAMPLE / 'annotation.json').read_text())
state = json.loads((WORK / 'review_state.json').read_text())
meta = json.loads((WORK / '空间工作索引.json').read_text())
changes = json.loads((WORK / '逐空间补充记录.json').read_text())
index = {m['id']: m for m in meta}
source = Image.open(WORK / '转正原图.png').convert('RGB')
colors = {'A': '#b45309', 'B': '#6d28d9', 'C': '#0369a1', 'D': '#be185d',
          'E': '#4338ca', 'F': '#0f766e', 'G': '#a16207', 'H': '#b91c1c'}

# 只复用纯绘图函数；不执行旧脚本重建名称表、写入数据的主流程。
helper = ast.parse((WORK / '生成核对材料.py').read_text())
nodes = [node for node in helper.body if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef))]
env = {'WORK': WORK, 'SAMPLE': SAMPLE, 'data': data, 'state': state,
       'meta': meta, 'byid': index, 'polys': {m['id']: Polygon(m['shape']) for m in meta},
       'source': source, 'FONT': '/System/Library/Fonts/STHeiti Medium.ttc',
       'COLORS': colors, 'badge_audit': []}
exec(compile(ast.Module(body=nodes, type_ignores=[]), '绘图函数', 'exec'), env)
env['upright_svg']()
import xml.etree.ElementTree as ET
svg = ET.parse(SAMPLE / '标注.svg')
headings = svg.getroot().findall('{http://www.w3.org/2000/svg}text')
headings[0].text = '36号首层：逐空间粗轮廓标注'
headings[1].text = '197个独立空间单元；功能缺失保留unknown；主要连通待核'
# 窄小单元用一行S号和未确认名，避免长标签越界后遮住相邻空间。
ns = {'s': 'http://www.w3.org/2000/svg'}
svg_label_audit = []
for s in data['spaces']:
    group = svg.find('.//s:g[@id="' + s['id'] + '"]', ns)
    poly = Polygon([(y, 2444-x) for x, y in s['polygon_px']])
    old_rect = group.find('s:rect', ns)
    old_box = env['box'](float(old_rect.get('x')), float(old_rect.get('y')),
                         float(old_rect.get('x'))+float(old_rect.get('width')),
                         float(old_rect.get('y'))+float(old_rect.get('height')))
    if s['type'] != 'unknown' and poly.covers(old_box):
        svg_label_audit.append({'id':s['id'], 'inside':True, 'shortened':False})
        continue
    label = s['id'] + ' ' + s['name']
    selected = None
    center = poly.representative_point()
    b = poly.bounds
    candidates = [(center.x, center.y)] + [
        (b[0]+(b[2]-b[0])*fx/20, b[1]+(b[3]-b[1])*fy/20)
        for fy in range(1,20) for fx in range(1,20)]
    for candidate_label in (label,s['id']):
        for size in (14,12,10,9,8,7,6,5,4,3,2):
            width, height = at.visual_width(candidate_label,size)+4, size+4
            options = []
            for xx, yy in candidates:
                rect = env['box'](xx-width/2, yy-height/2, xx+width/2, yy+height/2)
                if poly.covers(rect):
                    options.append((abs(xx-center.x)+abs(yy-center.y),xx,yy,rect))
            if options:
                _,xx,yy,rect = min(options,key=lambda t:t[0])
                selected = size,width,height,xx,yy,rect
                label = candidate_label
                break
        if selected:
            break
    assert selected, ('SVG label needs separate view',s['id'])
    size,width,height,xx,yy,rect = selected
    for child in list(group):
        if child.tag.endswith('}rect') or child.tag.endswith('}text'):
            group.remove(child)
    color = '#a35b00' if s['type']=='unknown' else '#164d6b'
    group.append(at.element('rect', {'x':xx-width/2,'y':yy-height/2,'width':width,
        'height':height,'rx':1,'fill':'#fff7df' if s['type']=='unknown' else 'white',
        'fill-opacity':'.92','stroke':color,'stroke-width':'.5'}))
    group.append(at.txt(xx-width/2+2,yy+size*.34,label,size,color,True))
    svg_label_audit.append({'id':s['id'],'inside':poly.covers(rect),'shortened':True,'font':size})
svg.write(SAMPLE / '标注.svg', encoding='unicode')
(WORK/'逐间补充_SVG标签审计.json').write_text(json.dumps(svg_label_audit,ensure_ascii=False,indent=2)+'\n')

rel = Path(os.path.relpath(WORK, SAMPLE)).as_posix()
unknown = [s['id'] for s in data['spaces'] if s['type'] == 'unknown']
known = {s['id']: s for s in data['spaces']}
newgroups = [
    ('A_放射科外缘', ['S026', 'S171', 'S172']),
    ('B_北西角与交通核', ['S040', 'S042', 'S045', 'S173', 'S174', 'S175', 'S176']),
    ('C_妇科候诊旁小间', ['S048', 'S177', 'S178']),
    ('D_出入院服务区', ['S078', 'S179', 'S180', 'S181', 'S182']),
    ('E_120值班区', ['S084', 'S183', 'S184', 'S185', 'S186']),
    ('F_后勤小间', ['S110', 'S112', 'S113', 'S187', 'S188', 'S189', 'S190']),
    ('G_输液与急诊北侧', ['S140', 'S157', 'S191', 'S192', 'S193']),
    ('H_输液交通核南侧', ['S152', 'S194', 'S195']),
    ('I_急诊东侧', ['S165', 'S196']),
    ('J_中药房南侧', ['S132', 'S197']),
]
figures = []
for title, ids in newgroups:
    name = '逐间补充_' + title
    fn = env['detail'](name, ids, {sid: sid for sid in ids})
    figures.append((title, ids, fn))
for q in state['connectivity_items']:
    ids = [q['source'], q['target']]
    if q['review_id'] == 'K07':
        ids.append('S075')
    env['detail'](q['review_id'] + '_连通核对', ids, {sid: sid[1:] for sid in ids},
                  q['crop_upright'], openings=True)

before = json.loads((WORK / '连通性测试.json').read_text())
after = env['graph_report'](data)
test = {'before_individual_refinement': before['after'], 'after_individual_refinement': after,
        'new_nodes_do_not_inherit_parent_access': True}
(WORK / '逐间补充_连通测试.json').write_text(json.dumps(test, ensure_ascii=False, indent=2) + '\n')

# 全图继续使用具名SVG；补充图用短S号，保留原始家具、墙线供用户查看。
import pymupdf
with pymupdf.open(SAMPLE / '标注.svg') as doc:
    page = doc[0]
    page.get_pixmap(matrix=pymupdf.Matrix(.7, .7), alpha=False).save(WORK / '逐间补充_标注全图.png')
    for title, ids, fn in figures:
        bounds = [env['polys'][sid].bounds for sid in ids]
        b = [min(q[0] for q in bounds)-10, min(q[1] for q in bounds)-10,
             max(q[2] for q in bounds)+10, max(q[3] for q in bounds)+10]
        clip = pymupdf.Rect(b[0]*1.63, b[1]*2444/1500+125,
                           b[2]*1.63, b[3]*2444/1500+125)
        page.get_pixmap(matrix=pymupdf.Matrix(1.4, 1.4), clip=clip, alpha=False).save(WORK / ('SVG_逐间复核_' + title + '.png'))

lines = ['# 36号首层平面：逐空间粗轮廓标注', '',
         '<!-- annotation:summary:start -->',
         '**状态：**已按“独立空间逐个编号、粗轮廓表达”的口径补充；具体功能缺失保留unknown，关键连通尚待核对。', '',
         f'**规模：**{len(data["spaces"])}个空间；73条access、1条service、8个建筑入口；5个已定位门洞。', '',
         f'**功能信息：**{len(unknown)}个单元的具体功能无法确认。这是原图信息限制，不要求逐项补出具体房名。', '',
         '[原图](' + data['image']['file'] + ') · [逐空间标注图](标注.svg)',
         '<!-- annotation:summary:end -->', '',
         '**本轮口径：**可辨独立隔间即使无名，也分别保留S编号和近似轮廓；不按候选名称并成大块。'
         '梯段、电梯井、家具、卫生器具不作为额外房间。分隔本身无法辨认的部分仍保留概念范围。', '',
         '**变更：**新增27个单元S171—S197，原S001—S170不重排。120值班中心的公共带保留S084，内部小间分出；'
         'S040的旧“卫生间”推定证据不足，已恢复unknown。原113项候选表及固定号已备份归档，后续可选补充。', '',
         '**连通：**新增小间不自动继承父块连接；可见门洞和原P号保留。'
         f'主入口按当前access可达{after["main_entry_reachable_count"]}个节点。'
         '孤立节点只表示本图证据不足，不视为不相通，也不作为负例。', '',
         f'![197个空间的标注总图]({rel}/逐间补充_标注全图.png)', '',
         '## 本轮拆出与补标的独立单元', '',
         '下图直接使用稳定S号。小间无功能名时只核对空间是否单独框出，无需填写猜测用途。', '']
for title, ids, fn in figures:
    lines += ['### ' + title.replace('_', '｜'), '', f'![{title}：稳定S编号]({rel}/{fn})', '']
    notes = [c for c in changes if c['new_space_id'] in ids]
    for c in notes:
        s = known[c['new_space_id']]
        name = '功能未定，保留unknown' if s['type'] == 'unknown' else s['name']
        lines.append(f'- **{s["id"]}**：{c["basis"]}；{name}。')
    lines.append('')

lines += ['## 可补充的空间性质', '',
          '下列范围会影响室内面积口径。如原图也无法判断，可继续留unknown。'
          '确认庭院／挑空后直接不计入室内面积，无需另答顶盖。', '']
for rid, sid, fn in [('10','S016','名称_10-10.png'), ('38','S059','名称_38-38.png'),
                     ('46','S079','名称_46-46.png'), ('51','S091','名称_51-51.png')]:
    lines += [f'### {rid}｜{sid}', '', f'![{rid}：原固定核对号]({rel}/{fn})', '',
              '**问题：**这里属于庭院／挑空、屋面，还是本层室内空间？', '',
              '**我的确认／备注：**待补充（看不清可继续未知）', '']

lines += ['## 关键连通疑点', '', '只核对主要空间之间的可达关系，无需补出小间门位或具体房名。', '']
for q in state['connectivity_items']:
    lines += [f'### {q["review_id"]}｜{q["source"]} ↔ {q["target"]}', '',
              f'![{q["review_id"]}：空间内为S编号数字]({rel}/{q["review_id"]}_连通核对.png)', '',
              '**问题：**' + q['question'], '', '**我的判断：**' + q['judgement'], '',
              '**我的确认／备注：**待填写', '']

lines += ['## 功能信息缺失清单', '',
          '以下单元均已独立保留轮廓与S号；unknown不表示漏标。仅在获得新证据时补充名称，不是必须逐项填写的任务。', '']
for i in range(0, len(unknown), 14):
    lines.append('、'.join(unknown[i:i+14]) + '。')
    lines.append('')
lines += ['**范围与坐标：**首层；原图不改，JSON仍用2444×3260原图像素坐标，SVG和核对图转正显示。'
          '庭院／屋面未定的范围暂沿用原面积口径，不据此计算真实面积。', '']
(SAMPLE / '标注说明.md').write_text('\n'.join(lines))
(WORK / '逐间补充_数字审计.json').write_text(json.dumps(env['badge_audit'], ensure_ascii=False, indent=2)+'\n')
print(json.dumps({'spaces': len(data['spaces']), 'unknown': len(unknown), 'figures': len(figures),
                  'access': after['access'], 'main_reachable': after['main_entry_reachable_count']}, ensure_ascii=False))
