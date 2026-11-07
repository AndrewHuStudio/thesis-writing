from pathlib import Path
from collections import Counter
import json,re,sys
from PIL import Image,ImageDraw,ImageFont

W=Path(__file__).resolve().parent
P=W.parents[1]/'标注试样/23_西安经开医院'
d=json.loads((P/'annotation.json').read_text());spaces={s['id']:s for s in d['spaces']}
cfg=json.loads((W/'本轮路径.json').read_text())
old=(Path(cfg['backup'])/'标注说明.md').read_text()
font=ImageFont.truetype('/System/Library/Fonts/STHeiti Medium.ttc',26)
im=Image.open(P/d['image']['file']).convert('RGB')
questions=[('K01',(1485,635,1785,835),['S026','S027','S028'],
            [('S033 急诊通道',1530,645),('K01 南侧门',1648,788)]),
           ('K02',(1230,2020,1670,2430),['S157'],
            [('S138 公共大厅',1240,2210),('S166 门诊通道',1470,2080),('P226 西侧门',1390,2220)])]
for key,box,ids,labels in questions:
    scale=3
    crop=im.crop(box).resize(((box[2]-box[0])*scale,(box[3]-box[1])*scale))
    crop.save(W/(key+'_原图.png'))
    draw=ImageDraw.Draw(crop)
    for sid in ids:
        poly=[((x-box[0])*scale,(y-box[1])*scale) for x,y in spaces[sid]['polygon_px']]
        draw.line(poly+[poly[0]],fill='#c026d3',width=4)
        # 房内标签偏移至不遮开口的位置。
        x=sum(p[0] for p in poly)/len(poly);y=sum(p[1] for p in poly)/len(poly)
        text=sid+' '+spaces[sid]['name'];bb=draw.textbbox((x,y),text,font=font)
        if bb[2]>crop.width:x=max(4,crop.width-(bb[2]-bb[0])-4)
        bb=draw.textbbox((x,y),text,font=font);draw.rectangle(bb,fill='white');draw.text((x,y),text,font=font,fill='#a21caf')
    for text,x,y in labels:
        xy=((x-box[0])*scale,(y-box[1])*scale);bb=draw.textbbox(xy,text,font=font)
        draw.rectangle(bb,fill='white');draw.text(xy,text,font=font,fill='#075985')
    crop.save(W/(key+'_局部.png'))

prefix='../../临时核对/23_西安经开医院_连通复核_20261105/'
summary=(W/'生成概览.md').read_text()
summary=summary.replace('# 平面标注概览','# 23_西安经开医院｜标注与连通复核')
summary=summary.replace('空间名称已齐；结构与关系仍以原图及人工核对为依据。',
 '**名称与类别已同步；连通复核推进中，尚有 K01 一项关键疑点待确认。**')
