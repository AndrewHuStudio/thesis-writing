"""Create a traceable first-pass spatial annotation, without changing the source."""
from pathlib import Path
import base64
from collections import Counter
import hashlib
import html
import json
import math
import shutil
import xml.etree.ElementTree as ET

import pymupdf

ROOT = Path('/Users/hushili/Documents/毕业 - 大论文写作/大论文')
SOURCE = ROOT / 'i-医院门诊平面/山东省立医院儿科综合楼_一层平面图.jpg'
OUT = ROOT / 'p-写作过程/标注试样/山东省立医院儿科综合楼_一层_概念连通标注_v3'
OUT.mkdir(parents=True, exist_ok=True)
BASE_W, BASE_H = 1992, 1248
W, H = 2796, 1751
FX, FY = W / BASE_W, H / BASE_H

nodes = []

def add(i, name, category, scope, box=None, poly=None, level='room',
        name_status='readable', candidate=None, note='', label_pos=None):
    if box:
        x1, y1, x2, y2 = box
        poly = [[x1,y1],[x2,y1],[x2,y2],[x1,y2]]
    points = [[round(x*FX,2), round(y*FY,2)] for x,y in poly]
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    signed_area = sum(points[j][0]*points[(j+1)%len(points)][1] - points[(j+1)%len(points)][0]*points[j][1] for j in range(len(points))) / 2
    area = abs(signed_area)
    cx = sum((points[j][0]+points[(j+1)%len(points)][0])*(points[j][0]*points[(j+1)%len(points)][1]-points[(j+1)%len(points)][0]*points[j][1]) for j in range(len(points))) / (6*signed_area)
    cy = sum((points[j][1]+points[(j+1)%len(points)][1])*(points[j][0]*points[(j+1)%len(points)][1]-points[(j+1)%len(points)][0]*points[j][1]) for j in range(len(points))) / (6*signed_area)
    nid = f'S{i:03d}'
    lp = label_pos or [min(p[0] for p in poly)+7, min(p[1] for p in poly)+10]
    nodes.append({
        'id': nid, 'name': name, 'category': category, 'scope': scope,
        'node_level': level, 'name_status': name_status,
        'candidate_name': candidate, 'annotation_method':'assistant_visual_annotation_on_source',
        'review_status': 'pending_user_or_second_review',
        'boundary_status': 'approximate_wall_centerline_or_visible_zone_envelope',
        'polygon_px': points,
        'polygon_normalized': [[round(x/W,7),round(y/H,7)] for x,y in points],
        'bbox_xyxy_px': [min(xs),min(ys),max(xs),max(ys)],
        'centroid_px': [round(cx,2),round(cy,2)], 'area_px2': round(area,2),
        'bbox_aspect_ratio': round((max(xs)-min(xs))/(max(ys)-min(ys)),5),
        'area_m2': None,
        'area_m2_estimate_from_provisional_axis_scale': round(area / FX / FY * (84.9/1365) * (56.4/917),2),
        'source_evidence': 'visible_source_text' if name_status=='readable' else ('partial_text_and_geometry' if candidate else 'visible_boundary_only'),
        'note': note,
        '_poly_base': poly, '_label_base': lp,
    })

# Public halls / services. Broad spaces and transport cores are explicit levels,
# never silently treated as single closed rooms.
add(1,'门诊大厅','hall','public_service',poly=[[314,181],[744,181],[770,189],[788,215],[794,245],[794,412],[1045,412],[1045,538],[314,538]],level='open_space',note='弧形外缘以折线近似；大厅连通范围需复核。',label_pos=[430,270])
add(2,'出入院大厅','hall','inpatient_public_service',poly=[[1045,412],[1423,412],[1423,1098],[1297,1098],[1297,664],[1045,664]],level='open_space',note='L形区域整体标注；内部通行分段未拆成多个房间。',label_pos=[1180,470])
add(3,'导医台','service','public_service',poly=[[183,245],[190,213],[210,190],[245,181],[314,181],[314,352],[183,352]],level='functional_block',note='弧线近似；服务区是否完全封闭未确认。')
add(4,'自助银行','service','public_service',box=[920,352,1045,412])
add(5,'门斗','entrance','public_service',box=[1045,352,1171,412])
add(6,'电梯及前厅组','vertical_core','staff_or_public_unknown',box=[1171,352,1360,412],level='core_block',name_status='descriptive',candidate='医护电梯厅',note='组内电梯、井道及前厅未逐个拆分；通行权限未知。')
add(7,'待核实前室','unknown','public_service',box=[1360,352,1423,412],name_status='unresolved',candidate='公用前室')
add(8,'西北楼梯间','vertical_core','public_service',box=[183,352,314,412],level='core_block',name_status='descriptive')
add(9,'西侧电梯及扶梯组','vertical_core','public_service',box=[183,412,314,538],level='core_block',name_status='descriptive',note='设备组边界，不代表单个房间。')
add(10,'北侧自动扶梯区','vertical_core','public_service',box=[794,352,920,412],level='core_block',name_status='descriptive')
add(11,'东北楼梯间','vertical_core','public_service',box=[1423,352,1550,412],level='core_block',name_status='descriptive')
add(12,'挂号收费','registration','public_service',box=[314,538,619,610],level='functional_block',note='只圈出北侧功能区；南侧柜台、排队带尚未完成细分。')
add(13,'门诊取药服务区','pharmacy_counter','outpatient_support',box=[619,538,1045,610],level='open_space',note='v2 将北侧公共取药区与南侧柜台工作带分开。与挂号收费区之间的轴线不当作实体隔墙。')
add(14,'办公','office','outpatient_support',box=[561,610,619,664])
add(15,'待核实小房间','unknown','public_service',box=[314,610,370,664],name_status='unresolved',candidate=None)
add(16,'门诊药房','pharmacy','outpatient_support',box=[314,664,1045,916],note='局部放大核实原文为“门诊药房”；内部为药架，不按候诊座椅判断。北侧柜台前的窄带未并入。',label_pos=[750,760])
add(17,'病房药房','pharmacy','inpatient_support',box=[1045,832,1232,1041],note='局部放大核实原文为“病房药房”；靠窗口一侧的墙线和柜台边界需复核。',label_pos=[1070,895])
add(18,'病房取药服务区','pharmacy_counter','inpatient_support',box=[1232,832,1297,1041],level='open_space',name_status='partial',candidate='病房取药',note='v2 合并原 S018/S019；原分界是穿过区域的轴线，未见实体隔墙。窗口和上下端门分别记录。')
add(20,'中部交通核（前室外）','vertical_core','public_service',poly=[[1105,664],[1297,664],[1297,832],[1045,832],[1045,704],[1105,704]],level='core_block',name_status='descriptive',note='v2 单独拆出北侧前室 S084。其余楼梯、电梯和扶梯仍为聚合块，内部路径尚不能视为全部互通。')
add(21,'南侧楼梯间','vertical_core','public_service',box=[1045,1041,1171,1098],level='core_block',name_status='descriptive')
add(22,'南侧电梯及前厅','vertical_core','public_service',box=[1171,1041,1297,1098],level='core_block',name_status='descriptive')

