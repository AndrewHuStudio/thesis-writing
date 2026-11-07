"""Preserve plan-12 user answers, add local connectivity questions and audits."""
from pathlib import Path
from collections import Counter
from html import escape, unescape
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent.parent / '标注试样' / '12_遂川县人民医院'
STAGE = ROOT / '待核验成果'
BACKUP = ROOT / '修改前备份'
data = json.loads((STAGE / 'annotation.json').read_text())
old = (BACKUP / '标注说明.md').read_text()
table_heading = '## 房间名称与区域性质固定核对表'
old_overview, table = old.split(table_heading, 1)
rels = data['relations']
openings = [o for r in rels for o in r.get('openings', [])]
located = sum(bool(r.get('openings')) for r in rels if r['type'] == 'access')
counts = Counter(r['type'] for r in rels)
prefix = '../../临时核对/12_遂川县人民医院_连通复核_20261103/'

overview = old_overview.replace(
    '# 12_遂川县人民医院｜确认同步后的标注草稿',
    '# 12_遂川县人民医院｜门洞定位与连通复核草稿')
overview = overview.replace(
    '本轮填写已同步：主要房名及8处区域性质已落实；仍有1个辅助功能块名称未定。连通性尚待专项复核。',
    '主要房名及8处区域性质已同步；本轮已对照原图补充门洞定位、修正人员可达关系并测试通行网络。'
    '仍有K01—K03三处关键疑点及S040名称未定，尚不宣布整图完成。')
overview = overview.replace(
    '**完成状态：**这是名称及结构调整同步；不是连通性完成声明。仅24／S040辅助功能块名称未定，本轮不追加问题。',
    '**完成状态：**门洞／开口已写入annotation.json，并在标注.svg显示P编号红点；'
    '保留既有名称确认与稳定编号。名称未定仍仅24／S040；连通性另有下列三处需确认。')
overview = overview.replace(
    '**关系处理：**仅清理删除／合并涉及的关系及重复项；R179与R178合并后对应同一空间对，保留R178。没有新增关系或门洞定位，不代表其他空间不连通。',
    '**上轮名称同步记录：**清理删除／合并涉及的关系及重复项；R179与R178合并后对应同一空间对，'
    '保留R178。本轮另作门洞定位与连通复核，结果见前方说明。')
overview = overview.replace(
    '**连接关系：**191 条，人员可达 181 条、入口连接 10 条。',
    f'**连接关系：**{len(rels)}条，人员可达{counts["access"]}条、'
    f'服务联系{counts["service"]}条、入口连接{counts["entrance"]}条。')
overview = overview.replace(
    '**入口：**西北入口、北侧入口、东北入口、中段西入口、中段西南入口、门诊西入口、门诊东入口、门诊东南侧入口、南侧配套用房入口、门诊主入口。',
    '**入口：**沿用E01—E10；新增E11中段北东侧平台入口、E12中段西北楼梯北侧入口、'
    'E13西北交通核北侧入口、E14中段西楼梯西侧入口、E15中段东楼梯北侧平台入口。'
    '外部门洞采用E编号，不混入室内P编号。')
overview = overview.replace(
    '**面积处理：**7处纹理区域与更衣休息合并保留完整面积；S065按室内通道计入。S043退出范围后，全部现行室内相对面积重新归一化。',
    '**面积处理：**上轮7处纹理区域与更衣休息合并保留完整面积，S065按室内通道计入，S043已退出范围。'
    '本轮补齐原标注漏出的S021大厅东侧门前区域，以及S091在S099／S107之间通向S118的横通道；'
    '沿用既有节点，不新增房间，室内相对面积重新归一化。')

