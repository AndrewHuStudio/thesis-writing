"""Revise review candidates from the seven chat photographs; keep core data intact."""

import ast
import hashlib
import json
import re
import shutil
from pathlib import Path

WORK = Path(__file__).resolve().parent
REVIEW = WORK.parent
ROOT = REVIEW.parents[2]
PROJECT = ROOT / 'p-平面标注与数据处理/标注试样/11_寿县县医院新区'
MD = PROJECT / '标注说明.md'

# These are readings and candidates, not user confirmations.
# Photo numbers refer to their order in the user's seven-image message.
UPDATES = {
    '01': ('门厅', '—', '照片1、2可见弧形入口区域的“门厅”字样；名称判读把握高，但上盖及室内外面积属性仍不能仅凭房名确定。把握：高。'),
    '02': ('值班', '—', '照片1住院药房北排可辨“值班”；按图中短名保留，不自行扩写。把握：高。'),
    '03': ('主任办公室', '—', '照片1可辨主任相关字样；中间笔画仍密集，完整名称继续作为候选，需核对是否确为“主任办公室”。把握：中。'),
    '04': ('贵重品库', '贵重药库', '照片1的文字更接近“贵重品库”；“贵重”及末字“库”较清楚，中间是否含“药”仍需核对，两候选共用该文字依据。把握：中。'),
    '05': ('暂无可靠候选', '—', '照片1交通核旁小间文字仍较小；目前不能可靠区分短字，不按电梯邻接关系补造用途。把握：低。'),
    '06': ('示教室', '—', '照片1可辨“示教室”三字，文字与现有S015位置对应。把握：高。'),
    '07': ('更衣', '—', '照片1、3中，入院处置旁小间的短字样倾向“更衣”；字较小，不由成对布局推定男女。把握：中。'),
    '08': ('更衣', '—', '照片1、3中，相邻小间短字样也倾向“更衣”；仍需核对原字，不按与上一间成对便认定用途。把握：中。'),
    '09': ('暂无可靠候选', '—', '照片1、3显示入院处置下方大间，仍未见可可靠采用的独立房名；保留未知，不根据相邻房名延伸。把握：低。'),
    '10': ('结算', '—', '照片1、3的两字标签支持“结算”，原“财务室”仅为片区推测，撤回该旧候选；保留图中短名。把握：高。'),
    '11': ('票据', '—', '照片1、3出入院手续区小间的字形倾向“票据”，末字仍较小，需再核对。把握：中。'),
    '12': ('餐车消毒', '—', '照片1、2中本位置文字疑为“餐车消毒”；中间小字仍需核对，候选依据为文字，不能仅由餐厅背景确定。把握：中。'),
    '13': ('餐车存放', '—', '照片1、2中本位置文字疑为“餐车存放”；短字与墙线相近，完整词组仍需核对。把握：中。'),
    '14': ('暂无可靠候选', '—', '照片1、2可定位该间，短标签仍不稳定；没有足够房间级文字依据，不补造具体餐饮用途。把握：低。'),
    '15': ('备餐', '—', '照片1、2的短字样倾向“备餐”；保留短名候选，不额外添加原图未读出的“间”。把握：中。'),
    '16': ('暂无可靠候选', '—', '照片1、2该小间文字仍不能可靠辨认；旧“仓库”缺少足够文字支持，撤回强行命名，继续自由填写。把握：低。'),
    '17': ('营养食堂', '—', '照片2空白大区域内清楚标“营养食堂”；旧“室外食堂／室外活动区”为误读，应撤回。名称不证明露天或室内，上盖及面积属性另核。把握：高。'),
    '18': ('主食库', '—', '照片2餐饮东北楼梯旁最上小间可辨“主食库”，文字与既有S036位置对应。把握：高。'),
    '19': ('副食库', '—', '照片2对应小间可辨“副食库”；名称依据是本间文字。把握：高。'),
    '20': ('调料库', '—', '照片2对应小间可辨“调料库”；名称依据是本间文字。把握：高。'),
    '21': ('冷库', '—', '照片2对应小间可辨“冷库”二字，无需从设备或常见配置推定。把握：高。'),
    '22': ('餐具洗涤', '餐具消毒', '照片2该位置可辨餐具相关文字，后半倾向“洗涤”；与“消毒”仍需核对，两候选共用文字线索，不能依厨房常见配置区分。把握：中。'),
    '23': ('餐厅办公', '—', '照片2餐饮南排本间可辨“餐厅办公”，沿用图面名称。把握：高。'),
    '24': ('垃圾', '—', '照片2餐饮南排中间小间字形倾向“垃圾”；短标签仍需核对，未凭厨房位置认定为垃圾间。把握：中。'),
    '25': ('厨师休息', '—', '照片2餐饮南排大间的字样倾向“厨师休息”；原“财务室”没有新图支持，撤回该旧候选。前部小字仍需核对。把握：中。'),
    '26': ('CR', '—', '照片4、5可读本间“CR”，逐间核对字母；保留原缩写，不补全。把握：高。'),
    '27': ('CR', '—', '照片4、5可读第二间“CR”，本间有独立字母标注，不由左邻用途推定。把握：高。'),
    '28': ('钼靶机', '—', '照片4、5牙片机相邻房间可辨“钼靶机”字样。把握：高。'),
    '29': ('胃肠透视', '肠胃透视／肠胃透析', '照片4、5可辨肠胃相关文字，但前两字顺序及末字“视／析”仍需核对；保留旧候选并列字形候选，不凭医学常用叫法自动改写原字。把握：中。'),
    '30': ('隔离观察', '—', '照片4、5中本间可读“隔离观察”，轮廓内另有便器；卫生设施属于内部配套，不能据此将整个S131命名为卫生间。把握：高。'),
    '31': ('隔离观察', '—', '照片4、5中右侧本间也标“隔离观察”，轮廓内含卫生设施；名称按本间文字，旧“隔离区卫生间”撤回。把握：高。'),
    '32': ('输液', '—', '照片4、5儿科治疗旁座椅房间可读“输液”；保留图面短名，座椅只作辅助证据。把握：高。'),
    '33': ('贵重物品库', '—', '照片6、7中西药房旁蓝色小间可辨“贵重物品库”；保留原图“物品”，不擅自改写为“药品”。把握：高。'),
    '34': ('观察诊室', '—', '照片6急诊床位组三间中的第一间可读“观察诊室”；撤回旧“留观室／急诊诊室”，床位不替代文字判读。把握：高。'),
    '35': ('观察诊室', '—', '照片6中间本间独立标“观察诊室”；原“观察病房”需纠正，不能因画床位将其改称病房。把握：高。'),
    '36': ('观察诊室', '—', '照片6中EICU上方本间也可读“观察诊室”；原“内科诊室”缺少新图文字支持，应撤回。把握：高。'),
    '37': ('器械、药品', '—', '照片6护士站旁本间可辨“器械、药品”，沿用原标注措辞，不扩写成未确认的库房。把握：高。'),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


original = MD.read_text()
rows = []
for line in original.splitlines():
    if re.match(r'^\| \d+ \| S\d+ \|', line):
        rows.append([v.strip() for v in line.strip('|').split('|')])
assert len(rows) == len(UPDATES) == 37
assert all(r[6].startswith('待确认') for r in rows), 'Preserve user answers before editing.'
assert [r[0] for r in rows] == list(UPDATES)
backup = WORK / '修改前备份'
backup.mkdir(exist_ok=True)
assert not (backup / MD.name).exists(), 'Do not overwrite an existing backup.'
shutil.copy2(MD, backup / MD.name)
shutil.copy2(REVIEW / '核对号映射.json', backup / '核对号映射.json')
core_before = {p.name: sha(p) for p in PROJECT.iterdir() if p.name != MD.name}

new_rows = []
updated = original
for row in rows:
    candidate, alternative, evidence = UPDATES[row[0]]
    new = row[:]
    new[3:6] = [candidate, alternative, evidence]
    updated = updated.replace('| ' + ' | '.join(row) + ' |', '| ' + ' | '.join(new) + ' |')
    new_rows.append(new)

# Reuse the established overlay layout. Its base remains the original local photo.
generator = REVIEW / '补充名称核对.py'
source = generator.read_text().split("path = OUT / '标注说明.md'")[0]
source = source.replace('TMP = Path(__file__).resolve().parent', 'TMP = Path(' + repr(str(WORK)) + ')')
source = source.replace("f'候选：{item[\"candidate\"]}'", "f'候选：{item[\"candidate\"]}'")
source = source.replace("f'{g:02d} {title}｜沿用总图核对号'", "f'{g:02d} {title}｜旧原图定位；候选按新照片复核'")
tree = ast.parse(source)
replacement = [(r[1], r[2], r[3], r[4], r[5]) for r in new_rows]
for node in tree.body:
    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'ROWS' for t in node.targets):
        node.value = ast.parse(repr(replacement), mode='eval').body