# South outpatient strip: keep individual consultation-room instances.
add(23,'普通门诊通道','corridor','ordinary_outpatient',box=[183,916,619,964],level='open_space',note='原图文字按视觉判读，通行人群和权限未作为已知标签。',label_pos=[385,932])
add(24,'南侧独立入口通道','corridor','south_clinic_scope_unknown',box=[619,916,689,1098],level='open_space',name_status='descriptive',note='入口及通道内的小字未完全辨认，不推断具体科室。')
add(25,'发热门诊通道','corridor','fever_outpatient',box=[689,916,920,964],level='open_space',note='原图名称视觉判读；是否完全独立通行需核实。',label_pos=[738,932])
add(26,'南侧东端通道','corridor','outpatient_support',box=[974,916,1045,1098],level='open_space',name_status='descriptive')
add(27,'医务廊（西）','corridor','ordinary_outpatient',poly=[[314,1019],[619,1019],[619,1047],[346,1047],[346,1098],[314,1098]],level='open_space',name_status='partial',candidate='医务廊',note='v2 补西端通道支路；功能字样部分可读，不据此确认医护专用权限。',label_pos=[500,1028])
add(28,'西南交通前厅','corridor','ordinary_outpatient',box=[490,1047,561,1098],level='open_space',name_status='descriptive')
add(29,'卫生间01','toilet','ordinary_outpatient',box=[314,964,346,1019],name_status='partial',candidate='WC',note='未辨认性别或无障碍属性。')
add(30,'卫生间02','toilet','ordinary_outpatient',box=[346,964,378,1019],name_status='partial',candidate='WC',note='未辨认性别或无障碍属性。')
add(31,'诊室01','consultation','ordinary_outpatient',box=[378,964,424,1019])
add(32,'诊室02','consultation','ordinary_outpatient',box=[424,964,474,1019])
add(33,'诊室03','consultation','ordinary_outpatient',box=[474,964,520,1019])
add(34,'诊室04','consultation','ordinary_outpatient',box=[520,964,570,1019])
add(35,'分诊','triage','ordinary_outpatient',box=[570,964,619,1019])
add(36,'卫生间03','toilet','ordinary_outpatient',box=[346,1047,378,1098],name_status='partial',candidate='WC',note='v2 将西侧通道支路归回 S027。')
add(37,'西南楼梯间','vertical_core','ordinary_outpatient',box=[378,1047,490,1098],level='core_block',name_status='descriptive')
add(38,'西南电梯','vertical_core','ordinary_outpatient',box=[561,1047,619,1098],level='core_block',name_status='descriptive')
add(39,'待核实服务间','unknown','fever_outpatient',box=[689,964,735,1062],name_status='unresolved',candidate='隔离／挂号',note='两行小字尚不能可靠确认，不用候选文字充当功能真值。')
add(40,'诊室05','consultation','fever_outpatient',box=[735,964,783,1062])
add(41,'诊室06','consultation','fever_outpatient',box=[783,964,832,1062])
add(42,'诊室07','consultation','fever_outpatient',box=[832,964,881,1062])
add(43,'卫生间04','toilet','fever_outpatient',box=[881,964,920,1014],name_status='partial',candidate='WC')
add(44,'卫生间05','toilet','fever_outpatient',box=[881,1014,920,1062],name_status='partial',candidate='WC')
add(45,'医务廊（东）','corridor','fever_outpatient',box=[689,1062,920,1098],level='open_space',name_status='partial',candidate='医务廊',note='名称部分可读，通行权限待核。',label_pos=[805,1073])
add(46,'财务','office','outpatient_support',box=[920,916,974,964])
add(47,'主任办','office','outpatient_support',box=[920,964,974,1030])
add(48,'医办','office','outpatient_support',box=[920,1030,974,1098])

# East public service strip; unresolved names are not invented.
add(49,'出入院手续服务带','service','inpatient_public_service',box=[1423,412,1486,538],level='functional_block',name_status='partial',candidate='出入院手续',note='柜台服务带，非单一封闭房间。')
add(50,'办公01','office','inpatient_public_service',box=[1486,412,1550,474])
add(51,'办公02','office','inpatient_public_service',box=[1486,474,1550,538])
add(52,'财务','office','inpatient_public_service',box=[1486,538,1550,664])
add(53,'手续服务等候带','service','inpatient_public_service',box=[1423,538,1486,664],level='functional_block',name_status='descriptive',note='名称为位置描述，非原图明确功能标签。')
add(54,'待核实服务用房','unknown','inpatient_public_service',box=[1423,664,1550,790],name_status='unresolved',candidate=None)
add(55,'东侧卫生间（西）','toilet','public_service',box=[1423,830,1488,916],name_status='descriptive',note='v2 将原卫生间组拆开，性别未核实；南北两个可见门口分别记录。')
add(56,'东侧公共通道','corridor','public_service',box=[1423,916,1550,964],level='open_space',name_status='descriptive')
add(57,'消防控制室（候选）','unknown','building_support',box=[1423,964,1550,1098],name_status='partial',candidate='消防控制室',note='小字需复核，候选名称不作为功能真值。')

# East emergency wing.
add(58,'内庭绿化带','landscape','nonclinical',box=[1550,412,1615,768],level='landscape',name_status='descriptive',note='非室内房间，默认排除训练。')
add(59,'待核实北端房间','unknown','emergency',box=[1550,215,1683,260],name_status='unresolved',candidate=None)
add(60,'急诊北侧交通核','vertical_core','emergency',poly=[[1550,260],[1683,260],[1683,352],[1615,352],[1615,412],[1550,412]],level='core_block',name_status='descriptive',note='v2 单独拆出公用前室 S085；交通核内部仍未逐一细分。')
add(61,'急诊诊区内廊','corridor','emergency',box=[1683,215,1722,768],level='open_space',name_status='descriptive',note='v2 不再将隔着门的公用前室直接并入本通道。',label_pos=[1691,540])
add(62,'待核实北端小间01','unknown','emergency',box=[1722,215,1760,260],name_status='unresolved',candidate=None)
add(63,'待核实北端小间02','unknown','emergency',box=[1760,215,1828,260],name_status='unresolved',candidate=None)
add(64,'留观区域（候选）','unknown','emergency',box=[1722,260,1828,516],name_status='partial',candidate='留观室',note='可见床位和局部文字；横穿该区的轴线未当作隔墙。',label_pos=[1750,300])
add(65,'待核实急诊辅助间','unknown','emergency',box=[1615,412,1683,452],name_status='unresolved',candidate=None)
add(66,'诊室08','consultation','emergency',box=[1615,452,1683,516])
add(67,'诊室09','consultation','emergency',box=[1615,516,1683,579])
add(68,'诊室10','consultation','emergency',box=[1615,579,1683,642])
add(69,'诊室11','consultation','emergency',box=[1615,642,1683,704])
add(70,'待核实急诊小间01','unknown','emergency',box=[1615,704,1646,768],name_status='unresolved',candidate=None)
add(71,'待核实急诊小间02','unknown','emergency',box=[1646,704,1683,768],name_status='unresolved',candidate=None)
add(72,'超声室（候选）','unknown','emergency',box=[1722,516,1828,579],name_status='partial',candidate='B超',note='仅候选功能，不作为已核实分类。')
add(73,'心电','examination','emergency',box=[1722,579,1828,642])
add(74,'检验','laboratory','emergency',box=[1722,642,1828,704])
add(75,'急诊药房','pharmacy','emergency',box=[1722,704,1828,768])
add(76,'急诊诊区南端过渡带','corridor','emergency',box=[1683,768,1828,790],level='open_space',name_status='descriptive')
add(77,'抢救室','resuscitation','emergency',box=[1550,768,1683,916],note='v2 将北侧床位带并回本室，不以穿过床位的轴线分割房间。',label_pos=[1572,840])
add(78,'急诊大厅及南侧交通带','hall','emergency',poly=[[1683,790],[1828,790],[1828,894],[1722,894],[1722,958],[1828,958],[1828,964],[1550,964],[1550,916],[1683,916]],level='open_space',label_pos=[1710,837])
add(79,'挂号收费（急诊）','registration','emergency',box=[1722,894,1828,922])
add(80,'护士站','nurse_station','emergency',box=[1722,922,1828,958])
add(81,'急诊南侧交通核','vertical_core','emergency',box=[1550,964,1828,1019],level='core_block',name_status='descriptive',note='电梯、值班小间及楼梯合并标注，未拆为房间。',label_pos=[1660,989])

add(82,'挂号柜台南侧工作带','service_work_area','outpatient_support',box=[370,610,561,664],level='functional_block',name_status='descriptive',note='v2 补原未标区域；与北侧挂号区之间的柜台窗口和门分开记录。')
add(83,'门诊取药南侧工作带','service_work_area','outpatient_support',box=[619,610,1045,664],level='functional_block',name_status='descriptive',note='由原 S013 拆出；与北侧取药服务区之间的窗口不等于人员通路。')
add(84,'前室（中部）','vestibule','public_service',box=[1045,664,1105,704],note='v2 从原 S020 拆出，可见南北两个门口。')
add(85,'公用前室（急诊北）','vestibule','emergency',box=[1615,352,1683,412],name_status='partial',candidate='公用前室',note='v2 分开记录西侧交通核和东侧内廊的门，避免把隔门空间当成无分隔区域。')
add(86,'东侧卫生间前廊','corridor','public_service',box=[1423,790,1515,830],level='open_space',name_status='descriptive',note='v2 从原 S055 拆出；洗手／前廊区域。')
add(87,'卫生间北侧附属小间','unknown','public_service',box=[1515,790,1550,830],name_status='unresolved',candidate=None,note='v2 从原 S055 拆出，原文字待核。')
add(88,'东侧卫生间（东）','toilet','public_service',box=[1488,830,1550,916],name_status='descriptive',note='v2 从原 S055 拆出，性别未核实；南北门分别记录。')