summary=summary.replace('绿化不参与。','7处已确认的露天／挑空内庭院不参与。')
scope='本图为西安经开医院一层平面（2444×3260），包含公共大厅、急诊、放射、外科、药房、老年门诊、中段门诊与体检片区。仅处理本图，沿用219个稳定S编号和现有轮廓。'
extra=f'''**范围与面积：**{scope} S092、S096、S133、S146、S150、S197、S202 均按用户本轮确认记为露天／挑空内庭院，不计室内面积；已重新归一化。

**用户填写：**166项名称全部采用“我的确认／备注”栏的明确填写，去除纯排版换行标签；“总诊手术”“设备时”“用点机房”“特殊药瓶库”等均保留原名。具体名称与标准功能类别分别保存，不自动纠正或扩展原名。

**连通处理：**已撤下13条缺乏直接开口依据的旧关系，补记可见内门、公共交通核连接及药房人员入口。S086经S087、S089经S090、S101经S100、S103经相邻诊室、S106经S105、S207经S206、S210经相邻诊室、S213经S214、S216经S215进出；不再重复记为直达走廊。S164药库经S163及S165相连。S120/S125东侧柜台、S073挂号收费柜台及S165挂号取药柜台的服务关系与人员通行分开保存。

**布局推断与概念连续：**R238（S011↔S013）按电梯面向前室的布置记录；R239（S074↔S078）按大厅内交通核整体接入记录；R158（S165↔S166）按柜台北端的工作区出入组织保留概念连接，不编造红点。两处自动扶梯、开放采血区、大厅分段与同片区通道碎片按图面连续性保留无定位的access。S016卫生间按现有整体节点及西侧通道组织保留R045，内部入口不继续细分。上述为图面判断／布局推断，未标为用户已确认。

**本轮不细究的内部细节：**S045、S062更衣小间及S113、S115管井未补造入口；交通核内部电梯门、楼梯与前室的逐间路线不展开。缺少关系不代表不可达，亦不作为已确认负例。露天内庭院保留轮廓与编号，不用它们串联室内功能区。

**核验状态：**结构、名称、面积及SVG红点对应检查通过；原图未改动。K01关键连通疑点未解决前，本图仍不宣布完成。

[原图]({d['image']['file']}) · [标注SVG](标注.svg)

## 连通关键核对（2026-11-05）

可直接在K01图下方填写“我的确认／备注”；也可在聊天中回复 `K01=……`。无需确定门宽或施工构造。原候选K02经二次放大已自主解决，保留判读记录，不需填写。

### K01｜S028“总诊手术”的唯一进出路线

![K01 手术房间及相邻厕所、南侧前区]({prefix}K01_局部.png)

[同范围无标记原图]({prefix}K01_原图.png)

**问题：**S028是否经南侧共用前区连向急诊通道S033？该前区是否应从S026/S027的厕所范围中分出，或实际由其他方向进入？

**我的判断：**南侧西端可见门形开口；北侧未见可确认门口。南门外侧落在当前S027轮廓中，可能是与厕所共用的前区，不能直接写成“穿过男厕所进入手术室”。已撤下旧R055（S028↔S033），暂不建立未经确认的替代路线。

**我的确认／备注：**待填写（可填“经南侧公共前区连接S033”，或说明实际直接相连空间／方向）。

### K02｜已自主解决：S157西侧门接公共大厅

![K02 交通核及西侧公共大厅、上侧门诊通道]({prefix}K02_局部.png)

[同范围无标记原图]({prefix}K02_原图.png)

**判读结果：**二次放大可辨西侧门形开口，交通核S157直接接公共大厅S138，已记录R242及红点P226（1380，2220）。东侧另有向外的楼梯门，不据此编造通往S166的室内边。该项依据本图自主完成，无需用户确认。
'''
history=old[old.index('## 房名与范围核对（2026-11-05）'):]
history=history.replace('本轮 166 项待确认。沿用历史核对号与当前 S 编号；下列候选来自旧稿，尚未视为本轮确认。',
 '本轮166项已全部按用户填写同步。原始候选、依据和填写栏保留作为历史记录，以填写栏实际名称为准；核对号与S编号不变。')
history=history.replace('先核对名称、类别和空间范围；名称确认后，再逐张复核人员连通与可定位门洞。本对话仅处理23号图；本图当前无门洞红点，既有关系仍需复核。',
 '名称已同步；本图本轮连通与门位结果见上方概览；仅K01仍待确认，K02已自主解决。')
history=history.replace('**范围属性重点：**S092、S096、S133、S146、S150、S197、S202 请同时说明“露天／挑空”或“室内可步入”，用于确定是否计入室内相对面积。',
 '**范围属性已确认：**上述7处内庭院均为露天／挑空，不计室内面积。')
newmd=summary.rstrip()+'\n\n'+extra+'\n\n<details>\n<summary>展开：已同步的166项房名填写记录与原核对图</summary>\n\n'+history+'\n</details>\n'
oldrows=[line for line in old.splitlines() if re.match(r'^\|\s*\d+\s*\|\s*S',line)]
assert all(line in newmd for line in oldrows)
for rel in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',newmd):assert (P/rel).is_file(),rel
(P/'标注说明.md').write_text(newmd)
print('MD已更新；166行用户填写原样保留；K01附图待填写，K02已自主解决。')
