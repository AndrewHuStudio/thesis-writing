from pathlib import Path
import json
import cv2
import pymupdf

R = Path(__file__).resolve().parent
record = json.loads((R / '复核记录.json').read_text())
tasks = json.loads((R / '片区范围.json').read_text())
out = R / '开口叠图复查'
out.mkdir(exist_ok=True)
covered = set()
for name, (_, bounds) in tasks.items():
    im = cv2.imread(str(R / '片区读图' / (name+'_编号.jpg')))
    x0, y0, x1, y1 = bounds
    for mark in record['openings']:
        x, y = mark['position_px']
        if x0 <= x <= x1 and y0 <= y <= y1:
            covered.add(mark['id'])
            px, py = round((x-x0)*3), round((y-y0)*3)
            cv2.circle(im, (px,py), 8, (255,255,255), -1)
            cv2.circle(im, (px,py), 6, (10,10,230), -1)
            cv2.putText(im, mark['id'], (px+7,py-6), cv2.FONT_HERSHEY_SIMPLEX,
                .35, (255,255,255), 3, cv2.LINE_AA)
            cv2.putText(im, mark['id'], (px+7,py-6), cv2.FONT_HERSHEY_SIMPLEX,
                .35, (10,10,180), 1, cv2.LINE_AA)
    for e in record['entrances']:
        x, y = e['position_px']
        if x0 <= x <= x1 and y0 <= y <= y1:
            px, py = round((x-x0)*3), round((y-y0)*3)
            cv2.circle(im, (px,py), 11, (140,10,220), 3)
            cv2.putText(im,e['id'],(px+10,py-7),cv2.FONT_HERSHEY_SIMPLEX,.6,(140,10,220),2)
    cv2.imwrite(str(out/(name+'.jpg')), im)
assert len(covered) == len(record['openings'])
doc = pymupdf.open(R / '待核验成果/标注.svg')
page = doc[0]
page.get_pixmap(matrix=pymupdf.Matrix(1.5,1.5),alpha=False).save(R/'连通复核定位总图.png')
page.get_pixmap(matrix=pymupdf.Matrix(.55,.55),alpha=False).save(R/'SVG全图检查.png')
for name in ['01西北横翼','04中西蓝区','06中央检验','07中东蓝区','12西纵翼下','16最南端']:
    _, (x0,y0,x1,y1) = tasks[name]
    page.get_pixmap(matrix=pymupdf.Matrix(2,2),
        clip=pymupdf.Rect(x0,y0+122.2,x1,y1+122.2),alpha=False).save(R/(name+'_SVG检查.png'))
print('开口叠图覆盖',len(covered),'个；生成全图及6处SVG局部')