for n in nodes:
    n['annotation_precision']='conceptual_floorplan_topology'
    if n['id'] in ['S003','S079','S080']:
        n['node_level']='semi_open_space'
        n['boundary_type']='half_height_wall'
        n['polygon_boundary_semantics']='functional_zone_extent_not_full_height_wall'
        n['generic_person_access']=True
        n['door_position_status']='unspecified_not_required_at_concept_stage'
        n['access_evidence']='user_clarification'
        n['note']='用户确认：半墙服务区，与外部公共空间可达；小门／矮门位置可在施工阶段确定。本轮不设定具体门坐标。'
    if n['id']=='S020':
        n['name']='中部电梯厅及交通核'
        n['central_subspace_type']='elevator_lobby'
        n['elevator_door_facing']='from_central_lobby_towards_left_and_right'
        n['note']='用户确认中央区域为电梯厅，向两侧进入电梯；撤回此前将中央图形直接解释为扶梯的判断。概念尺度保留整体节点。'
    if n['id']=='S009':
        n['user_confirmed_region_continuity']=['horizontal','vertical']
        n['note']='用户以箭头确认横向及纵向区域贯通；记录区域级可达，不生成穿越梯井的直线路径。'
    if n['id']=='S081':
        n['user_confirmed_access_side']='north_from_upper_hall'
        n['note']='用户确认从上方前厅方向进入电梯／楼梯区域；本轮整体保留，不追问施工级门位和内部距离。'
lookup = {n['id']:n for n in nodes}
relations=[]
door_markers=[]

def door(a,b,x,y,kind='direct_door_candidate',note='可见门洞／开启弧线的第二轮视觉判读；位置为近似值。',segment=None):
    rid=f'R{len(relations)+1:03d}'
    did=f'P{len(door_markers)+1:03d}'
    movement=kind in ['direct_door_candidate','open_passage_candidate','zone_continuity_candidate']
    aggregate_ids=[f'S{i:03d}' for i in [a,b] if lookup[f'S{i:03d}']['node_level']=='core_block']
    relations.append({'id':rid,'source':f'S{a:03d}','target':f'S{b:03d}',
                      'relation_type':kind,'label':None,'candidate_label':1,
                      'review_status':'pending','evidence_marker':did,
                      'access_permissions':'unknown','directionality':'unknown','note':note,
                      'is_movement_candidate':movement,'is_service_candidate':kind=='service_window_candidate',
                      'aggregate_endpoint_ids':aggregate_ids,
                      'evidence_segment_px':[[round(xx*FX,2),round(yy*FY,2)] for xx,yy in segment] if segment else None})
    door_markers.append({'id':did,'position_px':[round(x*FX,2),round(y*FY,2)],
                         'space_ids':[f'S{a:03d}',f'S{b:03d}'],
                         'marker_type':kind,'review_status':'pending','is_movement_candidate':movement,
                         'access_permissions':'unknown','aggregate_endpoint_ids':aggregate_ids,
                         'segment_px':[[round(xx*FX,2),round(yy*FY,2)] for xx,yy in segment] if segment else None,
                         '_segment_base':segment,'note':note, '_base':[x,y]})

door(1,2,1045,477)
door(4,1,937,412)
door(5,2,1107,412)
door(6,2,1243,412)
door(7,2,1389,412)
door(7,11,1423,380)
door(8,9,290,412)

# User arrow: the north gap and the absence of a wall between functional zones
# are different observations, and neither requires a door-leaf symbol.
door(1,13,654,538,'open_passage_candidate',note='用户箭头对应区域：大厅与取药区之间可见连续开口，未见门扇。',segment=[[621,538],[687,538]])
door(12,13,619,574,'zone_continuity_candidate',note='挂号收费与取药区之间仅见轴线／人为功能分界，未见实体隔墙；记录区域连续。',segment=[[619,540],[619,607]])
door(12,82,377,610)
door(14,82,561,648)
door(15,82,370,650)
door(13,83,630,610)
door(13,83,1032,610)
door(16,83,630,664)
door(16,83,1032,664)
door(12,82,466,610,'service_window_candidate',note='可见连续柜台及坐席，服务联系；不能作为人员穿行边。',segment=[[390,610],[551,610]])
door(13,83,826,610,'service_window_candidate',note='取药柜台／工作位形成服务界面；门口另行记录。',segment=[[655,610],[1012,610]])
door(2,84,1075,664)
door(84,20,1075,704)
door(2,20,1204,664)
door(17,26,1045,940)
door(17,18,1232,848)
door(17,18,1232,1018)
door(18,2,1297,876)
door(17,18,1232,942,'service_window_candidate',note='药房与病房取药区之间可见柜台及工作位；上下端门口单独记录。',segment=[[1232,870],[1232,998]])
door(21,22,1171,1071)

door(23,24,619,940)
door(25,24,689,940)
door(29,23,327,964)
door(30,23,359,964)
for a,x in [(31,397),(32,444),(33,491),(34,539)]: door(a,23,x,964)
for a,x in [(31,415),(32,435),(33,501)]: door(a,27,x,1019)
door(35,24,619,980)
door(36,27,361,1047)
door(37,28,490,1071)
door(27,24,619,1033)
door(27,28,524,1047,'zone_continuity_candidate',note='医务廊与楼梯前厅之间未见隔墙，为连续交通空间。',segment=[[493,1047],[558,1047]])
door(39,24,689,984)
for a,x in [(40,751),(41,802),(42,851)]: door(a,25,x,964)
for a,x in [(40,770),(41,819),(42,867)]: door(a,45,x,1062)
door(43,25,901,964)
door(44,45,900,1062)
door(45,24,689,1080)
door(26,16,1017,916)
door(46,26,974,948)
door(47,26,974,1014)
door(48,26,974,1060)
door(2,49,1423,426)
door(2,53,1423,551)
door(2,49,1423,484,'service_window_candidate',note='出入院服务柜台界面，不作为人员通路。',segment=[[1423,447],[1423,520]])
door(2,53,1423,611,'service_window_candidate',note='财务服务柜台界面，不作为人员通路。',segment=[[1423,578],[1423,644]])
door(50,49,1486,440)
door(51,49,1486,500)
door(52,53,1486,592)
door(54,2,1423,678)
door(2,86,1423,805)
door(86,55,1441,830)
door(86,88,1501,830)
door(86,87,1515,810)
door(55,56,1441,916)
door(88,56,1501,916)
door(2,56,1423,940)
door(56,78,1550,940,'zone_continuity_candidate',note='公共横向交通带跨人为区域边界连续，无门扇和隔墙；用户标记位置之一。',segment=[[1550,920],[1550,961]])
door(57,2,1423,982)
door(59,61,1683,241)
door(62,61,1722,244)
door(62,64,1740,260)
door(63,64,1775,260)
door(64,61,1722,290)
door(60,85,1615,392)
door(85,61,1683,392)
door(65,85,1658,412)
for a,y in [(66,500),(67,564),(68,627),(69,690)]: door(a,61,1683,y)
door(70,77,1631,768)
door(71,77,1667,768)
door(72,61,1722,546)
door(73,61,1722,607)
door(74,61,1722,671)
door(75,61,1722,733)
door(77,78,1683,846)
door(61,76,1702,768,note='v1 曾误记为开放连接；放大后可见双扇门，v2 改为门洞候选。')
door(76,78,1765,790,'zone_continuity_candidate',note='过渡带与急诊大厅之间未见实体隔断；轴线不当成墙。',segment=[[1725,790],[1824,790]])
door(78,81,1696,964,note='可见进入南侧交通核的门；交通核内部未完整拆分，不由此推断任意内部空间互通。')
door(78,81,1660,964,note='可见交通核内小间的北向门；小间尚未独立成节点，需继续拆分，不能解释为贯穿整个交通核的通路。')

def shared(a,b,x,y):
    relations.append({'id':f'R{len(relations)+1:03d}','source':f'S{a:03d}','target':f'S{b:03d}',
                      'relation_type':'shared_wall_candidate','label':None,'candidate_label':1,
                      'review_status':'pending','evidence_point_px':[round(x*FX,2),round(y*FY,2)],
                      'note':'可见相邻隔墙的首轮判读；共墙不等于直接通行。'})
for a,b,x,y in [(31,32,424,991),(32,33,474,991),(33,34,520,991),(34,35,570,991),
                 (39,40,735,1010),(40,41,783,1010),(41,42,832,1010),
                 (50,51,1518,474),(66,67,1648,516),(67,68,1648,579),(68,69,1648,642),
                 (73,74,1774,642),(74,75,1774,704),(79,80,1774,922)]: shared(a,b,x,y)

