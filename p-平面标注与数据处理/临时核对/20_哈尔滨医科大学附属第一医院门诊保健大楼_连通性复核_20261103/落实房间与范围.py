from pathlib import Path
import copy
import html
import json
import re
from shapely.geometry import Polygon
from shapely.ops import unary_union

OUT = Path(__file__).resolve().parent
PROJECT = OUT.parents[2] / 'p-平面标注与数据处理/标注试样/20_哈尔滨医科大学附属第一医院门诊保健大楼'
SOURCE = PROJECT / 'annotation.json'

# 沿用主间S编号；退役编号和原核对号仅保存在本图MD及外部映射。
MERGES = {
    'S066': ('S067', '内科'),
    'S106': ('S105', '护士分诊'),
    'S050': ('S049', '儿科'),
    'S051': ('S052', '耳科'),
    'S054': ('S055', '眼科'),
    'S057': ('S056', '妇产科'),
    'S058': ('S059', '心内'),
    'S075': ('S074', '皮肤'),
    'S076': ('S077', '男科'),
    'S079': ('S078', '口外'),
    'S085': ('S084', '肠道分诊'),
    'S100': ('S098', '后候药大厅'),
    'S109': ('S107', '急诊药局'),
}
NAMES = {
    'S039': ('乳腺扫描', 'examination'),
    'S040': ('管井', 'building_services'),
    'S002': ('脑外', 'consultation'),
    'S007': ('肿瘤', 'consultation'),
    'S012': ('离休干部保健诊', 'consultation'),
    'S019': ('新风井', 'building_services'),
    'S021': ('脑外暗室', 'examination'),
    'S023': ('男性科', 'consultation'),
    'S029': ('管井', 'building_services'),
    'S035': ('厕所前室', 'vestibule'),
    'S060': ('前室', 'vestibule'),
    'S061': ('前室', 'vestibule'),
    'S068': ('管井', 'building_services'),
    'S093': ('担架轮椅室', 'equipment_room'),
    'S095': ('收费', 'registration'),
    'S096': ('库房', 'storage'),
    'S103': ('分发室', 'pharmacy_counter'),
}