review = f'''## 本轮门洞与连通复核（2026-11-03）

**门洞与开口：**{len(openings)}处红点（P001—P175），其中门洞172处、无门开口3处，
对应{located}条人员可达关系。其余{counts['access'] - located}条为无定位红点的概念连接，主要是图面连续的走道／大厅分段；不在这些分段边界上虚构门位。

**原图判读与修正：**保留稳定S编号，修正10条旧关系的连接对象，撤下8条没有直接通行依据的旧关系；
新增44条人员可达和1条服务联系。R180收费区面向大厅的是柜台服务，已由人员可达改为service；
另以北侧实门恢复收费区通行。药房与大厅的服务窗口也不作为人员门洞。

**主要通行网络：**补齐北侧联络通道—中段东侧通道—南部门诊通道，以及导医区周围的连续交通联系。
这些联系依据本图连续铺地、走道开口和既有空间分段判定；原图没有实体分隔的位置只记概念access。
交通核仅核查对外连接，不继续拆分核内小间或编造内部路径。

**图连通测试：**仅以access构建无向图，入口分别作为外部接口，不通过共同null端点把各入口互连。
188个节点中，主要连通分量180个节点；S121单独连接E06室外入口。
181个节点有通向至少一个入口的已记录路径。其余7个为S108、S109、S113、S040、S137、S165、S182，
属于下列关键疑点或辅助内部细节；缺少已证实路径不代表实际不可达，也不作为不连通负样本。

**核验结果：**本轮正式校验valid=true、errors=[]，175个JSON开口与SVG红点的编号、坐标和两端空间一致；
名称完成标志仍为false，待定项为S040。程序检查不替代原图判读。
下列三项未解决前，连通性保留“复核待确认”状态。原名称核对表与已有填写完整保留在后面。

### K01｜门诊中央方形构图 S165

![K01：中央符号及两侧通道]({prefix}K01_中央构图.png)

**问题：**S165确实是可进入的电梯／交通核，还是大厅内的装饰、铺地图案等构图？若为交通核，它从哪一侧进入？

**我的判断：**既有数据称其为“门诊中央交通核”，但本轮放大后仅见闭合方框、圆和对角线，
未见清晰门洞或文字依据。先保留原名称与边界供核对，撤下原先连接西侧S164、东侧S166的两条无依据access；不画红点。
若确认只是铺地构图，可并入相邻大厅，不继续视作独立交通核。

**我的确认／备注：**待填写（写实际性质；如为交通核，补充相连通道或入口侧）

[查看同范围无标记原图]({prefix}K01_中央构图_原图.png)

### K02｜南侧护士站 S113及其处理／治疗室

![K02：护士站、处理治疗室和公共通道]({prefix}K02_南侧护士站.png)

**问题：**S113护士站的人员从西侧通道S104、南侧通道S115，还是其他位置进入？

**我的判断：**S108处理室—S109治疗室—S113护士站的内部房门可辨，已记录P点；
但S113外侧显示连续柜台／边界，没有可靠的小门位置。原先把S108直接连向S104的关系已改为实际的S108—S109门洞；
S113—S104旧关系暂撤下。若是半墙柜台且人员可达，只需确认连接哪条通道，无需提供精确门位。

**我的确认／备注：**待填写（例如“S113连S115，是半墙服务区”；或写实际连接）

[查看同范围无标记原图]({prefix}K02_南侧护士站_原图.png)

### K03｜门诊西北交通核 S121

![K03：西北交通核及室内通道]({prefix}K03_西北门诊交通核.png)

**问题：**S121除西侧室外入口E06外，是否还直接连到室内通道S123或其他室内空间？

**我的判断：**西侧外部入口清楚，保留E06；向东的边界未见可靠房门，南侧为S142办公室。
旧S121—S140关系两空间仅角点接触，不能作为直接人员连接，已撤下。
当前保留独立外部入口，不把S142办公室的门误当作楼梯出口。

**我的确认／备注：**待填写（可填“只连室外”；或写实际相连室内空间）

[查看同范围无标记原图]({prefix}K03_西北门诊交通核_原图.png)

**本轮不细究的内部细节：**S040交通核旁辅助功能块、S137卫生间／更衣功能块、S182收费储藏的具体内部小门仍不清楚，
本轮不增加逐间问题，也不以共墙补人员连接；名称确认情况保持原样。S190休憩与S193前室之间未见直接门洞，
撤下旧直接连接；两者各自通过已可辨的相邻房门接入网络。未记录关系均不等于判定不相通。

'''
overview = overview.replace('## 本轮填写已落实', review + '## 本轮填写已落实', 1)
text = overview + table_heading + table
(STAGE / '标注说明.md').write_text(text)
assert text.split(table_heading, 1)[1] == table

if __name__ == '__main__':
    from shapely.geometry import Point, Polygon
    spaces = {s['id']: s for s in data['spaces']}
    polygons = {k: Polygon(s['polygon_px']) for k, s in spaces.items()}
    adjacency = {k: set() for k in spaces}
    distances = []
    for r in rels:
        if r['type'] != 'access':
            continue
        adjacency[r['source']].add(r['target'])
        adjacency[r['target']].add(r['source'])
        for o in r.get('openings', []):
            p = Point(o['position_px'])
            dd = [polygons[r[k]].distance(p) for k in ['source', 'target']]
            distances.append({'id': o['id'], 'relation': r['id'],
                              'distances_px': [round(v, 2) for v in dd]})
    assert all(max(o['distances_px']) <= 8 for o in distances), distances
    unseen = set(spaces)
    components = []
    while unseen:
        queue = [min(unseen)]
        component = set()
        while queue:
            v = queue.pop()
            if v in component:
                continue
            component.add(v)
            queue.extend(adjacency[v] - component)
        components.append(sorted(component))
        unseen -= component
    components.sort(key=len, reverse=True)
    entries = {r['target'] for r in rels if r['type'] == 'entrance'}
    missing = [s for c in components if not entries.intersection(c) for s in c]
    assert set(missing) == {'S108', 'S109', 'S113', 'S040', 'S137', 'S165', 'S182'}
    missing_images = []
    for url in re.findall(r'!\[[^\]]*\]\(([^)]+)\)', text):
        if not (PROJECT / url).resolve().is_file():
            missing_images.append(url)
    assert not missing_images, missing_images
    original = json.loads((BACKUP / 'annotation.json').read_text())
    old_spaces = {s['id']: s for s in original['spaces']}
    assert set(spaces) == set(old_spaces)
    for sid, s in spaces.items():
        assert {k: v for k, v in s.items() if k not in {'area_ratio', 'polygon_px'}} == {
            k: v for k, v in old_spaces[sid].items() if k not in {'area_ratio', 'polygon_px'}}
        if sid not in {'S021', 'S091'}:
            assert s['polygon_px'] == old_spaces[sid]['polygon_px']
    report = {'openings': len(openings), 'located_access': located,
              'unlocated_access': counts['access'] - located,
              'counts': dict(counts), 'components': components,
              'component_sizes': [len(c) for c in components],
              'unreachable_from_entrances': missing,
              'reachable_from_entrances': len(spaces) - len(missing),
              'opening_distance_check': distances,
              'missing_images': missing_images,
              'user_name_table_preserved': True,
              'stable_space_ids_and_names_preserved': True,
              'original_image_sha256': hashlib.sha256(
                  (STAGE / data['image']['file']).read_bytes()).hexdigest()}
    (ROOT / '图连通与交付检查.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k not in {
        'components', 'opening_distance_check'}}, ensure_ascii=False))
