from pathlib import Path
import hashlib
import importlib.util
import json
import re
import sys
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Point, Polygon

ROOT = Path(__file__).resolve().parents[4]
WORK = Path(__file__).resolve().parent
SAMPLE = ROOT / 'p-平面标注与数据处理/标注试样' / WORK.parent.name
SKILL = Path('/Users/hushili/.codex/skills/outpatient-plan-annotation')
OLD_MAP = ROOT / 'p-平面标注与数据处理/临时核对/16-20_名称核对_20261103' / WORK.parent.name / '本轮核对映射.json'
spec = importlib.util.spec_from_file_location('annotation_tools', SKILL / 'scripts/annotation_tools.py')
at = importlib.util.module_from_spec(spec)
spec.loader.exec_module(at)

# The decisions below are visual readings of the five photographs in this chat.
# Unknown functions remain unknown even where the printed word 单间 is readable.
DECISIONS = {
    '01': ('待配库', 'storage', '照片1北侧独立房内可辨“待配库”，不是自动接受旧候选。'),
    '02': ('审方、打印', 'service_work_area', '照片1上排小室可辨“审方、打印”。'),
    '03': ('核对、摆药', 'service_work_area', '照片1上排开放操作区可辨“核对、摆药”；纠正旧候选“贴签”。'),
    '04': ('传达', 'office', '照片1西北电梯旁小室可辨“传达”；保留原图简称。'),
    '06': ('抗生素配制', 'medication_preparation', '照片1及3并列配制房可辨“抗生素配制”。'),
    '07': ('成品库', 'storage', '照片1及3北侧东端大房可辨“成品库”。'),
    '09': ('脱衣', 'staff_support', '照片1及3西侧更衣组下端可辨“脱衣”。'),
    '10': ('脱衣', 'staff_support', '照片1及3东侧更衣组下端同样标“脱衣”。'),
    '12': ('高压氧舱室', 'treatment', '照片2的高压氧舱图示、舱室文字及相邻控制室共同确定功能；房名为概念描述。'),
    '13': ('储气间', 'building_services', '照片2两个供气设备符号所在独立房可辨“储气间”。'),
    '14': ('高压氧候诊区', 'hall', '照片2高压氧片区入口内有成排候诊座椅，与舱室和登记接待相邻；采用功能描述名。'),
    '15': ('登记、接待', 'service_work_area', '照片2楼梯西侧下方小空间可辨“登记、接待”。'),
    '16': ('输液室', 'treatment', '照片1及3蓝色大空间红色功能牌可辨“输液室”，不是据床椅直接推定留观。'),
    '24': ('DR', 'imaging', '照片2及3 CT北侧西小室标“DR”。'),
    '25': ('抢救室', 'resuscitation', '照片2及3 CT北侧东小室可辨“抢救室”。'),
    '26': ('阅片', 'imaging', '照片2及3 CT西邻室标“阅片”；纠正旧候选“暗室”。'),
    '27': ('值班', 'staff_support', '照片2及3抢救区东南端上方小室可辨“值班”。'),
    '28': ('仪器维护', 'equipment_room', '照片2、3及5治疗室东邻房可辨“仪器维护”。'),
    '29': ('120联络', 'office', '照片2急诊支持房可辨“120联络”；保留图面简称。'),
    '30': ('值班', 'staff_support', '照片2及4西侧上方房标“值班”；图面未明确性别，不沿用旧候选的“男”。'),
    '31': ('值班', 'staff_support', '照片2及4西侧下方房同标“值班”；图面未明确性别，不沿用旧候选的“女”。'),
    '36': ('发血', 'laboratory', '照片3及4南排紫色第二小室可辨“发血”；纠正旧候选“交血／配血”。'),
    '37': ('内科', 'consultation', '照片3及5眼科右邻诊室标“内科”，不是旧候选“骨科”。'),
    '38': ('配血', 'laboratory', '照片3、4及5检验区后排西小室可辨“配血”。'),
    '40': ('实验', 'laboratory', '照片3、4及5后排第三间实验用房可辨“实验”，与前两间同名。'),
    '41': ('设备间', 'equipment_room', '照片4检验区西侧窄小房可辨“设备间”。'),
    '42': ('污洗间', 'waste_handling', '照片4设备间下方窄小房可辨“污洗间”。'),
    '43': ('出入院办理', 'registration', '照片4及5黄色长柜台功能牌可辨“出入院办理”；纠正旧候选“急诊药房”。'),
    '44': ('异地医保', 'office', '照片3及5东南办公组东北房可辨“异地医保”。'),
    '47': ('急诊门厅', 'hall', '照片4旋转门所在绿色大厅红牌可辨“急诊门厅”。'),
    '49': ('库房', 'storage', '照片4急诊门厅西南角小室可辨“库房”；纠正旧候选“值班室”。'),
}

