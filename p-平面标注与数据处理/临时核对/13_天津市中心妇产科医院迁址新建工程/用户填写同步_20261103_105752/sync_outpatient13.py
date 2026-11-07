from pathlib import Path
from collections import Counter
import json, re, shutil

root = Path('/Users/hushili/Documents/研究-论文写作/大论文')
work = Path('/tmp/outpatient13_sync_workdir').read_text()
work = Path(work)
stage = work / '待核验成果'
before = work / '修改前备份'
types = json.loads(Path('/Users/hushili/.codex/skills/outpatient-plan-annotation/references/space-types.json').read_text())
data = json.loads((before / 'annotation.json').read_text())
md = (before / '标注说明.md').read_text()
updates = {
    'S022': ('暗室', 'service_work_area'),
    'S026': ('工作台', 'service_work_area'),
    'S031': ('强电', 'building_services'),
    'S032': ('弱电', 'building_services'),
    'S035': ('更衣/财务', 'office'),
    'S045': ('病案存放', 'storage'),
    'S047': ('阅览室', 'staff_support'),
    'S049': ('消防控制室', 'building_control'),
    'S039': ('处置室', 'treatment'),
    'S069': ('阅览室/病案接待', 'service_work_area'),
    'S074': ('清单医保', 'registration'),
    'S148': ('化验', 'laboratory'),
    'S152': ('盥洗间', 'toilet'),
    'S153': ('鲜花超市', 'retail_service'),
    'S086': ('贵宾室', 'service'),
    'S106': ('更衣', 'staff_support'),
    'S174': ('病案资料室', 'storage'),
    'S191': ('观察室', 'observation'),
    'S200': ('输液室', 'treatment'),
}
rows = {}
for line in md.splitlines():
    cells = [x.strip() for x in line.strip().strip('|').split('|')]
    if len(cells) == 8 and re.fullmatch(r'\d{2}', cells[0]):
        assert cells[0] == cells[-1]
        assert cells[1] not in rows
        rows[cells[1]] = cells
assert len(rows) == 66
for sid, (name, typ) in updates.items():
    assert typ in types
    assert rows[sid][6] == ('弱点' if sid == 'S032' else name)
for s in data['spaces']:
    if s['id'] in updates:
        assert s['type'] == 'unknown'
        s['name'], s['type'] = updates[s['id']]
assert [s['id'] for s in data['spaces'] if s['type'] == 'unknown'] == ['S137', 'S138']
(stage / 'annotation.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')

# Keep the user's editable table, candidates, evidence, images and all original answers.
md = md.replace('未完成：21 个空间名称尚未确认；本轮依据6张近照补齐45项名称。',
                '本轮已同步用户明确填写的19项名称；仅32／S137、33／S138按用户“不管了”的备注暂缓，继续保留名称未确认及unknown。门洞与主要连通尚待复核，整图仍为草稿。')
start = md.index('## 本轮照片补名')
end = md.index('## 原66项固定核对表')
backup_link = '../../临时核对/13_天津市中心妇产科医院迁址新建工程/' + work.name + '/修改前备份/标注说明.md'
intro = f'''## 用户补充同步（2026-11-03）

本次从原“我的确认／备注”栏同步19项名称，unknown由21项减至2项；办公（10／S027）和值班室（17／S048）与现有名称一致，保留用户填写。12／S032原填“弱点”，用户在聊天中明确更正为“弱电”，本表保留原填记录并注明更正。

**暂缓项：**32／S137、33／S138原填“不管了”。按用户意愿暂停名称追问，名称及类型仍为未确认／unknown，不把该备注当作功能名称，不删除空间。原01—66核对号、S编号、轮廓、面积、层级及scope保持稳定。

**完成边界：**本轮完成明确名称同步；202个空间、164条关系（154条access、3条service、7条entrance）保留。当前已定位门洞红点0个，154条access均无openings；本轮未做门洞恢复和既有关系的最终语义复核，不能据此宣布整图标注完成。

**类别处理：**复合名称继续作为一个既有空间，不据名称拆分轮廓。更衣/财务按办公归类，阅览室按工作人员支持用房、阅览室/病案接待按服务工作区归类，清单医保按挂号收费、贵宾室按服务区归类；保留用户原名，不展开未经确认的业务用途。上述单类别用于概念级编码，不代替完整复合功能。

[本次同步前备份（含用户原始填写）]({backup_link})

### 前轮照片补名记录

此前依据6张近照补齐45项名称；本次再采用用户明确补充的19项，原66项中64项名称已同步、2项暂缓。照片判读与用户填写来源分别保留在原表中。照片材料和历史固定核对图继续沿用。

'''
md = md[:start] + intro + md[end:]
md = md.replace('## 原66项固定核对表：45项照片判读已同步，21项待确认',
                '## 原66项固定核对表：64项名称已同步，2项按用户备注暂缓')
