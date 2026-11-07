"""保存用户原始填写，生成当前确认结果与简洁成果概览。"""

from pathlib import Path
from collections import Counter
import importlib.util
import json
import os
import re

from markdown_it import MarkdownIt


OUT = Path(__file__).resolve().parent
REVIEW = OUT.parent
STAGE = OUT/'待核验成果'
ROOT = REVIEW.parents[1]
PROJECT = ROOT/'标注试样/03_晋中市第一人民医院迁建项目'
DATA = json.loads((STAGE/'annotation.json').read_text())
SPACES = {s['id']: s for s in DATA['spaces']}

RESULTS = {
    '01': '保留 R306：S316 与 S314 直接相通。配餐、医保／新农合前沿仍区分服务联系与工作人员通行，不把柜台窗口画成门。',
    '02': '中心供应保留经左侧通路可达的概念联系 R134。该通路未另拆节点，R134 不表示 S120 与 S125 之间有直接门洞，也不新增红点。',
    '03': 'MRI S161 经右下侧门连控制廊 S159；控制廊补回回折段。删除 R162、R163，西侧 S144 不直接进入 MRI 或机房。补充 S161—S162；S172 右上门连接 S171。',
    '04': '删除 R170、R180 两条跨越中间空间的直接边。等候 S173 经 S164 的合用前室部分进入处置 S176。打印出片 S177 经新增合用前室 S345 接护士站 S179、等候 S175，并接过渡间 S178；S178 与控制廊 S181 相通。',
    '05': '财务室 S331 有门通 S329。医疗超市 S337 经缓冲间／中间走道 S340 到交通核 S339；删除跳过中间节点的 R339，保留分段路径。',
    '06': '打印出片 S191 与 S188 相通。更衣 S199 的右侧门接东侧 S189，再到 S188；R206 按实际右侧门对应空间修正，避免红点指向北侧走廊。',
    '07': 'S215 改为设备间，分别连 S214、S216。两间胃肠经内侧 S217 接 S207，删除东侧 S189 的三条旧边。S205、S206 经 S207 进入；S209 上侧门、S210／S211 左侧门与 S207 对应。S218 按用户指定改为庭院，取消人员连接。',
    '08': 'S115 主入口改接下方门诊大厅 S107。S218 为庭院，不接机房及其他房间。值班、机房和库房沿已有 S344—S219—S224—S220 组织，不跨房另造直达边。',
    '09': '删除 S029、S076 两个交通核。保留 S079—S085；S083 改名清创室，归入处置治疗，并保留与手术间 S082 的概念连接，不补虚构门位。',
    '10': 'S265、S266、S267 合并为 S265“挂号收费医保新农合”，清除废弃编号和重复关系。S256、S258、S259、S261 作为该工作区的更衣／盥洗／卫生支持，保留原可辨名称；S257 保留 B超，S260、S262 采用用户接受的概念名“操作间”，服务右侧 S235，分别组织路径。',
    '11': 'S290 的左侧门连接 S289“120指挥中心”。S253 保持半墙挂号收费区，与 S235 保留可达联系，同时区分面向大厅的服务界面。',
    '12': 'S283 小通道保留，并连接 S280、S284。S271 按合用前室记录，联系 S285；与 EICU S275 的连接按包含内部走廊的功能块处理。保留大厅 S107 与配套保安 S286 的概念可达关系。',
    '13': '保留 S098—S105、S091—S105、S098—S343；其中 S091 右侧门的通行说明已采用。无法从原图清晰定位的概念连接不额外画红点。',
}


def rel(path, base=PROJECT):
    return os.path.relpath(Path(path), base)