def main():
    data = json.loads(SOURCE.read_text())
    spaces = {s['id']: s for s in data['spaces']}
    md = html.unescape((PROJECT / '标注说明.md').read_text())
    rows = {}
    for line in md.splitlines():
        cells = [html.unescape(x.strip()) for x in line.strip('|').split('|')]
        if len(cells) == 7 and re.fullmatch(r'\d+', cells[0]):
            rows[cells[1]] = cells
    assert len(rows) == 88
    for sid, (name, typ) in NAMES.items():
        spaces[sid]['name'] = name
        spaces[sid]['type'] = typ
    merge_records = []
    for retired, (retained, name) in MERGES.items():
        pa = Polygon(spaces[retained]['polygon_px'])
        pb = Polygon(spaces[retired]['polygon_px'])
        # 用户接受整体功能块；闭合两片间原隔墙带，不改变模块外侧轮廓。
        united = unary_union([pa.buffer(5, join_style=2), pb.buffer(5, join_style=2)]).buffer(-5, join_style=2)
        assert united.geom_type == 'Polygon' and united.is_valid, (retired, retained)
        for sid, space in spaces.items():
            if sid in (retired, retained) or sid in MERGES:
                continue
            assert united.intersection(Polygon(space['polygon_px'])).area <= 1, (retired, retained, sid)
        spaces[retained]['polygon_px'] = [[round(x, 4), round(y, 4)] for x, y in list(united.exterior.coords)[:-1]]
        spaces[retained]['name'] = name
        spaces[retained]['level'] = 'functional_block' if retained not in ('S098',) else 'open_space'
        if retained == 'S077':
            spaces[retained]['type'] = 'consultation'
        del spaces[retired]
        merge_records.append(dict(retired_id=retired, retained_id=retained, name=name, original_review_number=rows[retired][0], user_answer=rows[retired][5], basis='图面连续区域修正' if retired == 'S109' else '用户填写合并；S057自指46按同名相邻主间45/S056落实' if retired == 'S057' else '用户明确填写'))
    data['spaces'] = [s for s in data['spaces'] if s['id'] in spaces]
    # 原草稿将厕所入口支腿和楼梯前室互相错位；按实际门与墙重新对齐。
    spaces['S035']['polygon_px'] = [[2444-v, u] for u, v in [(1208, 1115), (1250, 1115), (1250, 1168), (1208, 1168)]]
    spaces['S028']['polygon_px'] = [[2444-v, u] for u, v in [(1208, 999), (1284, 999), (1284, 1168), (1258, 1168), (1258, 1107), (1208, 1107)]]
    # 原草稿把担架室北侧公共支廊并入担架室，且漏了厕所南侧横廊。
    # 按照片实际隔墙位置修正，保留S093/S048身份，不新增空间编号。
    spaces['S093']['polygon_px'] = [[2444-v, u] for u, v in [(2329, 1506), (2392, 1506), (2392, 1582), (2329, 1582)]]
    corridor = Polygon(spaces['S048']['polygon_px'])
    branch = Polygon([[2444-v, u] for u, v in [(2333, 1435), (2568, 1435), (2568, 1498), (2333, 1498)]])
    extended = unary_union([corridor, branch])
    assert extended.geom_type == 'Polygon'
    spaces['S048']['polygon_px'] = [[round(x, 4), round(y, 4)] for x, y in list(extended.exterior.coords)[:-1]]
    points = [(y, 2444-x) for x, y in spaces['S092']['polygon_px']]
    points = [(2325 if u == 2298 and v in (1438, 1590) else u, v) for u, v in points]
    spaces['S092']['polygon_px'] = [[2444-v, u] for u, v in points]
    # 高干门厅南侧实际门墙在原概念分界的东北侧，两端共用该墙重新对齐。
    for sid in ['S090', 'S097']:
        points = [(y, 2444-x) for x, y in spaces[sid]['polygon_px']]
        adjusted = []
        for u, v in points:
            if (u, v) == (1440, 1310):
                u, v = 1460, 1290
            elif (u, v) == (1354, 1220):
                u, v = 1354, 1187.4043
            elif sid == 'S097' and (u, v) == (1382, 1420):
                u, v = 1354, 1411
            elif sid == 'S097' and abs(u-1252.9101449275363) < .01:
                u, v = 1244, 1515
            if not adjusted or (u, v) != adjusted[-1]:
                adjusted.append((u, v))
        spaces[sid]['polygon_px'] = [[2444-v, u] for u, v in adjusted]
    # 住院门厅与出入院办公间的南端门口在原草稿轮廓外，补齐该门前白色厅区。
    hall = Polygon(spaces['S086']['polygon_px'])
    corner = Polygon([[2444-v, u] for u, v in [(2195, 1352), (2244, 1288), (2244, 1340)]])
    hall = unary_union([hall, corner])
    hall = hall.difference(Polygon(spaces['S092']['polygon_px']))
    spaces['S086']['polygon_px'] = [[round(x, 4), round(y, 4)] for x, y in list(hall.exterior.coords)[:-1]]
    aliases = {k: v[0] for k, v in MERGES.items()}
    dedup = set()
    relations = []
    removed = []
    for relation in data['relations']:
        r = copy.deepcopy(relation)
        r['source'] = aliases.get(r['source'], r['source'])
        r['target'] = aliases.get(r['target'], r['target'])
        if r['source'] == r['target']:
            removed.append(dict(relation_id=r['id'], reason='合并后内部自连接'))
            continue
        key = (r['type'], *sorted([str(r['source']), str(r['target'])]))
        if key in dedup:
            removed.append(dict(relation_id=r['id'], reason='合并后重复关系'))
            continue
        dedup.add(key)
        relations.append(r)
    data['relations'] = relations
    (OUT / '名称范围落实.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    (OUT / '用户填写与合并映射.json').write_text(json.dumps(dict(rows=rows, names=NAMES, merges=merge_records, aliases=aliases, internal_relations_removed=removed, notes=['79原文后候药大厅照录；未自动删去后字', '62男科和63合并按用户原名修改主间S077', '用户新增回填：32乳腺扫描、33管井、54并入内科、82并入护士分诊', '按图修正S093北侧支廊、补齐S048横廊及S086南端门前区域']), ensure_ascii=False, indent=2) + '\n')
    print('SPACES', len(data['spaces']), 'RELATIONS', len(relations), 'UNKNOWN', [s['id'] for s in data['spaces'] if s['type'] == 'unknown'])


if __name__ == '__main__':
    main()
