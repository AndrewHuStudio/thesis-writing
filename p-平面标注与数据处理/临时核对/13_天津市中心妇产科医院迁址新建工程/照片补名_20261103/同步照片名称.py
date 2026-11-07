"""Apply directly readable photo labels while preserving the original review mapping."""
from collections import Counter
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import re
import shutil
import xml.etree.ElementTree as ET

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[2]
SAMPLE = ROOT / '标注试样/13_天津市中心妇产科医院迁址新建工程'
BACKUP = WORK / '修改前备份'
STAGE = WORK / '待核验成果'
SKILL = Path('/Users/hushili/.codex/skills/outpatient-plan-annotation')
PREFIX = '../../临时核对/13_天津市中心妇产科医院迁址新建工程/照片补名_20261103'

# Only labels read directly from the supplied photographs enter the core data.
# S numbers, geometries, levels, scopes, areas, and relations remain stable.
READABLE = {
    'S008': ('控制室', 'building_control', '照片05、06：MRI旁的小间可读为控制室。'),
    'S009': ('暗房', 'service_work_area', '照片05、06：MRI上方房间可读为暗房。'),
    'S013': ('X光', 'imaging', '照片05、06：下侧检查间标注X光，保留原字，不补写室。'),
    'S014': ('控制室', 'building_control', '照片05、06：两间X光用房旁的狭长房间标注控制室。'),
    'S015': ('X光', 'imaging', '照片05、06：上侧独立检查间同样标注X光，并非原候选控制室。'),
    'S020': ('乳腺机', 'imaging', '照片05、06：可读为乳腺机；保留原标注，不补设备型号。'),
    'S021': ('控制室', 'building_control', '照片05、06：乳腺机上侧对应房间标注控制室。'),
    'S027': ('办公', 'office', '照片05、06：北排、阅片与值班之间的房间标注办公。'),
    'S038': ('登记', 'registration', '照片05：放射科候诊端、交通核右侧狭长房间标注登记。'),
    'S048': ('值班室', 'staff_support', '照片03：煎药房西侧窄间可读为值班室。'),
    'S050': ('强电', 'building_services', '照片03：西北交通核下侧两间狭长用房中，下间标注强电。'),
    'S051': ('弱电', 'building_services', '照片03：紧贴西北交通核下侧的上间标注弱电。'),
    'S055': ('输液药房', 'pharmacy', '照片03：西北交通核右侧两行字可读为输液、药房。'),
    'S057': ('质量检验室', 'laboratory', '照片03：男更旁小间两行字可读为质量检、验室。'),
    'S063': ('门诊接待', 'service', '照片03：药房支持区北排可读为门诊接待。'),
    'S066': ('男更', 'staff_support', '照片03：卫生间旁成对更衣小间左间标注男更。'),
    'S067': ('女更', 'staff_support', '照片03：成对更衣小间右间标注女更。'),
    'S072': ('医保科', 'office', '照片03：管理室右侧北排小间可读为医保科。'),
    'S126': ('护士休息', 'staff_support', '照片04：急诊南排长间标注护士休息。'),
    'S127': ('医生值班', 'staff_support', '照片04：护士休息右侧长间两行字标注医生值班。'),
    'S130': ('刷手／敷料', 'service_work_area', '照片04：手术支持位置两行文字可读为刷手、敷料；沿用现有空间层级。'),
    'S140': ('过道', 'corridor', '照片04：更衣、抢救与诊室之间的小型交通空间标注过道。'),
    'S146': ('注射室', 'treatment', '照片04：更衣旁横向小间标注注射室。'),
    'S150': ('采血室', 'laboratory', '照片04：东侧竖排房间、换药室下方可读为采血室。'),
    'S151': ('换药室', 'treatment', '照片04：东侧竖排房间、采血室上方可读为换药室。'),
    'S099': ('时间分辨', 'laboratory', '照片01：FISH下方房间可读为时间分辨；不展开为其他检验项目名。'),
    'S100': ('FISH', 'laboratory', '照片01：字母F、I、S、H均清楚，修正原候选FSH。'),
    'S105': ('留观', 'observation', '照片01：绒毛取材室左侧小间明确标注留观。'),
    'S107': ('脱衣', 'patient_preparation', '照片01：PCR下方、刷手左侧小间标注脱衣。'),
    'S108': ('资料', 'storage', '照片01：绒毛取材室下方横向房间标注资料。'),
    'S109': ('绒毛取材室', 'examination', '照片01：完整房名可读为绒毛取材室。'),
    'S110': ('刷手', 'service_work_area', '照片01：PCR下方右侧小间明确标注刷手，保留原字。'),
    'S114': ('免疫组化', 'laboratory', '照片01：门诊北排两行字可读为免疫、组化。'),
    'S115': ('取血', 'laboratory', '照片01：资料右侧、化验左侧小间可读为取血。'),
    'S116': ('脐血办公室', 'office', '照片01：绒毛取材室右侧横向房间可读为脐血办公室。'),
    'S170': ('护更', 'staff_support', '照片02：北排更衣组左间原字为护更，不展开缩写。'),
    'S172': ('男更', 'staff_support', '照片02：护更右侧狭长小间标注男更。'),
    'S173': ('女更', 'staff_support', '照片02：男更右侧小间标注女更。'),
    'S175': ('强电', 'building_services', '照片02：资料用房与楼梯之间、弱电左侧小间标注强电。'),
    'S192': ('检验室', 'laboratory', '照片02：康复诊室下方的独立房间标注检验室。'),
    'S193': ('康复诊室', 'consultation', '照片02：东端西列第二间标注康复诊室。'),
    'S194': ('资料室', 'storage', '照片02：东端西列最上方房间标注资料室。'),
    'S201': ('治疗室', 'treatment', '照片02：东端东列办公室、检查室下方房间标注治疗室。'),
    'S202': ('检查室', 'examination', '照片02：东端东列办公室下方房间标注检查室。'),
    'S203': ('办公室', 'office', '照片02：东端东列最上方房间标注办公室。'),
}