def conceptual_access(a,b,case,reason):
    relations.append({'id':f'R{len(relations)+1:03d}','source':f'S{a:03d}','target':f'S{b:03d}',
        'relation_type':'conceptual_access_user_confirmed','label':1,'candidate_label':1,
        'review_status':'user_confirmed_at_concept_level','is_movement_candidate':True,
        'is_service_candidate':False,'evidence_marker':None,'evidence_position_px':None,
        'door_geometry_status':'not_specified_not_required_at_this_stage',
        'source_authority':'user_clarification_in_chat','question_id':case,
        'access_permissions':'unknown','directionality':'unknown','note':reason,
        'aggregate_endpoint_ids':[f'S{i:03d}' for i in [a,b] if lookup[f'S{i:03d}']['node_level']=='core_block']})

conceptual_access(3,1,'01','半墙导医服务区，与相邻门诊大厅可达；小门位置未定，不伪造门洞点。')
conceptual_access(10,1,'02','用户确认北侧扶梯从左侧门诊大厅进入。')
conceptual_access(38,28,'03','用户确认梯门朝 B，即西侧前厅；仅记录接口方向。')
conceptual_access(79,78,'04','用户确认急诊挂号收费为半墙服务区，与外部公共空间可达；具体矮门位置未定。')
conceptual_access(80,78,'05','用户确认护士站为半墙，与外部公共空间联通；不设定具体小门位置。')
conceptual_access(9,1,'06','用户箭头确认西侧交通核区域向大厅贯通；不据此指定穿越构件的路径。')
conceptual_access(81,78,'08','用户确认南侧交通核由上方前厅进入；概念级可达成立。')

entrances=[]
for i,name,x,y,sid,status in [
    (1,'门诊入口',551,181,1,'readable'),
    (2,'保健入口（文字待核）',1107,352,5,'partial'),
    (3,'医护入口',1240,352,6,'readable'),
    (4,'南侧独立入口（科名待核）',652,1098,24,'partial'),
    (5,'次入口',1359,1098,2,'readable'),
    (6,'急诊入口',1828,829,78,'readable'),
    (7,'东北外门（功能未标明）',1702,215,61,'descriptive'),
    (8,'南侧电梯前厅外门（用途待核）',1205,1098,22,'descriptive'),
    (9,'西侧医务廊外门（用途待核）',331,1098,27,'descriptive'),
    (10,'西南前厅外门（用途待核）',530,1098,28,'descriptive'),
    (11,'南侧东端通道外门（用途待核）',1015,1098,26,'descriptive'),
    (12,'东侧医务廊外门（用途待核）',712,1098,45,'descriptive'),
    (13,'北侧前室外门（用途待核）',1391,352,7,'descriptive')]:
    entrances.append({'id':f'E{i:03d}','name':name,'position_px':[round(x*FX,2),round(y*FY,2)],
                      'space_id':f'S{sid:03d}','text_status':status,'review_status':'pending','_base':[x,y]})

shutil.copyfile(SOURCE,OUT/'source.jpg')
sha=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
for n in nodes:
    n['connectivity_review_status']='second_visual_pass_incomplete'
    n['internal_connectivity_status']='kept_as_conceptual_aggregate_internal_route_out_of_scope' if n['node_level']=='core_block' else 'not_independently_validated'
public_nodes=[{k:v for k,v in n.items() if not k.startswith('_')} for n in nodes]
public_doors=[{k:v for k,v in d.items() if not k.startswith('_')} for d in door_markers]
public_entries=[{k:v for k,v in d.items() if not k.startswith('_')} for d in entrances]
metadata={
    'schema_version':'0.3.0','annotation_date':'2026-10-25',
    'status':'concept_level_topology_with_user_confirmed_access',
    'source':{'relative_path':'source.jpg','original_path':str(SOURCE),
              'sha256':sha,'width':W,'height':H,
              'identity_status':'hospital_building_floor_taken_from_local_filename_not_independently_verified',
              'service_population':'pediatric_building_per_filename_not_general_adult_outpatient_sample'},
    'coordinate_system':{'origin':'top_left','x':'right','y':'down','unit':'source_image_pixel'},
    'calibration':{'status':'provisional_not_independently_verified',
                   'axis_span_mm':[84900,56400],
                   'axis_span_px_base':[1365,917],
                   'note':'总轴线尺寸用于面积估算；扫描变形、内净面积与墙体占地均未复核。area_m2 保留 null。'},
    'geometry_method':'assistant_placed_approximate_polygons_using_visible_walls_and_zone_boundaries',
    'coverage':'whole_image_second_connectivity_pass_selected_spaces_not_exhaustive_room_segmentation',
    'unannotated_or_aggregated':['左侧停车位不标作房间','柜台、排队带及部分开放空间未完整细分',
                                '交通核内部、电梯井、部分前室和小附属间采用聚合块',
                                '床位区内部未按轴线或家具拆分成房间','未完成所有门、服务窗口与所有共墙关系标注'],
    'training_ready':False,
    'negative_edge_policy':'unlisted_pairs_are_unknown_not_negative',
    'candidate_relation_policy':'label is null until evidence is reviewed; candidate_label is not ground truth',
    'mixed_level_policy':'room, open_space, functional_block, core_block, landscape must be explicitly selected or separated before modelling',
    'inference_leakage_warning':'真实质心、原图邻接与门洞信息是标注或评价资料；新设计中不可获得时不能直接作为预测输入。',
    'split_group':'山东省立医院儿科综合楼_待核项目组',
    'grouping_policy':'同源裁图、同楼层、增强副本及同医院资料不得因此被视为独立医院或任意跨数据集分组',
    'revision':'v3_conceptual_topology',
    'previous_version':'山东省立医院儿科综合楼_一层_连通性复核_v2',
    'precision_policy':{'target':'conceptual_layout_generation','required':'space_type_and_topological_access',
        'not_required':['精确小门位置','门宽','门扇构造','交通核内部精确路径'],
        'half_height_wall':'半墙服务区可记录概念级通达；门位置未定不作为缺标阻塞。',
        'provenance':'用户对编号01、04、05及概念平面精度的明确说明'},
    'pending_user_clarification_ids':[],
    'retired_space_ids':{'S019':'merged_into_S018_due_to_no_physical_partition'},
    'refined_space_ids':{'S013':['S013','S083'],'S020':['S020','S084'],'S055':['S055','S086','S087','S088'],'S060':['S060','S085'],'S061':['S061','S085'],'S036':['S036','S027']},
    'connectivity_complete':False,
    'relation_semantics':{
        'direct_door_candidate':'可见门洞／门扇开启符号，人员通行可能，权限未知',
        'open_passage_candidate':'可见无门开口，人员通行可能，权限未知',
        'zone_continuity_candidate':'人为功能分区边界处无实体隔断；不应凭标注线产生墙',
        'service_window_candidate':'柜台／窗口服务界面；不得由此生成穿行边',
        'shared_wall_candidate':'仅表示共墙；不自动表示可通行',
        'conceptual_access_user_confirmed':'用户确认概念级人员可达；不要求具体门位，不生成虚构门点'},
    'multigraph_policy':'多个门可以对应同一空间对；保存每个证据点，图视图按空间对归并。',
    'aggregate_policy':'当前概念尺度允许整体交通核节点；不据此计算内部精确路径或距离，不以未拆分施工细节阻塞本轮。',
}

def graph_view(kind):
    grouped={}
    for r in relations:
        selected=(r.get('is_movement_candidate',False) if kind=='movement' else
                  r.get('is_service_candidate',False) if kind=='service' else
                  r['relation_type']=='shared_wall_candidate')
        if not selected:continue
        key=tuple(sorted([r['source'],r['target']]))
        if key not in grouped:
            grouped[key]={'source':key[0],'target':key[1],'label':None,'review_status':'pending',
                          'relation_ids':[],'portal_ids':[],'aggregate_endpoint_ids':[]}
        q=grouped[key];q['relation_ids'].append(r['id'])
        if r.get('label')==1:q['label']=1;q['review_status']='user_confirmed_at_concept_level'
        if r.get('evidence_marker'):q['portal_ids'].append(r['evidence_marker'])
        q['aggregate_endpoint_ids']=sorted(set(q['aggregate_endpoint_ids']+r.get('aggregate_endpoint_ids',[])))
    return list(grouped.values())

views={k:graph_view(k) for k in ['movement','service','shared_wall']}
incident=Counter()
for e in views['movement']:
    incident[e['source']]+=1;incident[e['target']]+=1
isolated=[{'id':n['id'],'name':n['name'],'node_level':n['node_level'],'scope':n['scope']}
          for n in nodes if not incident[n['id']] and n['node_level']!='landscape']
