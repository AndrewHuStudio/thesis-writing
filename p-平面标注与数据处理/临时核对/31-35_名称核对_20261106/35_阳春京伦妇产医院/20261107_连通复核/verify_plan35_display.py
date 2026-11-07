from pathlib import Path
import markdown
from playwright.sync_api import sync_playwright
base=Path('/Users/hushili/Documents/研究-论文写作/大论文/p-平面标注与数据处理');p=base/'标注试样/35_阳春京伦妇产医院';out=base/'临时核对/31-35_名称核对_20261106/35_阳春京伦妇产医院/20261107_连通复核'
html='<!doctype html><meta charset="utf-8"><base href="'+p.as_uri()+'/"><style>body{font-family:Arial,"PingFang SC",sans-serif;font-size:16px;line-height:1.65;margin:30px;max-width:1100px}img{max-width:100%;height:auto}table{border-collapse:collapse;font-size:14px}td,th{border:1px solid #bbb;padding:8px}h3{margin-top:36px}</style>'+markdown.markdown((p/'标注说明.md').read_text(),extensions=['tables'])
preview=out/'标注说明_阅读预览.html';preview.write_text(html)
with sync_playwright() as pw:
 browser=pw.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True,args=['--allow-file-access-from-files'])
 page=browser.new_page(viewport={'width':1200,'height':1100},device_scale_factor=1)
 page.goto(preview.as_uri());page.wait_for_load_state('networkidle');print('image_loaded',page.locator('img').evaluate_all('(imgs)=>imgs.map(x=>({src:x.getAttribute("src"),loaded:x.complete&&x.naturalWidth>0}))'))
 for title,name in [('核对01｜S004','MD_名称01_阅读目检.png'),('K01｜门厅东侧电梯交通核 S072','MD_K01_阅读目检.png'),('K02｜03号灰色区域 S042 与东侧白色区域 S043','MD_K02_阅读目检.png')]:
  page.get_by_role('heading',name=title,exact=True).scroll_into_view_if_needed();page.screenshot(path=str(out/name))
 page.set_viewport_size({'width':1500,'height':1100});page.goto((p/'标注.svg').as_uri());page.wait_for_load_state('networkidle');page.evaluate("document.documentElement.style.width='1450px';document.documentElement.style.height='auto'");page.screenshot(path=str(out/'SVG浏览器_全图上段.png'))
 browser.close()
