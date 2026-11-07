from pathlib import Path
import html,json,re,sys
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon

W=Path(__file__).resolve().parent
P=W.parents[1]/'标注试样/23_西安经开医院'
sys.path.insert(0,'/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts')
import annotation_tools as at
d=json.loads((P/'annotation.json').read_text())
md=(P/'标注说明.md').read_text()
answers={}
for line in md.splitlines():
    if re.match(r'^\|\s*\d+\s*\|\s*S',line):
        cols=[html.unescape(x.strip()) for x in line.strip('|').split('|')]
        assert cols[0]==cols[-1]
        answer=re.sub(r'<br\s*/?>','',cols[5]).strip()
        assert answer not in ('','待确认','待填写','待定')
        answers[cols[1]]=cols[2] if answer in ('已确认','同意') else answer
assert len(answers)==166
classes={
 'building_services':['强弱电','暖通','配电间','空调机房','新风机房','管井','用点机房'],
 'staff_support':['值班','医值','更衣','茶水间'],
 'examination':['急诊检查','妇科乳腺','男性心电'],
 'consultation':['诊室','便民门诊','妇科诊室'],
 'vertical_core':['电梯'], 'vestibule':['电梯前室'],
 'pharmacy':['急诊药房','处置、药房','中草药房','中药房','西药房'],
 'pharmacy_counter':['取药室','挂号取药'],
 'imaging':['B超','X光机','MRI','妇科B超','男性B超'],
 'treatment':['清创','治疗','石膏','处置','介入治疗'],
 'equipment_room':['设备','设备时','设备室'],
 'service':['谈话','VIP室'],
 'operating_room':['总诊手术'],
 'toilet':['女厕所','男厕所'],
 'registration':['挂号与收费','挂号收费'],
 'office':['办公','主任','医办','统计记账','财务'],
 'conference':['示教室'], 'entrance':['门厅'],
 'waste_handling':['回收室'], 'building_control':['控制室','消防监控室'],
 'patient_preparation':['准备间'], 'service_work_area':['取片'],
 'retail_service':['便民超市'], 'observation':['观察室'],
 'laboratory':['检验','采血'], 'medication_preparation':['调钡室'],
 'storage':['库房','中药库','西药库','中药药库','一般药品库','特殊药瓶库','药库','计算机室'],
 'unknown':['内庭院'],
}
typemap={name:typ for typ,names in classes.items() for name in names}
typemap['计算机室']='equipment_room'
for s in d['spaces']:
    if s['id'] in answers:
        name=answers[s['id']]; s.update(name=name,type=typemap[name])
        if s['type']=='vertical_core': s['level']='core_block'
        if s['type']=='building_services': s['scope']='building_support'
at.normalize(d)
(W/'名称同步后.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
(W/'本轮确认名称.json').write_text(json.dumps(answers,ensure_ascii=False,indent=2))

tiles=[('A_急诊',(1330,360,2330,850)),('B_放射',(160,960,1185,1710)),
       ('C_外科',(1340,960,2180,1460)),('D_药房',(160,1750,1185,2580)),
       ('E_中段门诊',(1340,1750,2180,2440)),('F_老年门诊',(160,2440,1190,2790)),
       ('G_体检',(1340,2360,2330,2870))]
img=Image.open(P/d['image']['file']).convert('RGB')
font=ImageFont.truetype('/System/Library/Fonts/STHeiti Medium.ttc',23)
small=ImageFont.truetype('/System/Library/Fonts/STHeiti Medium.ttc',18)
for title,box in tiles:
    crop=img.crop(box).resize(((box[2]-box[0])*2,(box[3]-box[1])*2))
    crop.save(W/(title+'_原图.png'))
    dr=ImageDraw.Draw(crop)
    for x in range((box[0]//100+1)*100,box[2],100):
        xx=(x-box[0])*2;dr.line((xx,0,xx,crop.height),fill=(150,195,220),width=1)
        dr.text((xx+2,2),str(x),font=small,fill='blue')
    for y in range((box[1]//100+1)*100,box[3],100):
        yy=(y-box[1])*2;dr.line((0,yy,crop.width,yy),fill=(150,195,220),width=1)
        dr.text((2,yy+2),str(y),font=small,fill='blue')
    for s in d['spaces']:
        poly=Polygon(s['polygon_px']);pt=poly.representative_point()
        if box[0]<pt.x<box[2] and box[1]<pt.y<box[3]:
            xy=((pt.x-box[0])*2,(pt.y-box[1])*2)
            text=s['id'];bb=dr.textbbox(xy,text,font=font)
            dr.rectangle(bb,fill='white');dr.text(xy,text,font=font,fill=(160,0,100))
    crop.save(W/(title+'_坐标编号.png'))
print('已读取166条明确填写；7项内庭院属性等待确认。已生成7个片区复核图。')