for n in public_nodes:n['movement_candidate_degree']=incident[n['id']]
audit={
    'status':'incomplete_visual_review_not_validation_of_full_reachability',
    'movement_unique_space_pairs':len(views['movement']),
    'service_unique_space_pairs':len(views['service']),
    'shared_wall_unique_space_pairs':len(views['shared_wall']),
    'spaces_without_movement_evidence':isolated,
    'aggregate_spaces_kept_at_concept_level':[n['id'] for n in nodes if n['node_level']=='core_block'],
    'pending_user_clarification_ids':[],
    'out_of_scope_not_blockers':['施工级小门位置及门宽','交通核内部精确距离','门扇及门禁构造'],
    'not_proven':['所有相关门和开口均已覆盖','患者／医护通行权限','门禁、方向和营业状态',
                  '交通核内部可达性','未标空间对的不存在关系','全图精确行走路径及距离'],
    'user_feedback_cases':[
        {'case':'箭头处大厅到取药区','space_ids':['S001','S013'],'resolution':'补无门开口，保留开口线段'},
        {'case':'挂号与取药的功能分界','space_ids':['S012','S013'],'resolution':'补区域连续，轴线不当墙'},
        {'case':'中部前室南北门','space_ids':['S002','S084','S020'],'resolution':'拆前室并分别记录两个门'},
        {'case':'病房取药及窗口','space_ids':['S017','S018','S002'],'resolution':'合并被轴线误分区域；记录两处药房门、一处大厅门和服务窗口'},
        {'case':'东侧公卫与急诊横向交通','space_ids':['S002','S086','S055','S088','S056','S078'],'resolution':'拆公卫前廊和两厕，补门及横向连续'}],
}
data={'metadata':metadata,'statistics':{
    'spaces':len(nodes),'by_level':dict(Counter(n['node_level'] for n in nodes)),
    'by_scope':dict(Counter(n['scope'] for n in nodes)),
    'by_name_status':dict(Counter(n['name_status'] for n in nodes)),
    'relation_candidates':len(relations),'portal_markers':len(door_markers),
    'by_relation_type':dict(Counter(r['relation_type'] for r in relations)),
    'movement_unique_space_pairs':len(views['movement']),'service_unique_space_pairs':len(views['service']),
    'entrance_markers':len(entrances),'user_confirmed_conceptual_access_pairs':sum(e['label']==1 for e in views['movement']),
    'user_confirmed_conceptual_relations':sum(r['label']==1 for r in relations),
},'spaces':public_nodes,'relation_candidates':relations,'portal_candidates':public_doors,'entrance_candidates':public_entries,
  'graph_views':views,'connectivity_audit':audit}