# These are suggestions for the editable MD only, never asserted in annotation.json.
UNCERTAIN = {
    'S022': ('暗室', '辅房', '照片05、06：位于乳腺机控制室上方，两字仍不能可靠区分。把握：低。'),
    'S026': ('二合一', '二合区', '照片05、06：前两字似二合，末字受印刷纹理干扰；不按常见设备名补全。把握：中。'),
    'S031': ('强电', '配电', '照片05：交通核下方小间似电气用房，首字仍模糊。把握：低。'),
    'S032': ('辅房', '片库', '照片05：紧贴竖井的小间两字仍不清楚，不据相邻关系定名。把握：低。'),
    'S035': ('更衣／候诊', '暂无其他可靠候选', '照片05、06：上行似更衣，下行仍不清楚；组合房名尚不能确定。把握：低。'),
    'S039': ('导管放置室', '导诊／处置室', '照片05：两行房名可见导字及室字，中部仍有不同解释。把握：低。'),
    'S045': ('无菌存放', '病案存放', '照片03、04：末两字存放较清楚，前两字仍不能可靠区分；原无菌供应仅为历史候选。把握：低。'),
    'S047': ('高压室／无菌存储', '无菌室／无菌存储', '照片03：下行似无菌存储，上行首两字仍有不同解释。把握：中。'),
    'S049': ('消毒器材室', '消毒敷料室／消毒控制室', '照片03：消毒及末字室可辨，中部字受印刷网纹影响；这些候选共用相同文字线索，仍不能区分。把握：中。'),
    'S069': ('敷料室／消毒器材', '暂无其他可靠候选', '照片03：两行字末部似消毒器材，上行及完整用途仍不清楚。把握：低。'),
    'S074': ('清单发药', '清算发药', '照片03：医院街一侧的狭长服务位置，下行发药较清楚，上行第二字待核。把握：低。'),
    'S137': ('暂无可靠候选', '—', '照片04：急诊南侧交通核上方横向小间只有模糊单字母样标注，不能据此赋予用途。把握：低。'),
    'S138': ('暂无可靠候选', '—', '照片04：与S137成对的小间同样只有单字母样标注，不把字母当成房名或推断用途。把握：低。'),
    'S148': ('化验／量血压', '化验／测量', '照片04：东侧药局上方两行字，首行似化验，下行未能可靠读全。把握：低。'),
    'S152': ('妇产科诊室', '妇产科门诊', '照片04：东侧竖排最上间可辨妇产科，下一行仍未可靠读全，具体名称待核。把握：中。'),
    'S153': ('妇科小手术', '小手术室', '照片04：医院街与急诊接口处可辨妇科小手字样，末字未清，不自动补全。把握：中。'),
    'S086': ('尿采室', '采样室', '照片01：心电、B超右侧小间末字室清楚，前两字仍有不同解释，候选仅供看图核对。把握：低。'),
    'S106': ('缓冲', '污物', '照片01：留观上方狭窄隔间的两个短字仍模糊；不能按取材流程猜定用途。把握：低。'),
    'S174': ('病档资料室', '病案资料室', '照片02：可辨病及资料室，中间字仍不能可靠区分；不擅自规范成常用房名。把握：中。'),
    'S191': ('阴道镜室', '暂无其他可靠候选', '照片02：东端西列最下间首字似阴、末字室清楚，中部仍不清楚；不按妇产医院常见配置确定。把握：低。'),
    'S200': ('输液室', '蜡疗室', '照片02：东端东列、治疗室下方三字房名仍有不同解释；不以所属片区区分这两个候选。把握：低。'),
}