namespace = {'__file__': str(generator)}
exec(compile(ast.fix_missing_locations(tree), str(generator), 'exec'), namespace)
mapping = namespace['ITEMS']
(WORK / '核对号映射.json').write_text(json.dumps(mapping, ensure_ascii=False, indent=2) + '\n')

old_rel = '../../临时核对/11_寿县县医院新区_名称核对/'
updated = updated.replace(old_rel, old_rel + WORK.name + '/')
note = '''**新照片复核（2026-11-02）：**依据本次聊天提供的7张分片照片重新判读全部37项。表中有21项文字判读把握高、12项候选把握中、4项仍无可靠候选；这些是助手判读程度，均未标作用户已确认。核对号、S编号、位置及确认栏保持不变。\n\n**图源说明：**新照片目前由聊天附件提供，尚未取得可用于本地裁图的文件路径；以下总图与局部图仍使用既有原图作定位底图，侧栏候选已按本轮判读更新。候选及依据以当前表格为准。取得本地照片后可直接补入新照片局部，不必重新编号。\n\n**仍需补充：**05／S011、09／S019、14／S029、16／S031文字证据不足，优先核对这4处；其他中把握项可先由你直接改名，无需立即全部重拍。01／S001与17／S035仍需另填室内外及面积属性。\n\n'''
updated = updated.replace('## 名称逐项核对表\n\n', '## 名称逐项核对表\n\n' + note)
updated = updated.replace('其中部分原字放大后已有较可靠候选，仍列在表中供你确认；候选未写入 JSON 或 SVG。', '本轮依据新照片修正候选及判读依据，仍列在表中供你确认；候选未写入 JSON 或 SVG。')
MD.write_text(updated)
assert core_before == {p.name: sha(p) for p in PROJECT.iterdir() if p.name != MD.name}
assert {r[1] for r in new_rows} == {s['id'] for s in json.loads((PROJECT / 'annotation.json').read_text())['spaces'] if s['type'] == 'unknown'}
assert all((MD.parent / target).is_file() for target in re.findall(r'\]\(([^)]+)\)', updated))
assert len(re.findall('把握：高。', '\n'.join(r[5] for r in new_rows))) == 21
report = {'rows': 37, 'high': 21, 'medium': 12, 'low': 4, 'core_files_unchanged': True, 'core_sha256': core_before, 'user_answers_preserved': True, 'mapping_stable': True, 'links_valid': True}
(WORK / '核验结果.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(report, ensure_ascii=False))