(OUT/'spatial_data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
(OUT/'connectivity_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')

labelme={'version':'5.5.0','flags':{'connectivity_review_v2':True,'training_ready':False},
         'shapes':[{'label':n['id']+'__'+n['name'],'points':n['polygon_px'],
                    'group_id':int(n['id'][1:]),'description':n['node_level']+'; '+n['name_status']+'; '+n['note'],
                    'shape_type':'polygon','flags':{'name_uncertain':n['name_status'] in ['partial','unresolved'],
                                                  'aggregated_block':n['node_level'] in ['core_block','functional_block'],
                                                  'review_pending':True},'mask':None} for n in nodes],
         'imagePath':'source.jpg','imageData':None,'imageHeight':H,'imageWidth':W}
(OUT/'annotations.labelme.json').write_text(json.dumps(labelme,ensure_ascii=False,indent=2)+'\n')

COLORS={'hall':'#2563eb','service':'#b45309','entrance':'#0f766e','vertical_core':'#64748b','pharmacy_counter':'#15803d','service_work_area':'#64748b','vestibule':'#0f766e',
        'registration':'#c2410c','pharmacy':'#15803d','office':'#7c3aed','unknown':'#d97706',
        'waiting':'#0369a1','corridor':'#0f766e','toilet':'#9333ea','consultation':'#2563eb',
        'triage':'#e11d48','landscape':'#65a30d','examination':'#0891b2','laboratory':'#0284c7',
        'resuscitation':'#dc2626','nurse_station':'#e11d48'}
scope_names={'public_service':'公共服务','inpatient_public_service':'出入院服务',
             'staff_or_public_unknown':'权限待核交通核','outpatient_support':'门诊支持','inpatient_support':'住院支持',
             'ordinary_outpatient':'普通门诊','fever_outpatient':'发热门诊',
             'south_clinic_scope_unknown':'南侧诊区待核','building_support':'建筑支持',
             'emergency':'急诊','nonclinical':'非临床'}
level_names={'room':'房间','open_space':'开放空间','semi_open_space':'半墙服务区','functional_block':'功能块（未细分）',
             'core_block':'交通核（未细分）','landscape':'绿化'}

base64_image=base64.b64encode(SOURCE.read_bytes()).decode()
parts=[f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{BASE_W}" height="1408" viewBox="0 0 {BASE_W} 1408">',
       '<rect width="1992" height="1408" fill="white"/>',
       '<style>text{font-family:Arial,"PingFang SC","Microsoft YaHei",sans-serif}.space .outline{stroke-width:1.8;fill-opacity:.08}.space.uncertain .outline{stroke-dasharray:6 3}.sid{font-size:8.5px;font-weight:700;fill:white;pointer-events:none}.space{cursor:pointer}.space:hover .outline,.space.selected .outline{stroke-width:4;fill-opacity:.3}.door{fill:#fff;stroke:#dc2626;stroke-width:1.6}.entrance{fill:#db2777;stroke:white;stroke-width:1.2}</style>',
       '<text x="42" y="40" font-size="25" font-weight="700" fill="#10243a">山东省立医院儿科综合楼 · 概念级连通标注 v3</text>',
       f'<text x="42" y="68" font-size="14" fill="#475569">{len(nodes)} 个空间／区域 · 已纳入用户对 01—08 的说明 · 半墙服务区记录可达，不指定小门位置</text>',
       '<text x="42" y="93" font-size="13" fill="#475569">绿虚线：半墙功能边界（非门位）　红圈：图面门洞候选　蓝／紫：开放连接　橙方块：服务窗口</text>',
       '<g id="plan" transform="translate(0 115)">',
       f'<image id="source-image" x="0" y="0" width="{BASE_W}" height="{BASE_H}" xlink:href="data:image/jpeg;base64,{base64_image}"/>',
       '<g id="space-layer">']
for n in nodes:
    poly=' '.join(f'{x},{y}' for x,y in n['_poly_base'])
    color=COLORS[n['category']]
    if n.get('boundary_type')=='half_height_wall':color='#059669'
    uncertain=n['name_status'] in ['partial','unresolved']
    lx,ly=n['_label_base']
    lx=min(lx,max(x for x,y in n['_poly_base'])-31)
    title=html.escape(f"{n['id']} | {n['name']} | {level_names[n['node_level']]} | {scope_names[n['scope']]} | {n['note']}")
    dash=' stroke-dasharray="6 3"' if uncertain or n.get('boundary_type')=='half_height_wall' else ''
    parts.append(f'<g class="space {"uncertain" if uncertain else ""}" id="{n["id"]}" data-scope="{n["scope"]}" data-level="{n["node_level"]}" data-uncertain="{str(uncertain).lower()}"><title>{title}</title><polygon class="outline" points="{poly}" fill="{color}" fill-opacity="0.08" stroke="{color}" stroke-width="1.8"{dash}/><g class="idlabel"><rect x="{lx}" y="{ly}" width="29" height="13" rx="3" fill="{color}" opacity=".95"/><text class="sid" x="{lx+3}" y="{ly+10}" font-size="8.5" font-weight="700" fill="white">{n["id"]}</text></g></g>')
parts.append('</g><g id="door-layer">')
for d in door_markers:
    x,y=d['_base']
    typ=d['marker_type'];c={'direct_door_candidate':'#dc2626','open_passage_candidate':'#0284c7','zone_continuity_candidate':'#7c3aed','service_window_candidate':'#d97706'}[typ]
    parts.append(f'<g class="marker" id="{d["id"]}" data-type="{typ}"><title>{d["id"]}: {" ↔ ".join(d["space_ids"])} | {typ} | {html.escape(d["note"])}</title>')
    if d['_segment_base']:
        a,b=d['_segment_base'];parts.append(f'<line x1="{a[0]}" y1="{a[1]}" x2="{b[0]}" y2="{b[1]}" stroke="{c}" stroke-width="3" stroke-dasharray="5 3"/>')
    if typ=='direct_door_candidate':
        parts.append(f'<circle cx="{x}" cy="{y}" r="3.5" fill="white" stroke="{c}" stroke-width="1.6"/>')
    elif typ=='service_window_candidate':
        parts.append(f'<rect x="{x-4}" y="{y-4}" width="8" height="8" fill="white" stroke="{c}" stroke-width="1.8"/>')
    else:
        parts.append(f'<path d="M{x},{y-5} L{x+5},{y} L{x},{y+5} L{x-5},{y} Z" fill="white" stroke="{c}" stroke-width="2"/>')
    parts.append('</g>')
parts.append('</g><g id="entrance-layer">')
for e in entrances:
    x,y=e['_base']
    parts.append(f'<g><title>{e["id"]} {html.escape(e["name"])}</title><path class="entrance" d="M{x-6},{y-6} L{x+6},{y-6} L{x+6},{y+6} L{x-6},{y+6} Z" fill="#db2777" stroke="white" stroke-width="1.2"/><text x="{x+9}" y="{y+4}" font-size="11" font-weight="700" fill="#be185d">{e["id"]}</text></g>')
parts.append('</g></g><text x="42" y="1391" font-size="12" fill="#475569">概念精度：空间组织与可达性｜不要求施工级门位、门宽和内部距离｜用户确认的可达关系单独记录来源｜2026-10-25</text></svg>')
svg=''.join(parts)
(OUT/'标注预览.svg').write_text(svg)
ET.fromstring(svg)
doc=pymupdf.open(stream=svg.encode(),filetype='svg')
doc[0].get_pixmap(matrix=pymupdf.Matrix(1.55,1.55),alpha=False).save(OUT/'标注预览.png')

# Standalone review page; all data and the reference image are embedded.
summary=data['statistics']
review_template='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>一层空间标注复核</title><style>
*{box-sizing:border-box}body{margin:0;font-family:system-ui,-apple-system,"PingFang SC",sans-serif;color:#16283c;background:#f2f5f8}header{padding:20px 24px;background:white;border-bottom:1px solid #dce3eb}h1{font-size:22px;margin:0 0 9px}p{margin:7px 0;line-height:1.6}.meta{color:#586b7e;font-size:13px}.toolbar{display:flex;flex-wrap:wrap;align-items:center;gap:12px;margin-top:13px}select,input,button{font:inherit;padding:7px 9px;border:1px solid #cbd5e1;border-radius:7px;background:white}button{cursor:pointer}main{display:grid;grid-template-columns:minmax(0,1fr) 360px;gap:14px;padding:14px}.canvas{background:white;border:1px solid #dce3eb;border-radius:10px;overflow:auto;height:calc(100vh - 185px)}.canvas svg{display:block;max-width:none;width:1600px;height:auto}.side{display:flex;flex-direction:column;gap:12px}.panel{background:white;padding:15px;border:1px solid #dce3eb;border-radius:10px}#detail{font-size:13px;line-height:1.7}#list{height:calc(100vh - 490px);min-height:180px;overflow:auto}.row{border-top:1px solid #edf0f4;padding:8px 2px;cursor:pointer;font-size:13px}.row:hover,.row.active{background:#eff6ff}small{display:block;color:#60758a}label{font-size:13px}code{word-break:break-all}.badge{display:inline-block;background:#fff4de;color:#855d12;padding:2px 7px;border-radius:5px;font-size:12px}@media(max-width:1000px){main{grid-template-columns:1fr}.canvas{height:65vh}#list{height:300px}}
</style><header><h1>一层空间标注 · 可交互复核</h1><p>__COUNT__ 个空间／区域，__REL__ 条关系候选，__DOORS__ 个门／连接点，__ENTRY__ 处入口。<span class="badge">首轮草稿，尚未验收为训练真值</span></p><p class="meta">点空间编号或右侧清单查看详情。概略轮廓尚未精修；虚线名称待核，实线也不等于用户已验收。交通核和功能块与房间分级保存。</p><div class="toolbar"><input id="search" placeholder="搜索编号、名称、候选名"><select id="scope"><option value="">全部功能范围</option></select><select id="level"><option value="">全部空间层级</option></select><label><input id="uncertain" type="checkbox">仅看名称待核</label><label><input id="labels" type="checkbox" checked>编号</label><label><input id="doors" type="checkbox" checked>连接候选</label><label><input id="overlay" type="checkbox" checked>轮廓</label><label>缩放 <input id="zoom" type="range" min="60" max="240" value="100"></label><button id="reset">重置</button><a href="spatial_data.json" download>结构化数据</a> · <a href="annotations.labelme.json" download>LabelMe JSON</a></div></header><main><div class="canvas" id="canvas">__SVG__</div><aside class="side"><div class="panel" id="detail">选择一个空间查看功能、层级、轮廓、候选名称和连接证据。<p><b>面积说明：</b>正式 area_m2 为 null；估算面积仅供检查，不可作为实测值。</p><p><b>关系说明：</b>所有关系尚待复核；未列出的空间对保持未知，不能当作不连接。</p></div><div class="panel"><b id="list-count"></b><div id="list"></div></div></aside></main><script>
const DATA=__DATA__, SCOPES=__SCOPES__, LEVELS=__LEVELS__;
const $=s=>document.querySelector(s), esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
Object.entries(SCOPES).forEach(([k,v])=>$('#scope').add(new Option(v,k)));Object.entries(LEVELS).forEach(([k,v])=>$('#level').add(new Option(v,k)));
function filtered(){const q=$('#search').value.trim().toLowerCase();return DATA.spaces.filter(n=>(!$('#scope').value||n.scope===$('#scope').value)&&(!$('#level').value||n.node_level===$('#level').value)&&(!$('#uncertain').checked||['partial','unresolved'].includes(n.name_status))&&(!q||[n.id,n.name,n.candidate_name,n.note].join(' ').toLowerCase().includes(q)));}
function render(){const ns=filtered(), ids=new Set(ns.map(n=>n.id));DATA.spaces.forEach(n=>$('#'+n.id).style.display=ids.has(n.id)?'':'none');$('#list-count').textContent=`当前显示 ${ns.length} / ${DATA.spaces.length}`;$('#list').innerHTML=ns.map(n=>`<div class="row" data-id="${n.id}"><b>${n.id}</b> ${esc(n.name)}<small>${esc(SCOPES[n.scope])} · ${esc(LEVELS[n.node_level])}${['partial','unresolved'].includes(n.name_status)?' · 名称待核':''}</small></div>`).join('');document.querySelectorAll('.row').forEach(el=>el.onclick=()=>select(el.dataset.id,true));}
function select(id,scroll){document.querySelectorAll('.space.selected').forEach(e=>e.classList.remove('selected'));const el=$('#'+id),n=DATA.spaces.find(n=>n.id===id);el.classList.add('selected');document.querySelectorAll('.row').forEach(e=>e.classList.toggle('active',e.dataset.id===id));const rel=DATA.relation_candidates.filter(r=>r.source===id||r.target===id);$('#detail').innerHTML=`<h3>${n.id} ${esc(n.name)}</h3><b>范围：</b>${esc(SCOPES[n.scope])}<br><b>层级：</b>${esc(LEVELS[n.node_level])}<br><b>名称状态：</b>${esc(n.name_status)}<br><b>候选名：</b>${esc(n.candidate_name||'—')}<br><b>几何：</b>原图坐标多边形，${n.polygon_px.length} 顶点<br><b>像素面积：</b>${n.area_px2}<br><b>估算面积：</b>${n.area_m2_estimate_from_provisional_axis_scale} m²（待校准，含墙线近似）<br><b>正式面积：</b>null<br><b>说明：</b>${esc(n.note||'首轮视觉标注，待复核。')}<p><b>关联候选 ${rel.length} 条：</b></p>${rel.map(r=>`<div>${r.id} ${r.source} ↔ ${r.target}<small>${esc(r.relation_type)}；待核，权限未知</small></div>`).join('')||'尚未标注，不能据此认定无连接。'}`;if(scroll)el.scrollIntoView({block:'center',inline:'center',behavior:'smooth'});}
document.querySelectorAll('.space').forEach(el=>el.onclick=()=>select(el.id,false));['search','scope','level','uncertain'].forEach(id=>$('#'+id).addEventListener('input',render));$('#labels').onchange=()=>document.querySelectorAll('.idlabel').forEach(e=>e.style.display=$('#labels').checked?'':'none');$('#doors').onchange=()=>$('#door-layer').style.display=$('#doors').checked?'':'none';$('#overlay').onchange=()=>$('#space-layer').style.visibility=$('#overlay').checked?'visible':'hidden';$('#zoom').oninput=()=>$('.canvas svg').style.width=(1600*$('#zoom').value/100)+'px';$('#reset').onclick=()=>{['search','scope','level'].forEach(id=>$('#'+id).value='');$('#uncertain').checked=false;$('#zoom').value=100;$('.canvas svg').style.width='1600px';render();};render();
</script></html>'''
review=review_template.replace('__COUNT__',str(len(nodes))).replace('__REL__',str(len(relations))).replace('__DOORS__',str(len(door_markers))).replace('__ENTRY__',str(len(entrances))).replace('__SVG__',svg).replace('__DATA__',json.dumps(data,ensure_ascii=False).replace('</','<\\/')).replace('__SCOPES__',json.dumps(scope_names,ensure_ascii=False)).replace('__LEVELS__',json.dumps(level_names,ensure_ascii=False))
review=review.replace('一层空间标注 · 可交互复核','连通性复核 v2 · 门洞、开口与窗口')
review=review.replace('个门／连接点','个门／开口／窗口证据点').replace('首轮草稿，尚未验收为训练真值','补查草稿，全图连通性尚未验收')
review=review.replace('点空间编号或右侧清单查看详情。','点空间编号、连接符号或右侧清单查看详情。红圈为门；蓝菱形为无门开口；紫菱形为区域连续；橙方块为服务窗口。')
review=review.replace('<label><input id="doors"', '<select id="portal-type"><option value="">全部连接符号</option><option value="direct_door_candidate">门洞</option><option value="open_passage_candidate">无门开口</option><option value="zone_continuity_candidate">区域连续</option><option value="service_window_candidate">服务窗口（不穿行）</option></select><label><input id="no-movement" type="checkbox">未记录通行证据</label><label><input id="doors"')
review=review.replace('(!q||[n.id,n.name,n.candidate_name,n.note]', '(!$(\'#no-movement\').checked||n.movement_candidate_degree===0)&&(!q||[n.id,n.name,n.candidate_name,n.note]')
review=review.replace("['search','scope','level','uncertain'].forEach", "['search','scope','level','uncertain','no-movement'].forEach")
review=review.replace("$('#uncertain').checked=false;", "$('#uncertain').checked=false;$('#no-movement').checked=false;$('#portal-type').value='';document.querySelectorAll('.marker').forEach(e=>e.style.display='');")
review=review.replace('${esc(r.relation_type)}；待核，权限未知',"${esc(TYPES[r.relation_type]||r.relation_type)}；${r.is_movement_candidate?'通行候选，权限待核':'非通行关系'}")
review=review.replace('连通性复核 v2 · 门洞、开口与窗口','概念级连通标注 v3 · 已纳入用户说明')
review=review.replace('条关系候选','条关系记录').replace('补查草稿，全图连通性尚未验收','概念级精度，小门位置不作必要条件')
review=review.replace('交通核和功能块与房间分级保存。','交通核可整体保留；半墙服务区记录概念级可达，小门位置无需指定。')
review=review.replace('所有关系尚待复核；未列出的空间对保持未知，不能当作不连接。','用户确认的概念级可达关系标为 1；其余图面候选保留待核。未列出的关系仍未知。')
review=review.replace("r.is_movement_candidate?'通行候选，权限待核':'非通行关系'","r.label===1?'概念可达已确认，权限未定':r.is_movement_candidate?'图面通行候选':'非通行关系'")
extra_js='''
const TYPES={direct_door_candidate:'门洞',open_passage_candidate:'无门开口',zone_continuity_candidate:'区域连续',service_window_candidate:'服务窗口（不穿行）',shared_wall_candidate:'共墙（不自动通行）',conceptual_access_user_confirmed:'用户确认的概念级可达'};
document.querySelectorAll('.marker').forEach(el=>el.onclick=()=>{const p=DATA.portal_candidates.find(p=>p.id===el.id);const r=DATA.relation_candidates.find(r=>r.evidence_marker===p.id);$('#detail').innerHTML=`<h3>${p.id} ${esc(TYPES[p.marker_type])}</h3><b>两端：</b>${p.space_ids.map(id=>{const n=DATA.spaces.find(n=>n.id===id);return esc(id+' '+n.name)}).join(' ↔ ')}<p><b>人员通行：</b>${p.is_movement_candidate?'候选通路，权限与方向未知':'服务界面，不创建人员穿行边'}</p><b>证据说明：</b>${esc(p.note)}<p><b>空间层级：</b>${p.aggregate_endpoint_ids.length?'包含交通核聚合节点，内部仍需细分':'端点已独立标出，仍需复核'}</p><b>关系记录：</b>${r.id}<br><b>训练标签：</b>null，尚待验收`;});
$('#portal-type').onchange=()=>document.querySelectorAll('.marker').forEach(el=>el.style.display=!$('#portal-type').value||el.dataset.type===$('#portal-type').value?'':'none');
'''
review=review.replace('</script>',extra_js+'</script>')
review=review.replace('包含交通核聚合节点，内部仍需细分','交通核按概念整体节点记录，内部精确路径不在本轮范围')
(OUT/'打开复核.html').write_text(review)

name_counts=Counter(n['name_status'] for n in nodes)
readme=f'''# 山东省立医院儿科综合楼一层：首轮空间标注

日期：2026-10-25。依据工作目录中的高清 JPG 进行辅助标注，不改动原图。

这是可继续校订的标注试样，不是已经验收的训练数据或精确 CAD 测绘成果。

## 文件

- `打开复核.html`：离线交互复核，支持编号／名称搜索、范围与层级筛选、缩放及点选空间。无需联网。
- `标注预览.png` / `标注预览.svg`：全图概览，SVG 自带原图、可缩放。
- `spatial_data.json`：空间、候选关系、门／连接点、入口及出处、几何、校准状态。
- `annotations.labelme.json`：LabelMe 格式多边形，配合同目录 `source.jpg` 打开；未在 LabelMe 应用内验收。
- `source.jpg`：原始图片的字节相同副本。

## 本次实际完成

- {len(nodes)} 个空间／区域多边形；其中 {dict(Counter(n['node_level'] for n in nodes))}。
- 名称判读状态：{dict(name_counts)}。`descriptive` 是按位置或形态给出的描述名，不代表读出了原图标签。
- {len(relations)} 条关系候选，其中 {len(door_markers)} 条附门洞／通道连接点、其余为选定共墙候选；{len(entrances)} 个入口候选。
- 同类诊室分别编号，共 {sum(n['category']=='consultation' for n in nodes)} 个。
- 所有坐标均对应原始 {W} × {H} 图像；不对应聊天中缩小后的图片。

## 如何理解标注

1. 轮廓为依据墙线或区域边缘放置的概略多边形；弧线用折线近似，门洞处连续补线。它们尚未逐像素贴合内净边界，不可称为精确房间分割。
2. 实线是可读名称或描述编号，虚线是部分可读／未辨认名称；所有项目均尚待用户或第二次复核，实线不代表已完成验收。
3. `room`、`open_space`、`functional_block`、`core_block` 和 `landscape` 分级保存。功能块和交通核内部尚未全拆，不能全部当成房间节点。
4. 普通门诊、发热门诊、急诊、出入院服务与建筑支持分别记录；文件名表明它来自儿科综合楼，不能不加说明地当作普通成人门诊。
5. 候选关系的 `label` 全为 null，`candidate_label=1` 只表示待核的存在关系。未列出的空间对为未知，不是 0。共墙、开门和开放连接分别保存；未确认患者／医护权限及方向。
6. 面积估算使用可见总轴线跨度 84.9 m × 56.4 m，尚未完成独立校准、扫描变形与净面积复核，因此 `area_m2` 留空，估算值仅供检查。
7. 图纸真实质心、真实邻接和门洞可作标注或评价；若新设计中不可获得，不能直接拿作关系预测输入。
8. 本次未完整覆盖柜台、排队带、交通核内部、全部小附属间、所有门洞与所有共墙关系。左侧停车位未标作房间。
9. 关键名称经局部放大复核：S016 为“门诊药房”，S017 为“病房药房”；不能按内部长条图案把药架误作候诊座椅。

## 文件检查范围

已检查 JSON 与 SVG 可解析、原图副本哈希、空间编号一致、坐标范围、多边形有效性、相互重叠与所标连接点的位置，并查看 PNG 渲染。HTML 完成脚本语法检查；当前电脑控制工具未提供可用浏览器，因此未在浏览器 UI 内实测交互。LabelMe JSON 未在 LabelMe 应用内打开验证。

## 未解决与后续

优先复核 `name_status=unresolved/partial` 的名称、南侧诊区归属、服务窗口与门洞差别、聚合块的拆分以及各关系证据。原图来源、医院／楼栋／楼层身份和年份还应对照原始出版物核实。

可先用普通门诊局部验证数据流程，再选择任务范围。未确定类别体系、独立项目数量、数据切分和推断输入前，不将这版直接投喂 GCN 并报告性能。

## 原图溯源

原路径：`{SOURCE}`。

SHA-256：`{sha}`。

标注方法：助手直接查看原图与局部放大后放置坐标，OCR 只作辅助且误识别较多，未将 OCR 输出自动当成真值。未训练模型、未调用 Rhino。
'''
(OUT/'标注说明.md').write_text(readme)
counts=Counter(r['relation_type'] for r in relations)
readme_v2=f'''# 山东省立医院儿科综合楼一层：连通性复核 v2

日期：2026-10-25。保留 v1 原文件，另存本版。原始 JPG 未修改。

本版回应用户指出的开放连接、漏标门洞及区域级打通问题。它仍是视觉复核草稿，不声称完成全部连通性或训练标签验收。

## 查看文件

- `打开复核.html`：点空间编号或连接符号查看说明，可筛选门洞、无门开口、区域连续、服务窗口，也可查未记录通行证据的空间。
- `标注预览.png` / `标注预览.svg`：全图静态预览。
- `spatial_data.json`：空间多边形、连接证据、分类型关系、候选图视图与审核状态。
- `connectivity_audit.json`：仍缺少通行证据的节点、待拆交通核和未证明事项。
- `annotations.labelme.json` 与 `source.jpg`：可继续编辑的空间多边形及字节相同原图副本。编辑后需另行同步其他导出文件；当前复核页只读。

## 本次修改

1. 大厅 S001 与取药服务区 S013 之间补记无门开口，并保存其线段；挂号 S012 与取药 S013 的轴线分界记录为区域连续，避免人为切断通路。
2. S013 分成公共取药区 S013 与南侧柜台工作带 S083；补挂号工作带 S082。窗口和门分别保存，窗口不作为人员穿行边。
3. 合并被轴线误分的病房取药区 S018/S019，保留 S018，停用 S019。补药房与取药区上下端的两处门、取药区至大厅的门及服务窗口。
4. 拆出中部前室 S084，分别标出与大厅、交通核的门；补急诊北侧公用前室 S085，修正原内廊跨门合并问题。
5. 将公卫组拆为西厕 S055、东厕 S088、前廊 S086 与附属间 S087，补相关门；补 S056 与急诊大厅 S078 的无隔断连续交通。
6. 补南侧诊室医务廊侧门、卫生间门、前厅门和右侧辅助用房门。修正急诊内廊 S061 至过渡带 S076：放大可见双扇门，原开放连接改为门洞候选。
7. 西侧医务廊 S027 补西端支路，缩小 S036 卫生间轮廓；抢救室 S077 补北侧床位带，不按穿过区域的轴线切割。

## 当前统计

- 空间／区域：{len(nodes)}。层级：{dict(Counter(n['node_level'] for n in nodes))}。
- 关系候选：{len(relations)}。分类：{dict(counts)}。
- 图形证据点：{len(door_markers)}；外门／入口候选：{len(entrances)}。
- 按空间对归并后的人员通行候选边：{len(views['movement'])}；服务联系：{len(views['service'])}；共墙：{len(views['shared_wall'])}。
- 未记录人员通行证据的非绿化空间：{len(isolated)}，详见审计 JSON。这是缺标提示，不证明空间真的隔绝。

## 关系定义

| 类型 | 表达内容 | 可否直接用于人员通行图 |
| --- | --- | --- |
| direct_door_candidate | 可见门洞／门扇开启符号 | 可作候选，权限、方向待核 |
| open_passage_candidate | 可见无门开口 | 可作候选，权限待核 |
| zone_continuity_candidate | 功能区之间未见实体隔断 | 可作候选；这是分区联系，不是门 |
| service_window_candidate | 挂号／取药等柜台服务界面 | 不可据此穿行 |
| shared_wall_candidate | 共墙 | 不自动通行 |

一个空间对可以有两个门、也可以同时有窗口和门。`portal_candidates` 保存每处证据，`graph_views` 按空间对归并。不要把证据点数当成唯一图边数。

所有关系 `label` 仍为 null，`candidate_label=1` 仅为待核存在关系。未列出的空间对仍未知，不记成 0；不把整张图的所有可能空间对自动当负样本。

## 尚未解决

- 原图局部模糊或聚合交通核内部仍需拆分；进入聚合区域的门不证明内部任意房间互通。
- 患者／医护／工作人员的权限、门禁、门的方向性、营业状态不能仅凭此图全部确定。
- 真实路径、距离、通路净宽和完整出入口网络尚未验收；本版不能据此报告完整流线仿真结果。
- 多边形仍为概略墙线／区域轮廓；正式 `area_m2` 保持 null，仅保留按总轴线跨度计算的检查用估算值。
- 来源、医院／楼栋／楼层与年份尚应对照原始出处核实；现有文件名表明为儿科综合楼。

## 检查范围

检查 JSON/SVG 解析、原图副本哈希、空间编号及坐标、多边形有效性与重叠、连接证据点与边界的距离、关系端点和图视图去重。检查静态 PNG 和重点局部。HTML 做脚本语法检查；当前无可用浏览器连接，未声称完成浏览器 UI 实测。LabelMe 格式未在该应用内验收。

SHA-256：`{sha}`。
'''
(OUT/'标注说明.md').write_text(readme_v2)
readme_v3=f'''# 概念级连通标注 v3

本版按用户反馈，将目标精度限定为门诊概念平面的空间组织与可达关系。

## 已纳入的确认

- 01 导医台、04 急诊挂号收费、05 护士站：半墙服务区，与相邻外部公共空间概念级可达。小门／矮门位置可以后续确定，本轮不要求，也不伪造坐标。
- 02 北侧扶梯从左侧门诊大厅进入。
- 03 西南电梯朝 B（西侧前厅）开门。
- 06 西侧交通核按用户箭头记录横向、纵向区域贯通；不据此画穿越梯井的直线路径。
- 07 中央区域按用户说明记为电梯厅，向两侧进入电梯；撤回此前扶梯解读。整体交通核在本轮可以保留。
- 08 急诊南侧交通核从上方前厅方向进入。

本批 01—08 已无待追问的施工级门位问题。

## 数据精度原则

1. 主要记录空间功能、区域范围和概念级可达性。半墙的功能边界不等于完整隔墙，也不要求指定小门几何。
2. 用户明确确认的可达关系为 `conceptual_access_user_confirmed`，`label=1`，无 `evidence_marker` 和虚构门坐标，并记录问题序号及来源。
3. 图上可见的门、开口、共墙和窗口继续作为图面证据保存。未逐项核验的候选仍 `label=null`。确认区域可达不等于确认每个门位、门宽、单向权限或候选标记都正确。
4. 施工门位、门宽、门扇和交通核内部精确距离不作为本轮数据准备的必要条件。
5. 取药／挂号的服务窗口和人员进入服务区的小门是不同关系。用户确认服务区可达后可保留人员边；不能仅由柜台窗口本身推出通路。
6. 交通核可作为整体节点参与概念级拓扑建模，不声称得到精确内部行走路径。
7. 正式面积仍为 null；检查用面积估算、原图质心等不自动作为新设计时的模型输入。

## 文件与统计

`打开复核.html` 为只读页面；`标注预览.png/svg` 为预览；`spatial_data.json` 包含空间与关系；`annotations.labelme.json` 配合 `source.jpg` 保存区域轮廓；`connectivity_audit.json` 保存图数据检查范围。

- 空间／区域：{len(nodes)}；层级：{dict(Counter(n['node_level'] for n in nodes))}。
- 关系记录：{len(relations)}；用户确认的概念级可达空间对：{sum(e['label']==1 for e in views['movement'])}。
- 当前没有任何通行记录的非绿化节点：{len(isolated)}。这只表示没有零度节点，不证明已标全所有连接。
- 本批用户待回答项：0。

保留全部历史版本。原图未改动。仍需统一建模类别、确定预测任务、数据分组与验证方式；本版不以少量澄清就声称模型训练条件全部就绪。

图纸出处、房间名称及其余图面候选关系的可靠性仍应在数据验收中核查；这些与不要求施工门位是不同层面。
'''
(OUT/'标注说明.md').write_text(readme_v3)
clarify=ROOT/'p-写作过程/标注试样/连通性待确认_编号截图/用户确认记录_01-08.json'
shutil.copyfile(clarify,OUT/'用户确认记录_01-08.json')
print(json.dumps({'output_directory':str(OUT),'statistics':summary,'files':[p.name for p in OUT.iterdir()]},ensure_ascii=False,indent=2))
