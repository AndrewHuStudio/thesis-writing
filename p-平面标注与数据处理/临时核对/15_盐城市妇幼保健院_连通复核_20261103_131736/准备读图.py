from pathlib import Path
import json
import cv2
import numpy as np
from shapely.geometry import Polygon, box

R = Path(__file__).resolve().parent
F = R.parent / '15_盐城市妇幼保健院_照片同步_20261103'
reg = {r['photo']: r for r in json.loads((F / '照片配准结果.json').read_text())}
data = json.loads((R / '修改前备份/annotation.json').read_text())
tasks = {
    '01西北横翼': (1, (175, 260, 1065, 550)),
    '02中央北段': (2, (1040, 205, 1390, 980)),
    '03东北横翼': (3, (1370, 260, 2230, 550)),
    '04中西蓝区': (4, (705, 865, 1070, 1350)),
    '05中西紫区': (4, (225, 955, 725, 1350)),
    '06中央检验': (9, (1045, 955, 1390, 1350)),
    '07中东蓝区': (6, (1370, 865, 1810, 1350)),
    '08东侧输液': (6, (1790, 955, 2175, 1350)),
    '09中央南段': (9, (1040, 1410, 1390, 1850)),
    '10东侧教室': (9, (1700, 1400, 2010, 1880)),
    '11西纵翼上': (7, (225, 1400, 730, 1895)),
    '12西纵翼下': (8, (225, 1870, 730, 2270)),
    '13大会议厅': (10, (420, 2240, 730, 2540)),
    '14西南办公': (11, (225, 2510, 730, 2910)),
    '15南端东侧': (11, (700, 2650, 1075, 2910)),
    '16最南端': (11, (515, 2880, 895, 3085)),
    '17横向主通道': (9, (225, 1320, 2000, 1500)),
}
for name, (photo, bounds) in tasks.items():
    x0, y0, x1, y1 = bounds
    scale = 3
    T = np.array([[scale, 0, -x0*scale], [0, scale, -y0*scale], [0, 0, 1.]])
    H = np.array(reg[f'照片{photo:02}.jpg']['H'])
    source = cv2.imread(str(F / '用户补充照片' / f'照片{photo:02}.jpg'))
    im = cv2.warpPerspective(source, T @ np.linalg.inv(H),
        ((x1-x0)*scale, (y1-y0)*scale), borderValue=(255,255,255))
    cv2.imwrite(str(R / '片区读图' / (name + '_原图.jpg')), im)
    for s in data['spaces']:
        p = Polygon(s['polygon_px'])
        if not p.intersects(box(*bounds)):
            continue
        points = np.int32((np.array(s['polygon_px'])-[x0, y0])*scale)
        cv2.polylines(im, [points], True, (200, 140, 60), 1)
        anchor = p.intersection(box(*bounds)).representative_point()
        ax, ay = int((anchor.x-x0)*scale), int((anchor.y-y0)*scale)
        text = s['id']
        cv2.rectangle(im, (ax-26, ay-10), (ax+27, ay+5), (255,255,255), -1)
        cv2.putText(im, text, (ax-25, ay+2), cv2.FONT_HERSHEY_SIMPLEX, .37, (150,30,10), 1, cv2.LINE_AA)
    # Coordinate rulers provide original-plan coordinates for manual openings.
    for x in range((x0//50+1)*50, x1, 50):
        cv2.putText(im, str(x), ((x-x0)*scale-15, 14), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,180), 1)
    for y in range((y0//50+1)*50, y1, 50):
        cv2.putText(im, str(y), (1, (y-y0)*scale), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,180), 1)
    cv2.imwrite(str(R / '片区读图' / (name + '_编号.jpg')), im)
(R / '片区范围.json').write_text(json.dumps(tasks, ensure_ascii=False, indent=2)+'\n')
print('已生成17片区配准原图与编号图')
