from pathlib import Path
import xml.etree.ElementTree as ET
import pymupdf
from PIL import Image
BASE=Path('/Users/hushili/Documents/研究-论文写作/大论文/p-平面标注与数据处理')
P=BASE/'标注试样/35_阳春京伦妇产医院'
OUT=BASE/'临时核对/31-35_名称核对_20261106/35_阳春京伦妇产医院/20261107_填写同步与连通验收'
svg=P/'标注.svg'
ET.register_namespace('','http://www.w3.org/2000/svg')
ET.register_namespace('xlink','http://www.w3.org/1999/xlink')
tree=ET.parse(svg)
for el in tree.iter():
    if el.get('data-opening-id'):
        for child in el:
            if child.tag.endswith('text'):child.set('stroke-width','0.5')
tree.write(svg,encoding='utf-8',xml_declaration=True)
doc=pymupdf.open(svg)
pix=doc[0].get_pixmap(matrix=pymupdf.Matrix(1.2,1.2))
Image.frombytes('RGB',[pix.width,pix.height],pix.samples).rotate(90,expand=True).save(OUT/'最终全图_目检.png')
regions=[('诊疗与休息室',(390,490,1260,820)),('庭院与药房',(390,800,1220,1320)),('合并大厅',(610,1270,1220,1510)),('影像诊室',(390,1480,1260,2065)),('门厅东侧',(1320,1460,2200,1790)),('南侧清洁间',(1440,1900,1690,2070))]
for name,box in regions:
    rect=pymupdf.Rect(2444-box[3],box[0],2444-box[1],box[2])
    pix=doc[0].get_pixmap(matrix=pymupdf.Matrix(2,2),clip=rect)
    im=Image.frombytes('RGB',[pix.width,pix.height],pix.samples).rotate(90,expand=True)
    im.save(OUT/('最终_'+name+'_目检.png'))
print('final SVG rendered in full and 6 regions')