def fit_small_labels(svg_path):
    """Keep three updated labels inside their original small polygons."""
    ns = 'http://www.w3.org/2000/svg'
    tree = ET.parse(svg_path)
    layouts = {
        'S066': (1309, 1372, 70, 28, 6, ['S066 男更', '〔工作人员支持用房〕']),
        'S067': (1309, 1405, 70, 25, 6, ['S067 女更', '〔工作人员支持用房〕']),
        'S107': (1717, 1558, 35, 29, 5, ['S107', '脱衣', '〔患者准备〕']),
    }
    for sid, (x, y, width, height, font, lines) in layouts.items():
        group = tree.getroot().find(f'.//{{{ns}}}g[@id="{sid}"]')
        rect = group.find(f'{{{ns}}}rect')
        color = rect.get('stroke')
        for child in list(group):
            if child.tag in {f'{{{ns}}}rect', f'{{{ns}}}text'}:
                group.remove(child)
        line_height = font + 1
        label_height = len(lines) * line_height + 4
        top = y + (height - label_height) / 2
        ET.SubElement(group, f'{{{ns}}}rect', {'x':str(x+0.5), 'y':str(top), 'width':str(width-1), 'height':str(label_height), 'rx':'1', 'fill':'white', 'fill-opacity':'.94', 'stroke':color, 'stroke-width':'.6'})
        for i, line in enumerate(lines):
            item = ET.SubElement(group, f'{{{ns}}}text', {'x':str(x+2), 'y':str(top+font+1+i*line_height), 'font-size':str(font), 'fill':color, 'font-weight':'bold', 'font-family':'Arial, Microsoft YaHei, PingFang SC, sans-serif'})
            item.text = line
    tree.write(svg_path, encoding='unicode')