PENDING = {
    '05': ('普通药及营养液配制', '普通药品配制', '照片1及3可辨配制功能，但中段具体药品／营养液文字仍不够清楚；两候选共用配制文字依据，不能据此恢复完整原名。', '中'),
    '08': ('餐室', '库房', '照片1左侧支持组最下方两字仍有笔画粘连；旧候选保留作比较，不能确定首字。', '低'),
    '11': ('药品库', '药品相关支持房', '照片1及3斜角房内两字不够清楚；仅依药剂片区和旧文字线索，房间级用途证据不足。', '低'),
    '32': ('急诊检验区', '急诊输液区', '照片2及4区名仍有重影，现有布局不能区分用途；候选均不是确认事实。', '低'),
    '33': ('范围待核：可能是同一操作区', '独立小室', '照片4横向操作区中间竖线更像轴线，未见清晰实墙；需与34一并判断是否与32合并。', '低'),
    '34': ('范围待核：可能是同一操作区', '独立小室', '与33共享照片4的范围疑点：中间线疑为轴线；暂保留旧S编号及轮廓，尚未合并。', '低'),
    '35': ('验血', '取血', '照片3、4及5可辨末字“血”，首字笔画仍粘连；两候选共用此文字线索。', '中'),
    '39': ('储血', '输血', '照片3、4及5可辨末字“血”，首字“储／输”仍需确认；旧“血库／血液检验”候选留在历史备份。', '中'),
    '45': ('复印资料', '病案资料', '照片5可见东南独立办公房及模糊多字房名，仍不能可靠辨清；两候选仅为旧文字线索，功能证据不足。', '低'),
    '46': ('住院服务大厅', '其他公共服务门厅', '照片5红色长牌的中段专名仍难辨；有柜台和公共门厅布局，仅能确定大厅形态，不能据相邻住院电梯替代专名。', '低'),
    '48': ('导诊室', '导诊相关支持房', '照片4门厅西侧小室字样仍模糊；两候选共用原文字形和入口位置线索，不能确定。', '低'),
    '50': ('外送用房', '其他急诊支持用房', '照片4西南第二小室文字仍粘连，不能可靠辨字；候选仅来自旧文字线索与位置，房间级证据不足。', '低'),
}
for n in range(17, 24):
    PENDING[f'{n:02}'] = ('单间（功能待确认）', '输液单间／留观单间', '照片1、2及3均可读“单间”，但没有单间内部设施或用途专名；相邻输液室不足以确认每间的功能类别，名称和类别暂保留unknown。', '中')

ANCHORS = [
    (1140,590),(1290,590),(1720,600),(800,645),(1210,790),
    (1480,790),(1800,800),(940,900),(1105,905),(1640,905),
    (1740,1045),(550,1000),(675,980),(460,1190),(575,1270),
    (1550,1000),(1115,1215),(1175,1215),(1235,1215),(1293,1215),
    (1353,1215),(1412,1215),(1480,1215),(870,1420),(1065,1465),
    (850,1610),(1600,1522),(1550,1605),(410,1360),(200,1560),
    (200,1660),(420,1870),(495,1755),(610,1755),(687,1815),
    (760,1815),(940,1815),(760,1915),(850,1915),(1200,1980),
    (608,1964),(610,1983),(1210,2080),(2100,1850),(1905,1900),
    (2025,2345),(800,2280),(410,2210),(410,2340),(510,2350),
]
# Group names and ranges may change; review numbers and S IDs never do.
GROUPS = [
    (1,3,'北侧药剂上排',1),(4,4,'西北传达',1),
    (5,7,'北侧配制及成品库',1),(8,10,'北侧支持及更衣',1),
    (11,11,'北侧斜角支持房',1),(12,15,'西侧高压氧',2),
    (16,16,'蓝色输液室',3),(17,23,'蓝色连续单间',3),
    (24,26,'急诊影像及抢救支持',3),(27,28,'急诊东端支持',3),
    (29,31,'西侧急诊支持',2),(32,34,'西南功能及范围疑点',4),
    (35,37,'南排血液服务与诊室',3),(38,40,'检验区后排',5),
    (41,42,'检验区西侧小间',4),(43,43,'出入院办理',5),
    (44,46,'东南公共服务',5),(47,50,'急诊门厅及西南小间',4),
]