def main():
    # 字节原件另有备份；这份阅读副本仅重定向图片路径，不改用户填写。
    source = (OUT/'修改前备份/标注说明.md').read_text()
    def rebase(match):
        target = match[1]
        if target.startswith(('#', 'http:', 'https:')):
            return match[0]
        return '](' + os.path.relpath((PROJECT/target).resolve(), OUT) + ')'
    archive = re.sub(r'\]\(([^)]+)\)', rebase, source)
    (OUT/'用户原始填写.md').write_text(
        '# 用户原始填写归档\n\n本文件保留同步前的填写、原图与旧编号图；当前成果请以正式目录为准。\n\n'+archive)
    helper_path = REVIEW/'MD局部核对优化_20261101/优化核对文档.py'
    spec = importlib.util.spec_from_file_location('review_images', helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.OUT = OUT/'核对图'
    helper.OUT.mkdir(exist_ok=True)
    helper.SPACES = SPACES
    previous = json.loads((REVIEW/'MD局部核对优化_20261101/文档优化核验.json').read_text())
    groups = json.loads((REVIEW/'本轮核对映射.json').read_text())['groups']
    inventory = []
    body = ['# 03 号一层｜13 组填写的确认结果', '',
            '**状态：** 已按用户填写及后续聊天中接受的概念精度同步。原始填写单独归档，以下图与说明对应更新后的编号。', '',
            '**精度：** 用户接受合理的概念连接和粗粒度用途；未逐门精确测绘。无定位红点的连接不等于已识别出直接门洞。', '']
    for g in groups:
        num, title = g['number'], g['title']
        old = next(item for item in previous['images'] if item['code'] in {num, '09-A'}
                   and item['code'].startswith(num))
        ids = set(old['visible_target_ids']) & SPACES.keys()
        if num == '04':
            ids.add('S345')
        if num == '07':
            ids.add('S217')
        picture = helper.make_picture(num, title, old['bbox_upright_px'], ids)
        inventory.append(picture)
        img = rel(picture['image'], OUT)
        raw = rel(picture['raw'], OUT)
        body += [f'## {num}｜{title}', '', f'![{num} 当前编号局部图]({img})', '',
                 RESULTS[num], '', f'[无编号原图细节]({raw})', '']
    body += ['## 原始填写', '', '[查看用户原始填写及旧核对图](用户原始填写.md)', '']
    (OUT/'13组确认结果.md').write_text('\n'.join(body))
    (OUT/'更新后局部图映射.json').write_text(json.dumps(inventory, ensure_ascii=False, indent=2)+'\n')
    counts = Counter(r['type'] for r in DATA['relations'])
    openings = [o for r in DATA['relations'] for o in r.get('openings', [])]
    located = sum(bool(r.get('openings')) for r in DATA['relations'] if r['type'] == 'access')
    base = (STAGE/'标注说明.md').read_text()
    old_scope = re.search(r'\*\*范围：\*\*[^\n]+', source).group(0)
    old_names = re.search(r'\*\*本轮采用的概念名称：\*\*[^\n]+', source).group(0)
    names = old_names.replace('S260 卫生间、S261 卫生间前室、S262 卫生间前室',
                              'S260 操作间、S261 卫生间前室、S262 操作间')
    lines = ['# 晋中市第一人民医院迁建项目｜一层标注概览', '',
             '**状态：** 本张一层平面的概念级标注已按用户填写更新；原 13 组核对已收敛，无继续要求逐门填写的项目。', '',
             '**采用精度：** 用户明确接受粗粒度用途和符合现有布局的合理连接。已辨识门洞保留近似点位；其余 `access` 表示概念可达，不一律等同直接开门。其中 R134 包含未单独拆分的中心供应左侧通路。不得将全部无定位连接宣称为逐门核实的通行真值。', '',
             old_scope, '', names, '',
             f'**空间：** {len(DATA["spaces"])} 个空间／区域。删除 S029、S076；S265—S267 合并并保留 S265；新增合用前室 S345。其他稳定 S 编号沿用，不补空号。同名房间继续独立记录。', '',
             '**庭院与面积：** S218 按用户指定改为庭院，与既有 S226、S227、S232 等庭院分别保留原轮廓；不参与室内面积归一化，不建立人员连接。室内 `area_ratio` 重新归一化，合计为 1；不保存平方米或像素面积。', '',
             f'**关系：** 共 {len(DATA["relations"])} 条，其中人员可达 {counts["access"]}、服务联系 {counts["service"]}、共墙 {counts["shared_wall"]}、建筑入口 {counts["entrance"]}。服务窗口及共墙不据此作为人员开口。', '',
             f'**门洞：** {len(openings)} 个红点，对应 {located} 条人员可达关系；另有 {counts["access"]-located} 条概念关系无定位红点。同一空间对有多扇门时合并关系、分别保存 P 编号。既有 P 编号沿用，取消庭院连接时清除相应开口。', '',
             '**原图与坐标：** 原图 3064×3672 像素，字节保持不变。JSON 坐标对应未旋转原图；SVG 转正显示，标签为“S编号＋具体名称＋〔标准功能类别〕”，红点与 JSON 开口逐项对应。', '',
             '## 13 组确认后的处理', '',
             '| 核对号 | 已采用的信息与处理 | 核对号（重复） |', '| --- | --- | --- |']
    for g in groups:
        num = g['number']
        lines.append(f'| {num} | {RESULTS[num]} | {num} |')
    courtyard_ids = [s['id'] for s in DATA['spaces'] if s['type'] == 'courtyard']
    lines = [line.replace('S226、S227、S232 等庭院', '、'.join(s for s in courtyard_ids if s != 'S218')+' 等庭院') for line in lines]
    lines += ['', '## 图片与完整填写记录', '',
              f'[查看 13 组更新后局部图与确认结果]({rel(OUT/"13组确认结果.md")}) · '
              f'[查看用户原始填写归档]({rel(OUT/"用户原始填写.md")})。', '',
              '原始填写、旧图和修改前四文件均完整保留在正式目录之外。下图为本轮改动较集中的普放与急诊收费片区。', '']
    for num in ('07', '10'):
        item = next(i for i in inventory if i['code'] == num)
        lines += [f'![{num} 更新后的局部图]({rel(item["image"])})', '']
    lines += ['## 成果与核验', '',
              '[具名原图](./03_晋中市第一人民医院迁建项目_原图.jpg) · [标注.svg](./标注.svg) · [annotation.json](./annotation.json)。', '',
              '**入口：** '+ '、'.join(r['id']+' '+r['name'] for r in DATA['relations'] if r['type']=='entrance')+'。', '']
    types = json.loads(Path('/Users/hushili/.codex/skills/outpatient-plan-annotation/references/space-types.json').read_text())
    totals = Counter(s['type'] for s in DATA['spaces'])
    lines += ['**类型与数量：** '+ '、'.join(f'{types[k]} {v}' for k,v in totals.items())+'。']
    lines += ['', '**核验口径：** 完成名称、类别、面积、几何、开口与标签对应及四文件检查；图面与局部视觉核验另有外部记录。这里的完成指本张一层的概念级成果，不扩展为施工测绘或逐门精确复核。', '']
    (STAGE/'标注说明.md').write_text('\n'.join(lines))
    # 预览使用正式 MD 目录作为 base，检查相对路径与最终位置一致。
    html = MarkdownIt('commonmark', {'html':True}).enable('table').render('\n'.join(lines))
    style = 'body{font:16px/1.7 sans-serif;max-width:1050px;margin:30px auto;color:#23384b}img{max-width:100%}table{border-collapse:collapse}td,th{border:1px solid #ccd7e3;padding:9px;text-align:left}'
    (OUT/'说明预览.html').write_text(f'<meta charset="utf-8"><base href="{PROJECT.as_uri()}/"><style>{style}</style>'+html)
    print('13 groups preserved and resolved; current local images', len(inventory))


if __name__ == '__main__':
    main()