def main():
    STAGE.mkdir(exist_ok=False)
    for file in BACKUP.iterdir():
        shutil.copy2(file, STAGE / file.name)
    before = json.loads((BACKUP / 'annotation.json').read_text())
    data = copy.deepcopy(before)
    assert len(READABLE) == 45
    assert len(UNCERTAIN) == 21
    old_pending = {s['id'] for s in before['spaces'] if s['type'] == 'unknown'}
    assert old_pending == set(READABLE) | set(UNCERTAIN)
    for space in data['spaces']:
        if space['id'] in READABLE:
            space['name'], space['type'], _ = READABLE[space['id']]
    (STAGE / 'annotation.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    text = (BACKUP / '标注说明.md').read_text()
    mapping = {}
    lines = []
    for line in text.splitlines():
        if re.match(r'^\|\s*\d+\s*\|\s*S\d+', line):
            cells = [c.strip() for c in line.strip('|').split('|')]
            number, sid = cells[:2]
            assert cells[-1] == number
            mapping[sid] = number
            assert cells[6] == '待确认', 'Existing user answer must be preserved, not overwritten.'
            if sid in READABLE:
                name, _, evidence = READABLE[sid]
                cells[3:7] = [name, '—', evidence + ' 把握：高。', '照片判读已同步；非用户逐项确认']
            else:
                name, alternative, evidence = UNCERTAIN[sid]
                cells[3:6] = [name, alternative, evidence]
            line = '| ' + ' | '.join(cells) + ' |'
        lines.append(line)
    assert len(mapping) == 66
    text = '\n'.join(lines) + '\n'
    pending_numbers = sorted(mapping[sid] for sid in UNCERTAIN)
    pending_label = '、'.join(f'{mapping[sid]}／{sid}' for sid in sorted(UNCERTAIN, key=mapping.get))
    text = text.replace('未完成：66 个空间名称尚未确认。', '未完成：21 个空间名称尚未确认；本轮依据6张近照补齐45项名称。')
    text = text.replace('## 名称不清楚的空间：66 项', '## 原66项固定核对表：45项照片判读已同步，21项待确认')
    text = text.replace(
        '以下逐项列出当前 JSON 中的全部未确认空间。候选沿用上一轮核对记录，并已核对 S 编号及轮廓与当前标注一致；所有候选仍需确认，不能当作正式名称。',
        '下表保留原01—66核对号及S编号映射，包含45项已依据照片判读并同步的名称，以及21项仍未确认的名称。照片判读是助手对图面文字的识别，不冒称用户逐项确认。仍待确认的候选只保存在本说明中，JSON继续为unknown。')
    text = text.replace('按片区统计：放射科 15 项、药房及消毒支持 14 项、急诊 12 项、门诊西段 12 项、门诊中段 5 项、门诊东段 8 项。',
        '原核对项分区数量保留如下；仍待确认：待统计。')
    # Count by original table grouping rather than inferred use or image position.
    old_scope = {}
    for line in (BACKUP / '标注说明.md').read_text().splitlines():
        if re.match(r'^\|\s*\d+\s*\|\s*S\d+', line):
            cells = [c.strip() for c in line.strip('|').split('|')]
            old_scope[cells[1]] = cells[2]
    group_pending = Counter(old_scope[sid] for sid in UNCERTAIN)
    group_sentence = '仍待确认：' + '、'.join(f'{k}{group_pending[k]}项' for k in ['放射科', '药房及消毒支持', '急诊', '门诊西段', '门诊中段', '门诊东段']) + '。'
    text = re.sub(r'原核对项分区数量保留如下；仍待确认：[^\n]+', '原核对项分区数量保留如下；' + group_sentence, text)
    for name, total in [('放射科',15),('药房及消毒支持',14),('急诊',12),('门诊西段',12),('门诊中段',5),('门诊东段',8)]:
        text = text.replace(f'| {name} | {total} |', f'| {name} | 原{total}项；待确认{group_pending[name]}项 |')
    text = text.replace('| 片区 | 待确认数量 | 局部放大图 |', '| 片区 | 原核对项／当前待确认 | 局部放大图 |')
    text = text.replace('以上 66 项确认前，核心 JSON 继续保留 `unknown`，整张图仍为标注草稿。',
        '本轮45项名称已写入JSON与SVG；上述21项仍为unknown。整张图仍为标注草稿，门洞定位及主要连通关系尚待后续复核。')
    text = text.replace('**名称待确认：**详见上方 01—66 核对表，共 66 项；表内全部对应当前 JSON 中的 `unknown` 空间。此图尚不能宣布打标完成。',
        '**名称待确认：**详见原01—66核对表中的21项待确认行：' + pending_label + '。此图尚不能宣布打标完成。')
    text = text.replace('66个待确认空间在核心JSON中为unknown', '21个待确认空间在核心JSON中为unknown')
    text = text.replace('本轮只通过草稿结构核查，尚未完成正式名称确认及最终校验。',
        '本轮只补充照片中清楚的名称及类别，未更改轮廓、面积、空间层级、scope或关系；门洞定位、连通语义及整图最终核验仍未完成。')
    text = text.replace('候选较多时，本行', '旧核对总图及旧局部图用于固定编号定位，黄色状态为此前快照；当前完成状态以本表和最新SVG为准。\n\n候选较多时，本行')
    type_names = json.loads((SKILL / 'references/space-types.json').read_text())
    type_counts = Counter(s['type'] for s in data['spaces'])
    type_line = '**类型与数量：**' + '、'.join(f'{type_names[k]} {v} 个' for k,v in type_counts.items()) + '。'
    text = re.sub(r'^\*\*类型与数量：\*\*.*$', type_line, text, flags=re.M)
    intro = (
        '\n## 本轮照片补名（2026-11-03）\n\n'
        '已保存本次6张照片及修改前四文件备份。本轮45项为清晰图面文字判读，未逐项要求用户重答；'
        '21项因模糊字、缩写或不同读法继续待确认。原66项固定核对号、稳定S编号及所有轮廓保留。\n\n'
        f'**剩余核对号：**{pending_label}。请继续填写原表同号行，无需另填答案表。\n\n'
        f'[修改前备份]({PREFIX}/修改前备份/标注说明.md)｜'
        + ' · '.join(f'[照片{i:02d}]({PREFIX}/用户照片/照片{i:02d}.jpg)' for i in range(1,7))
        + '\n\n**完成边界：**名称剩21项；202个空间、164条关系保留。本轮未增补门洞红点，'
        '也未对164条既有关系逐项作最终语义复核。名称补齐与整图完成分开记录。\n'
    )
    text = text.replace('\n## 原66项固定核对表', intro + '\n## 原66项固定核对表', 1)
    photos = {
        '### 放射科：01—14': [('放射科另一照.png','照片05放射科近照，01—14及21定位'),('放射科右侧文字.png','照片05放射科右端，11—14及21')],
        '### 药房支持及放射科末端：15—24': [('药房文字.png','照片03药房支持区，15—24及26—27、30—31、35')],
        '### 药房支持与急诊交界：25—35': [('照片_急诊.png','照片04急诊支持区，29、34、36'),('急诊南侧.png','照片04急诊南排，25、28、32—33')],
        '### 急诊：36—41': [('急诊东侧.png','照片04急诊东侧，37—40')],
        '### 门诊西段：42—53': [('照片_遗传检验.png','照片01遗传检验与取材片区，43—53'),('西北小间.png','照片01西北小间，42／S086')],
        '### 门诊中段：54—58': [('北排文字.png','照片02北排，54—58')],
        '### 门诊东段：59—66': [('照片_东段.png','照片02东段，59—66')],
    }
    for heading, entries in photos.items():
        addition = '\n\n**本轮近照（与下方原核对号对应）：**\n\n' + '\n\n'.join(f'![{label}]({PREFIX}/{filename})' for filename,label in entries)
        text = text.replace(heading, heading + addition, 1)
    (STAGE / '标注说明.md').write_text(text)
    spec = importlib.util.spec_from_file_location('annotation_tools', SKILL / 'scripts/annotation_tools.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.render(data, STAGE / 'annotation.json', STAGE / '标注.svg')
    fit_small_labels(STAGE / '标注.svg')
    assert before['image'] == data['image'] and before['relations'] == data['relations']
    for old, new in zip(before['spaces'], data['spaces']):
        assert old['id'] == new['id']
        assert {k:v for k,v in old.items() if k not in {'name','type'}} == {k:v for k,v in new.items() if k not in {'name','type'}}
        if old['id'] not in READABLE:
            assert old == new
    result, code = module.check(data, STAGE / 'annotation.json', check_dir=True)
    assert code == 2 and result['valid'] and result['errors'] == []
    assert set(result['pending_name_ids']) == set(UNCERTAIN)
    report = {'photo_readable_count':len(READABLE),'pending_count':len(UNCERTAIN),'pending_review_numbers':pending_numbers,'validation':result,'exit_code':code,'spaces_unchanged':True,'geometry_area_level_scope_unchanged':True,'relations_unchanged':True,'mapping_unchanged':True}
    (WORK / '核验结果.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
