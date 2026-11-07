from pathlib import Path
import json
R=Path(__file__).resolve().parent
M=json.loads((R.parent/'15_盐城市妇幼保健院_名称核对_20261101/核对号映射.json').read_text())
by_num={int(r['number']):r for r in M}
observations={}
def put(nums,name,typ,photo,evidence='房名文字可辨，按原图名称或缩写记录。'):
    if isinstance(nums,int):nums=[nums]
    for n in nums:
        assert str(n) not in observations,n
        observations[str(n)]={'number':by_num[n]['number'],'id':by_num[n]['id'],'name':name,'type':typ,'photo':photo,'evidence':evidence}
# Northern central segment: grouped 医办 labels apply to the partitioned row.
put(range(3,7),'医办','office',[2], '照片02上排“医办”文字可辨；逐间保留原隔墙及编号。')
# Both nursing wings. Bed counts are deliberately not inferred from blurred digits.
for nums,ph in [(range(26,44),1),(range(61,79),3)]:
    put(nums,'病房','ward',[ph],'对应房间可见床位图注，片区标题为“45床标准护理单元”；记录病房，不补写模糊床数。')
put([10,44],'风机房','building_services',[1,3])
put([13,51],'污洗','waste_handling',[1,3])
put([16,48],'医生办公','office',[1,3])
put([17,47],'护士办','office',[1,3])
put([18,46],'主任办','office',[1,3])
put([19,54],'更衣室','staff_support',[1,3])
put([20,60],'库房','storage',[1,3])
put([21,59],'治疗','treatment',[1,3])
put([22,58],'处置','treatment',[1,3])
put([23,57],'护士站','nurse_station',[1,3])
put([24,56],'监护','observation',[1,3])
put([25,55],'配餐','hospital_logistics',[1,3])
# West and east blue blocks; labels straddle some narrow-cell dividing lines.
put(list(range(79,87))+list(range(111,119)),'医办','office',[4,6], '同排多个“医办”成组标注可辨；每个有隔墙和门的原编号单元保留，未合并。')
put([88,89,95,96,105,106,110,120,121,127,128,137,138,142],'设备','equipment_room',[4,6])
put([91,94,97,100,101,104,107,126,129,132,133,136,141],'机房','building_services',[4,6], '图中“机房”在成对小间之间成组标注；保留原图已有分隔，不补具体设备名称。')
put([92,93,124,125],'更衣室','staff_support',[4,6])
put([109,140],'护士站','nurse_station',[4,6])
# Purple outpatient block.
put([143,148],'医办','office',[4])
put([144,149],'主任','office',[4])
put(145,'会议示教','conference',[4])
put([146,147],'更衣','staff_support',[4])
put([150,151,152,154,155,156,157,158,159,160,161,163,164,165,167,168,171],'诊室','consultation',[4,7])
put([162,166,175,176,177,178],'治疗','treatment',[4,7])
put([169,170],'护士站','nurse_station',[4,7])
put(174,'检查','examination',[4,7])
# Central laboratory block; ambiguous words remain pending.
put(180,'样本处理','laboratory',[5,9])
put(181,'扩增','laboratory',[5,9])
put(183,'HIV','laboratory',[5,9], '保留图中文字HIV，不从缩写扩写检验项目。')
put([185,186,187],'缓冲','vestibule',[5,9])
put(189,'生化免疫','laboratory',[5,9])
put(190,'细菌检验','laboratory',[9])
put(191,'男更','staff_support',[9])
put(192,'女更','staff_support',[9])
put(193,'医办','office',[9])
put(194,'检验室','laboratory',[9])
put(195,'主任','office',[9])
put(196,'男厕','toilet',[9])
put(198,'体液','laboratory',[9])
put(201,'女厕','toilet',[9])
# Infusion hall.
put(202,'儿童输液区','treatment',[6])
put(203,'输液大厅','treatment',[6])
put(204,'肌注','treatment',[6])
put(205,'护士站','nurse_station',[6])
put(206,'静注','treatment',[6])
put(207,'处置','treatment',[6])
put([208,209],'诊室','consultation',[6])
put([210,211],'医办','office',[6])
put([212,213,214],'等候','hall',[6])
# West vertical outpatient wings.
put([215,242,274],'主任','office',[7,8,10,11])
put([225,250,275],'医办','office',[7,8,10,11])
put([226,228],'更衣','staff_support',[7])
put(list(range(216,225))+[229,230,231,236,237,238]+list(range(243,250)),'诊室','consultation',[7])
put([232,233,239,240],'治疗','treatment',[7])
put([234,241],'护士站','nurse_station',[7])
put([235,266],'会议示教','conference',[7,8])
put([257,265,276,283]+list(range(258,265))+[268,269,270]+list(range(277,282))+list(range(284,291)),'诊室','consultation',[8,10,11])
put([271,272,291,292],'治疗','treatment',[8,10,11])
put([273,282],'护士站','nurse_station',[8,10,11])
# Reading / conference and administrative areas.
put(293,'设备间','building_services',[10])
put(294,'大会议厅','conference',[10,11], '大会议厅标题位于前区，结合整厅座席范围对应厅体S367，不将标题位置当作一间设备房。')
put([296,304,311,312,313,318]+list(range(297,304))+[306,307,308,314,315,316,317,323,324,325],'办公','office',[10,11], '成组“办公”文字与独立隔墙、门洞对应；保留图纸原名。')
put(305,'会议示教','conference',[10,11])
put(309,'打印室','office',[10,11])
put(326,'阅览室','education',[10,11])
put(328,'资料室','storage',[10,11])
put(333,'办公室','office',[10,11])
put([334,335,336],'会议室','conference',[10,11])
# Additional words checked with enlarged photo patches.
put([87,90,119,122],'离子控制室','building_control',[4,6])
put([98,99,102,103,130,131,134,135],'更衣室','staff_support',[4,6], '图中“更衣室”文字在两小单元间成组标注，保留原有分隔和编号。')
put(179,'试剂储存','laboratory',[9])
put(182,'产物分析','laboratory',[9])
put(184,'洁净区','laboratory',[9])
put(188,'污染区','laboratory',[9])
put(197,'凝血','laboratory',[9])
put(256,'会议室','conference',[9])
put(310,'办公区','office',[10,11], '大区域内有明确“办公区”图注；茶水与打印不据此扩成多个房间。')
(R/'照片识读记录.json').write_text(json.dumps(observations,ensure_ascii=False,indent=2)+'\n')
print('可同步',len(observations),'剩余',336-len(observations))
for group in range(14):
    pending=[r for r in M if r['group']==group and str(int(r['number'])) not in observations]
    print('片区',group+1,', '.join(r['number']+'/'+r['id'] for r in pending))