def make_image(base, bounds, entries, target, title, scale=2):
    x0,y0,x1,y1 = bounds
    canvas = base.crop(tuple(round(v*scale) for v in bounds)).convert('RGB')
    font='/Library/Fonts/Arial Unicode.ttf'
    title_font=ImageFont.truetype(font,26)
    subtitle_font=ImageFont.truetype(font,18)
    subtitle='固定核对号在房内；绿色=图面已辨读，橙色=待核。描边仍是待复核范围。'
    if canvas.width<1000:subtitle='房内数字：绿=已辨读，橙=待核'
    measure=ImageDraw.Draw(canvas)
    def wrap_text(text,font):
        lines=['']
        for ch in text:
            if measure.textlength(lines[-1]+ch,font=font)>canvas.width-30:lines.append('')
            lines[-1]+=ch
        return lines
    titles=wrap_text(title,title_font);subtitles=wrap_text(subtitle,subtitle_font)
    header=16+len(titles)*34+len(subtitles)*25
    out = Image.new('RGB',(canvas.width,canvas.height+header),'white')
    out.paste(canvas,(0,header))
    draw=ImageDraw.Draw(out)
    for i,line in enumerate(titles):draw.text((16,8+i*34),line,font=title_font,fill='#18314c')
    for i,line in enumerate(subtitles):draw.text((16,8+len(titles)*34+i*25),line,font=subtitle_font,fill='#52677b')
    for row in entries:
        n=row['number'];s=spaces[row['id']];color='#168267' if n in DECISIONS else '#b45309'
        pts=[((x-x0)*scale,(y-y0)*scale+header) for x,y in s['polygon_px']]
        draw.line(pts+[pts[0]],fill=color,width=2)
        x,y=ANCHORS[int(n)-1];cx=(x-x0)*scale;cy=(y-y0)*scale+header;r=(7 if n in {'41','42'} else 10)*scale
        draw.ellipse((cx-r,cy-r,cx+r,cy+r),fill='white',outline=color,width=3)
        draw.text((cx,cy),n,font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf',round((10 if n in {'41','42'} else 13)*scale)),anchor='mm',fill=color)
    out.save(target,quality=95)


if __name__ == '__main__':
    json_path=SAMPLE/'annotation.json';md_path=SAMPLE/'标注说明.md'
    for name in ['annotation.json','标注.svg','标注说明.md']:
        assert (SAMPLE/name).read_bytes()==(WORK/'修改前备份'/name).read_bytes(),f'{name} changed since backup; reread before applying.'
    data=json.loads(json_path.read_text());before=json.loads(json_path.read_text())
    old_md=md_path.read_text();mapping=json.loads(OLD_MAP.read_text())
    rows={}
    for line in old_md.splitlines():
        cells=[c.strip() for c in line.strip('|').split('|')]
        if len(cells)==7 and re.fullmatch(r'\d{2}',cells[0]):rows[cells[0]]=cells
    assert len(rows)==50
    assert all(rows[r['number']][1]==r['id'] for r in mapping)
    assert all(c[5]=='待确认' for c in rows.values()),'New user answers require a fresh review.'
    spaces={s['id']:s for s in data['spaces']}
    decisions=[]
    for row in mapping:
        n=row['number'];s=spaces[row['id']]
        if n in DECISIONS:
            name,kind,basis=DECISIONS[n];s.update(name=name,type=kind)
            if n=='43':s['scope']='inpatient_support'
            rows[n][2:5]=[name,'—',basis+' 图面辨读：高；已同步JSON/SVG，未冒充用户确认。']
            decisions.append({'number':n,'id':s['id'],'name':name,'type':kind,'basis':basis,'source':'2026-11-03用户照片；助手图面辨读'})
        else:
            name,alt,basis,confidence=PENDING[n]
            rows[n][2:5]=[name,alt,basis+f' 把握：{confidence}。']
    for sid in ['S037','S067']:spaces[sid]['type']='education'
    assert data['relations']==before['relations']
    assert [(s['id'],s['polygon_px'],s.get('area_ratio')) for s in data['spaces']]==[(s['id'],s['polygon_px'],s.get('area_ratio')) for s in before['spaces']]
    json_path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    at.render(data,json_path,SAMPLE/'标注.svg')
    tree=ET.parse(SAMPLE/'标注.svg')
    tree.getroot().find('{http://www.w3.org/2000/svg}text').text='18号东营市人民医院 · 急诊急救中心暨内科病房综合楼 · 一层标注草稿'
    tree.write(SAMPLE/'标注.svg',encoding='unicode')
    at.summary(data,WORK/'本轮概览.md')
    overview=(WORK/'本轮概览.md').read_text().replace('# 平面标注概览','# '+SAMPLE.name+'｜一层标注草稿',1)
    manual=old_md[old_md.index('**范围与层次：**'):old_md.index('## 名称核对填写表')]
    manual=re.sub(r'北侧具体功能及蓝色床位区用途尚未确认；相关空间保持 unknown，片区范围不作为已确定的专科训练标签。','北侧静脉药物配制相关房已部分辨读；蓝色主区已辨读为输液室，连续单间用途仍待核。未定空间不作为已确定的专科训练标签。',manual)
    manual=re.sub(r'\*\*待确认：\*\*.*?\n\n','',manual,flags=re.S)
    relative=Path('../../临时核对')/WORK.parent.name/WORK.name
    original=Image.open(SAMPLE/data['image']['file']).resize((data['image']['width']*2,data['image']['height']*2))
    for i,row in enumerate(mapping):assert Polygon(spaces[row['id']]['polygon_px']).contains(Point(*ANCHORS[i]).buffer(6 if row['number'] in {'41','42'} else 9)),row['number']
    make_image(original,(140,450,2210,2450),mapping,WORK/'房内编号总图.jpg','18号｜固定核对号01—50；原图定位总图')
    lines=[overview,manual,'## 照片房名核对与填写','',
        '本轮依据：2026-11-03聊天中提供的5张局部照片。31项原待核名称已由助手图面辨读同步；另将两处“示教”统一归入教学培训类别。现有133个S编号、50个核对号及原填写全部保留。',
        '','**填写方式：**绿色编号表示已有图面依据并已同步，橙色编号表示仍待核；“我的确认／备注”保留原值，助手辨读不自动替用户填写。可直接改预估名称并填“已确认”，也可写实际名称／类别／合并意见。',
        '','**范围重点：**32／S080、33／S081、34／S082疑似被轴线误拆；已在对应局部提出，尚未执行合并。17—23的“单间”字样虽可读，具体功能类别仍未确定，JSON继续unknown。',
        '','**阶段边界：**本轮只核房名、功能类别与范围；148条关系和所有多边形暂保留原样。等你说“房间标注完毕”后，再读取最新填写，落实明确修正、合并或排除，随后开展连通性复核。当前无室内门洞坐标和P红点，不代表没有门洞。',
        '',f'[查看原图]({data["image"]["file"]})｜[查看标注](标注.svg)',
        '',f'![18号房内编号总图]({relative}/房内编号总图.jpg)','']
    for start,end,title,photo in GROUPS:
        chosen=[r for r in mapping if start<=int(r['number'])<=end]
        polys=[Polygon(spaces[r['id']]['polygon_px']) for r in chosen]
        bounds=(max(130,min(p.bounds[0] for p in polys)-45),max(450,min(p.bounds[1] for p in polys)-40),min(2200,max(p.bounds[2] for p in polys)+45),min(2450,max(p.bounds[3] for p in polys)+40))
        tag=f'{start:02}' if start==end else f'{start:02}-{end:02}'
        name=f'局部_{tag}_房内编号.jpg';raw=f'局部_{tag}_照片原貌.jpg'
        base=Image.open(WORK/f'照片_{photo:02}_对齐原图.jpg')
        base.crop(tuple(round(v*2) for v in bounds)).save(WORK/raw,quality=95)
        make_image(base,bounds,chosen,WORK/name,f'{tag}｜{title}；照片{photo}')
        lines += [f'### {tag}｜{title}','',f'![{tag}：房内核对数字]({relative}/{name})','',f'[查看同范围无标记照片]({relative}/{raw})','']
        if start==32:lines+=['**范围问题：**33与34之间是否只有轴线、没有实体隔墙？请在对应确认栏说明是否将32—34合并，或写出实际空间范围。','']
        lines+=['| 核对号 | S编号 | 预估名称（可改） | 备选名称 | 依据与把握 | 我的确认／备注 | 核对号（重复） |','| --- | --- | --- | --- | --- | --- | --- |']
        for row in chosen:lines.append('| '+' | '.join(rows[row['number']])+' |')
        lines.append('')
    md_path.write_text('\n'.join(lines)+'\n')
    (WORK/'图面辨读同步记录.json').write_text(json.dumps(decisions,ensure_ascii=False,indent=2)+'\n')
    (WORK/'固定核对映射.json').write_text(json.dumps([{'number':r['number'],'id':r['id'],'state':'图面已辨读' if r['number'] in DECISIONS else '待核'} for r in mapping],ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'synchronized':len(decisions),'unknown':len(at.unresolved(data)),'spaces':len(spaces),'relations_unchanged':data['relations']==before['relations'],'groups':len(GROUPS)},ensure_ascii=False))
