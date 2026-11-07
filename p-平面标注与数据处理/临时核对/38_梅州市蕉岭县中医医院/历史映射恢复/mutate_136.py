p='/Users/hushili/Documents/研究-论文写作/大论文/p-平面标注与数据处理/临时核对/38_梅州市蕉岭县中医医院/历史映射恢复/build_annotation.py'
s=open(p).read()
s=s.replace("Polygon([(165,702),(221,702),(221,710),(268,710),(268,780),(165,780)])","(221,710,268,780)")
s=s.replace("'门诊大厅北侧交通核'","'门诊大厅上侧电梯组'")
s=s.replace("(165,676,221,702)","(165,676,221,744)")
s=s.replace("room('pharmacy_west_1'", """# 完整放大图可辨认两个电梯旁的小房间；具体用途未标注。
for k,b in [('hall_core_side_1',(165,744,195,780)),('hall_core_side_2',(195,744,221,780))]:
 room(k,b,'public_service',0,'无可靠候选','电梯旁独立房间，图上无功能文字')
vest=next(i for i in items if i['key']=='hall_north_2')
vest.update(name='卫生间前厅',type='vestibule',level='open_space',candidate='',basis='')
room('pharmacy_west_1'""")
s=s.replace("for n,it in enumerate(ordered,1):it['id']=f'S{n:03d}'", """old_path=TMP/'work_spaces.json'
old=json.loads(old_path.read_text()) if old_path.exists() else []
old_ids={i['key']:i['id'] for i in old}
next_id=max([int(i[1:]) for i in old_ids.values()]+[0])+1
for it in ordered:
 if it['key'] in old_ids:it['id']=old_ids[it['key']]
 else:it['id']=f'S{next_id:03d}';next_id+=1
""")
# 复核后不可确认的跨片区连通删去，省略不代表不连通。
s=s.replace("('fe_passage','hall'),","")
open(p,'w').write(s)