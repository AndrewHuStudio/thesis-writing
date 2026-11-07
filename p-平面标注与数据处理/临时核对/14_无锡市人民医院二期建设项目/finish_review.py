from PIL import Image,ImageDraw,ImageFont
from pathlib import Path
P=Path('/Users/hushili/Documents/研究-论文写作/大论文/p-平面标注与数据处理/临时核对/14_无锡市人民医院二期建设项目');im=Image.open(P/'14_高清核对总图.png').convert('RGB');d=ImageDraw.Draw(im);sc=3;f=ImageFont.truetype('/System/Library/Fonts/STHeiti Medium.ttc',38)
headings=[('L',18,'A1 北侧西部｜01—09','#b45309'),('R',145,'A2 北侧东部｜10—11','#b45309'),('L',707,'A3 北侧南排西段｜12—15','#b45309'),('R',385,'A4 北侧南排东段｜16—21','#b45309'),('R',866,'B 北侧支持｜22—24','#be185d'),('L',1066,'C 输液片区｜25—28','#0f766e'),('L',1606,'E 检验片区｜29—32','#7c3aed'),('R',1317,'F1 中下部支持用房｜33','#9f1239'),('R',1425,'G 东侧体检上排｜34—36','#1d4ed8'),('R',1681,'F2 中下部保健支持｜37—43','#9f1239'),('L',1957,'H 西南急诊｜44—53','#6d28d9'),('R',2397,'I 留观支持｜54—55','#047857')]
for side,y,t,c in headings:d.text(((20 if side=='L' else 3980)*sc,y*sc),t,font=f,fill=c)
im.save(P/'14_高清核对总图.jpg',quality=95,subsampling=0)
im.resize((2300,1515),Image.Resampling.LANCZOS).save(P/'14_核对总图_预览.jpg',quality=94)
# Two sidebar crops enable direct text QA without opening the full 14k canvas.
im.crop((0,0,620*sc,1035*sc)).resize((1240,2070)).save(P/'14_北侧边栏检查.png')
im.crop((3980*sc,1680*sc,4590*sc,2255*sc)).resize((1220,1150)).save(P/'14_保健边栏检查.png')
print('review jpeg',im.size)