md = md.replace('下表保留原01—66核对号及S编号映射，包含45项已依据照片判读并同步的名称，以及21项仍未确认的名称。照片判读是助手对图面文字的识别，不冒称用户逐项确认。仍待确认的候选只保存在本说明中，JSON继续为unknown。',
                '下表保留原01—66核对号及S编号映射、历史候选与证据及用户填写。45项来自前轮照片判读，19项采用本轮用户明确名称，32、33项按备注暂缓。当前实际名称以JSON及SVG为准，历史“预估名称”不覆盖用户答案。照片判读不冒称用户逐项确认。')
md = md.replace('原核对项分区数量保留如下；仍待确认：放射科6项、药房及消毒支持5项、急诊5项、门诊西段2项、门诊中段1项、门诊东段2项。',
                '原核对项分区及编号保留如下；仅急诊32、33两项仍为unknown，用户已明确暂缓。')
md = md.replace('| 原15项；待确认6项 |', '| 原15项；名称已同步 |')
md = md.replace('| 原14项；待确认5项 |', '| 原14项；名称已同步 |')
md = md.replace('| 原12项；待确认5项 |', '| 原12项；暂缓2项 |')
md = md.replace('| 原12项；待确认2项 |', '| 原12项；名称已同步 |')
md = md.replace('| 原5项；待确认1项  |', '| 原5项；名称已同步 |')
md = md.replace('| 原8项；待确认2项  |', '| 原8项；名称已同步 |')
lines = md.splitlines()
for i, line in enumerate(lines):
    cells = [x.strip() for x in line.strip().strip('|').split('|')]
    if len(cells) != 8 or not re.fullmatch(r'\d{2}', cells[0]):
        continue
    sid = cells[1]
    if sid in updates:
        if sid == 'S032':
            cells[6] = '弱电（原填“弱点”，聊天已更正）；已同步'
        else:
            cells[6] += '；已同步'
    elif sid in {'S027', 'S048'}:
        cells[6] += '；用户已确认，与现有名称一致'
    elif sid in {'S137', 'S138'}:
        cells[6] += '；按用户备注暂缓，保留unknown'
    lines[i] = '| ' + ' | '.join(cells) + ' |'
md = '\n'.join(lines) + '\n'
md = md.replace('本轮45项名称已写入JSON与SVG；上述21项仍为unknown。整张图仍为标注草稿，门洞定位及主要连通关系尚待后续复核。',
                '前轮45项照片名称与本轮19项用户补充已同步JSON和SVG；仅32／S137、33／S138按用户备注暂缓并保留unknown。整张图仍为标注草稿，门洞定位及主要连通关系尚待复核。')
counts = Counter(s['type'] for s in data['spaces'])
md = re.sub(r'\*\*类型与数量：\*\*[^\n]+', '**类型与数量：**' + '、'.join(f'{types[k]} {v} 个' for k, v in counts.items()) + '。', md)
md = re.sub(r'\*\*名称待确认：\*\*[^\n]+', '**名称待确认：**仅32／S137、33／S138仍为unknown；原填“不管了”，按用户备注暂缓，不再列入本轮名称追问。整图尚未完成门洞与连通复核。', md)
md = re.sub(r'\*\*名称与编号：\*\*[^\n]+', '**名称与编号：**保留原66项核对号及用户填写，当前2项unknown为S137、S138，名称已确定200个。S010在首版几何复核中被识别为误分窄条，已并入S008，不再使用；其余S编号保留。SVG直接显示S编号、具体名称与标准类别，暂缓空间显示“名称未确认”。本轮仅同步明确填写的名称及类别，门洞定位、连通语义及整图最终核验仍未完成。', md)
md = md.replace('不包含施工门坐标、门宽或流线权限。入口位置为图面箭头附近的近似接口。',
                '当前尚无门洞近似定位点；后续应回看原图记录清晰门洞／开口。门宽、施工构造及流线权限不纳入本数据。入口位置为图面箭头附近的近似接口。')
(stage / '标注说明.md').write_text(md)
print(json.dumps({'updated_names': len(updates), 'pending': ['S137', 'S138'], 'stage': str(stage)}, ensure_ascii=False))
