"""Check row preservation, image coverage and rendered Markdown review samples."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys

import markdown
from PIL import Image

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[2]
BASE = ROOT / 'p-平面标注与数据处理'
SKILL = Path('/Users/hushili/.codex/skills/outpatient-plan-annotation')
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
NAMES = ['09_深圳大学学府医院', '10_石家庄第一医院新建赵卜口院区']


def rows(text):
    found = []
    for line in text.splitlines():
        values = [x.strip() for x in line.strip().strip('|').split('|')]
        if len(values) == 7 and re.fullmatch(r'\d+', values[0]) and re.fullmatch(r'S\d+', values[1]):
            found.append(values)
    return found


def main(name):
    project = BASE/'标注试样'/name
    out = WORK/name
    md = project/'标注说明.md'
    text = md.read_text()
    old_text = (out/'修改前备份/标注说明.md').read_text()
    old_rows, new_rows = rows(old_text), rows(text)
    assert old_rows == new_rows
    data = json.loads((project/'annotation.json').read_text())
    unknown = {s['id'] for s in data['spaces'] if s['type']=='unknown'}
    assert {r[1] for r in new_rows} == unknown
    assert len({r[0] for r in new_rows}) == len(new_rows)
    assert all(r[0] == r[-1] for r in new_rows)
    assert [int(r[0]) for r in new_rows] == list(range(1, len(new_rows)+1))
    hashes = json.loads((out/'修改前文件校验.json').read_text())
    assert len(list(project.iterdir())) == 4
    for filename, digest in hashes.items():
        if filename != md.name:
            assert hashlib.sha256((project/filename).read_bytes()).hexdigest() == digest
    links = re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', text)
    assert all((md.parent/link).exists() for link in links)
    metadata = json.loads((out/'局部图映射与检查.json').read_text())
    mapped = [(v['number'], v['sid']) for panel in metadata['panels'] for v in panel['items']]
    assert mapped == [(r[0], r[1]) for r in new_rows]
    if name.startswith('09'):
        prior = json.loads((BASE/'临时核对/09_深圳大学学府医院_名称核对_20261101/核对映射.json').read_text())['review']
    else:
        prior = json.loads((BASE/'临时核对/10_石家庄_20261029/核对编号映射.json').read_text())
    assert mapped == [(v['number'], v['sid']) for v in prior]
    matches = list(re.finditer(r'^#### 核对 (.+)$', text, re.M))
    assert len(matches) == metadata['panel_count']
    for i, match in enumerate(matches):
        block = text[match.start(): matches[i+1].start() if i+1 < len(matches) else len(text)]
        panel_rows = rows(block)
        assert 1 <= len(panel_rows) <= 8
        panel = metadata['panels'][i]
        assert [(r[0],r[1]) for r in panel_rows] == [(v['number'],v['sid']) for v in panel['items']]
        imgs = re.findall(r'!\[[^\]]*\]\(([^)]+)\)', block)
        assert len(imgs) == 1 and Path(imgs[0]).name == panel['file']
        assert all(v['badge_inside'] for v in panel['items'])
        with Image.open(out/panel['file']) as im:
            im.verify()
    # Render representative actual Markdown blocks at a normal document reading width.
    for index, suffix in [(0, '首组'), (14 if name.startswith('09') else 9, '密集组')]:
        start = matches[index].start()
        end = matches[index+1].start() if index+1 < len(matches) else len(text)
        block = text[start:end]
        def absolute_link(m):
            return '](' + (md.parent/m.group(1)).resolve().as_uri() + ')'
        block = re.sub(r'\]\(([^)]+)\)', absolute_link, block)
        html = '<!doctype html><meta charset="utf-8"><style>'
        html += 'body{font:16px/1.55 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;max-width:1120px;margin:24px auto;color:#172033}'
        html += 'img{display:block;max-width:100%;height:auto}table{border-collapse:collapse;width:100%;font-size:14px}th,td{border:1px solid #cbd5e1;padding:8px;text-align:left}th{background:#f1f5f9}a{color:#0369a1}'
        html += '</style>' + markdown.markdown(block, extensions=['tables'])
        html_path = out/f'MD预览_{suffix}.html'
        html_path.write_text(html)
        shot = out/f'MD预览_{suffix}.png'
        command = [CHROME,'--headless','--disable-gpu','--no-first-run','--no-default-browser-check','--hide-scrollbars',
                   '--allow-file-access-from-files', '--user-data-dir=/tmp/name-review-'+name[:2]+'-'+suffix,
                   '--window-size=1280,1750','--screenshot='+str(shot),html_path.as_uri()]
        result = subprocess.run(command, capture_output=True, text=True)
        assert result.returncode == 0 and shot.exists(), result.stderr[-1200:]
    validation = subprocess.run([sys.executable, str(SKILL/'scripts/annotation_tools.py'),
                                  'validate', str(project/'annotation.json'), '--check-dir'],
                                 capture_output=True, text=True)
    (out/'正式草稿状态校验.txt').write_text(validation.stdout+'\n'+validation.stderr)
    assert validation.returncode == 2, validation.stdout[-3000:]+validation.stderr
    report = {'project': name, 'rows': len(new_rows), 'panels': len(matches),
              'rows_and_answers_preserved': True, 'stable_mapping_matches_original': True,
              'all_image_and_file_links_exist': True, 'each_row_has_adjacent_local_image': True,
              'all_number_badges_inside_target': True, 'source_json_svg_unchanged': True,
              'formal_validation_exit': validation.returncode, 'status': '名称待用户确认；非正式标注完成'}
    (out/'交付检查.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False), flush=True)


if __name__ == '__main__':
    for name in NAMES:
        main(name)
