from pathlib import Path
from collections import Counter
import json,re,hashlib
R=Path(__file__).resolve().parent
P=R.parent.parent/'标注试样/15_盐城市妇幼保健院'
B=Path((R/'本轮备份路径.txt').read_text().strip())
M=json.loads((R.parent/'15_盐城市妇幼保健院_名称核对_20261101/核对号映射.json').read_text())
O=json.loads((R/'照片识读记录.json').read_text())
old=json.loads((B/'annotation.json').read_text());data=json.loads((P/'annotation.json').read_text())
assert old==data,'JSON已被其他操作修改，需重新核对'
md=(P/'标注说明.md').read_text()
assert md==(B/'标注说明.md').read_text(),'MD已被其他操作修改，需保留新增填写后再同步'
S={s['id']:s for s in data['spaces']}
for item in O.values():
    s=S[item['id']]
    assert s['type']=='unknown' and s['name']=='名称未确认'
    s.update(name=item['name'],type=item['type'])
# The central unlabelled courtyard keeps its pending name. Its area is excluded
# under the user's explicit blanket rule; no new access relation is invented.
S['S274']['type']='courtyard'
S['S274'].pop('area_ratio',None)
def area(points):return abs(sum(points[i][0]*points[(i+1)%len(points)][1]-points[(i+1)%len(points)][0]*points[i][1] for i in range(len(points)))/2)
indoor=[s for s in data['spaces'] if s['type'] not in {'landscape','courtyard'}]
total=sum(area(s['polygon_px']) for s in indoor)
for s in indoor:s['area_ratio']=round(area(s['polygon_px'])/total,8)
remaining=[r for r in M if str(int(r['number'])) not in O]
assert len(remaining)==39
uncertain={
 1:('休息区','等候区','可见成组桌椅，但没有可辨房名，不能区分会客、休息或等候。'),
 2:('休息区','等候区','同片区另一个桌椅区域，未见可辨文字；不能以家具确定原名。'),
 7:('等候区','休息区','座席可辨，但无明确名称；请补原名，或明确接受该功能名。'),
 8:('等候区','休息区','座席区域可定位；具体名称未标清，不从相邻空间套名。'),
 9:('会议室','示教室','有会议桌椅，未见房名文字；不能仅凭桌椅区分会议与示教。'),
 11:('暂无可靠候选','—','照片01中两字房名仍模糊，需要该房名近照或直接填写。'),
 12:('储物室','储藏室','照片01可见三字轮廓，字形不足以可靠区分候选；请核对原字。'),
 14:('值班更衣','更衣室','下排“更衣”较清楚，前缀仍模糊；需要完整房名。'),
 15:('值班更衣','更衣室','下排“更衣”较清楚，上排字迹不稳；不补造男女属性。'),
 45:('会议室','示教室','可见会议桌椅，没有可辨房名文字；需原名或接受功能名。'),
 49:('值班更衣','更衣室','“更衣”可辨，前缀仍不清；需要完整房名。'),
 50:('值班更衣','更衣室','“更衣”可辨，前缀仍不清；不凭对称关系套用49。'),
 52:('储物室','储藏室','三字房名仍有模糊字；候选依据仅为字形，不视为已确认。'),
 53:('暂无可靠候选','—','照片03房名笔画粘连，当前不能可靠辨认。'),
 108:('医技候诊区','候诊区','座席及邻近护士站可辨，但本区具体名称不清；可确认较粗功能名。'),
 123:('暂无可靠候选','—','照片06中本小间未见清楚文字，不能凭对称关系套用机房。'),
 139:('医技候诊区','候诊区','黄色“医技”是片区题注；座席区的具体原名未标清。'),
 153:('工作区','服务区','可见邻近工作台，无法确认本条形区域具体岗位或用途。'),
 172:('妇科检查','检查室','部分字形似“妇科检查”，整名仍不够稳定；需局部近照核实。'),
 173:('门诊候诊区','候诊区','“标准门诊单元”是片区标题；座席区原名未单列，可确认较粗功能名。'),
 199:('采血处理','采样处理','首段字形仍不稳，两候选仅有共同字形依据，不扩写为确定检验项目。'),
 200:('暂无可靠候选','—','小房间文字笔画粘连，不能确定整名；需原字近照或直接填写。'),
 227:('门诊候诊区','候诊区','片区题注及座席可辨，但题注不等于本区独立名称。'),
 251:('阅览','电教','照片09中两字标题仍小；须核对本块原字，不套用253的名称。'),
 252:('中庭','挑空区','围合空白区可定位；依用户统一口径已排除室内面积，具体名称仍待定，不再追问是否计面积。'),
 253:('电教','阅览','照片09中两字标题仍不稳；需该块原字近照或直接填写。'),
 254:('休息区','等候区','桌椅可辨，未见名称文字；不能据此决定具体用途。'),
 255:('休息区','等候区','另一处桌椅区域未见房名；与254分别保留编号。'),
 267:('门诊候诊区','候诊区','座席与门诊片区题注可辨；可直接确认较粗功能名，无需逐张重拍座椅。'),
 295:('舞台','讲台区','“大会议厅”为整体标题，已用于厅体294；此前区条带的具体用途仍待核，不重复当作另一间会议厅。'),
 319:('办公','—','可见桌椅与沙发，无独立房名，不补造主任或领导等具体身份。'),
 320:('暂无可靠候选','—','狭长小间未见可辨房名，不能从邻接办公室推定用途。'),
 321:('办公','—','可见办公家具但未见文字；没有证据补写具体岗位。'),
 322:('暂无可靠候选','—','狭长小间无清楚文字，不能从对称位置套名。'),
 327:('消防','设备间','文字似“消防”，现有字形仍不足以确认；需要原名近照。'),
 329:('公共大厅','—','会议区前的公共空间未见独立名称；需原名或接受大厅这一功能名。'),
 330:('服务台','茶歇服务区','只有台面及家具线索，没有可辨文字；不能确定服务内容。'),
 331:('办公','工作间','可见桌椅，未见房名文字；候选共用家具依据，无法区分。'),
 332:('办公','工作间','同片区另一间，未见文字；不能借用331的用途判断。')}
assert set(uncertain)=={int(r['number']) for r in remaining}
# Preserve every review number, S id, and all existing answer cells, changing
# only cells with no prior room-name answer (S274 has the user's area rule).
lines=[]
for line in md.splitlines():
    cells=[v.strip() for v in line.strip().strip('|').split('|')]
    if len(cells)==7 and re.fullmatch(r'S\d+',cells[1]):
        n=int(cells[0]);item=O.get(str(n))
        if item:
            assert cells[5]=='待确认',(n,cells[5])
            photos='、'.join(f'{ph:02}' for ph in item['photo'])
            cells[2]=item['name'];cells[3]='—'
            cells[4]=f'补充照片{photos}逐项识读。{item["evidence"]}把握：高。'
            cells[5]='照片识读已同步；非用户填写'
        else:
            candidate,alternative,reason=uncertain[n]
            cells[2]=candidate;cells[3]=alternative;cells[4]=reason+'把握：'+('中' if n in {14,15,49,50,172,199,327} else '低')+'。'
            if n==252:cells[5]='面积排除已按用户口径落实；仅名称待确认'
            else:assert cells[5]=='待确认',(n,cells[5])
        line='| '+' | '.join(cells)+' |'
    lines.append(line)
md='\n'.join(lines)+'\n'
md=md.replace('未完成：336 个空间名称尚未确认。','未完成：39 个空间名称尚未确认；本轮已依据补充照片同步297项名称。',1)
start=md.index('## 补充照片后，还需要哪些信息（2026-11-03）')
end=md.index('## 名称核对填写表',start)
summary='''## 补充照片识读结果与剩余信息（2026-11-03）

**本轮已依据11张照片同步297项名称，原336项名称核对中剩39项；全图仍有426个空间／区域，S编号、核对号及轮廓均未重排。** 已同步行标为“照片识读已同步”，表示助手依据图面判读，不冒称用户逐项确认。图上只写“医办”“设备”“HIV”等时保留原写法；病房依据床位图注及“45床标准护理单元”题注识别，模糊床数不补写。

**面积口径已落实：**所有挑空、上空及露天区域不计室内面积。11处既有绿化继续排除；S274（原核对252）按本轮针对该围合空白区的面积确认，归入不计室内面积的中庭类，具体名称仍未确认，不据此判定能否步入或创建可达关系。已移除S274的占比并对其余室内区域重新归一化，不再逐项追问这类区域是否计面积。

### 现在还需要哪些信息

**资料01｜图纸楼层。**仍缺能读清“项目名称＋楼层／平面图名称”的图题，或图纸明确标注的楼层文字。照片中的“门诊大厅上空”不能单独证明是第几层；本图暂不认定为首层。

**我的确认／备注：**待填写（填写实际图题或楼层即可）

**资料02｜剩余39项的具体名称。**下表按既有片区汇总；具体S编号、候选依据及可填写确认栏仍在下方原名称表中，旁边已换成对应补充照片的定位图。可以直接按原核对号在聊天中答复，或修改原表；不需要再次填写已同步的297项。无文字的桌椅区、候诊区等，可明确接受表中较粗功能名，无需补施工细节。S274仅需补名称，不再确认面积。

| 片区 | 剩余核对号（沿用原号） | 数量 |
| --- | --- | --- |
'''
for group in range(14):
    items=[r for r in remaining if r['group']==group]
    if items:
        old_heading=re.search(rf'^### {group+1:02} (.+?)（',md,re.M).group(1)
        summary+=f'| {group+1:02} {old_heading} | '+ '、'.join(r['number'] for r in items)+f' | {len(items)} |\n'
summary+='''
**不用整批重拍。**只对下方表中仍有模糊字的项，补拍能读清原字的局部，保留相邻门口或走廊方便定位；其余无文字的区域直接说明实际用途或接受候选功能名即可。蓝区的123、办公区的320／322等小间无法从照片确定用途，暂留unknown，不用“辅助用房”代替实际名称。

**结构与关系状态：**本轮补齐名称并落实面积口径；未新增门洞红点，也未把名称同步当作主要连通关系已全部复核。局部柜台、窄小间和交通核的内部精确路线不在本轮逐项追问。

[剩余39项定位总图](../../临时核对/15_盐城市妇幼保健院_照片同步_20261103/剩余39项定位总图.png) · [补充照片目录](../../临时核对/15_盐城市妇幼保健院_照片同步_20261103/用户补充照片/)

'''
md=md[:start]+summary+md[end:]
md=md.replace('**本次清单：336 项未确认名称，其中房间 308 项、功能块 12 项、开放区域 11 项、半开放服务区 5 项。**','**固定核对表共336项：本轮已同步297项，剩39项名称未确认；保留已同步行供追溯，不重新编号。**')
md=md.replace('这份表列出当前 JSON 中全部 `unknown` 项；“未确认”表示尚无可采用的确定名称，不等同于每一处原图文字都完全无法辨认。当前原图文字较模糊，不能仅凭色块、家具或常见配置确定房名。','这份表保留最初336项的固定映射，并覆盖当前全部名称未确认项。未确认项的候选只在本表中，JSON不写入猜测名称；S274的中庭面积类别已确认，名称仍待定。不能仅凭色块、家具或常见配置确定房名。')
md=md.replace('各片区附三倍放大定位图；放大便于定位，但不能恢复原图已丢失的文字细节。','原始总图仍用于回查固定编号；各片区现附补充照片配准后的局部定位图。配准只用于对照，不替换原图或改变原坐标；放大不恢复已缺失的文字。')
photo_for_group={0:2,1:1,2:3,3:4,4:6,5:4,6:9,7:6,8:7,9:9,10:8,11:10,12:11,13:11}
for group,photo in photo_for_group.items():
    entries=[r for r in M if r['group']==group]
    old_image=entries[0]['detail']
    pattern=r'!\[([^\]]*)\]\(../../临时核对/15_盐城市妇幼保健院_名称核对_20261101/'+re.escape(old_image)+r'\)'
    target=f'../../临时核对/15_盐城市妇幼保健院_照片同步_20261103/照片定位局部/片区{group+1:02}_照片{photo:02}_编号.jpg'
    md,count=re.subn(pattern,lambda m:f'![{m.group(1)}：补充照片{photo:02}，编号沿用原表]({target})',md)
    assert count==1,(group,count)
    if group==0:
        md=md.replace(f']({target})',f']({target})\n\n![核对08补充照片定位](../../临时核对/15_盐城市妇幼保健院_照片同步_20261103/照片定位局部/片区01_照片05_编号.jpg)',1)
    pending_count=sum(r['group']==group for r in remaining)
    md=re.sub(rf'(^### {group+1:02} .+?)（(\d+)项）',rf'\1（\2项；剩余{pending_count}项）',md,flags=re.M)
    for row in entries:
        # Existing question table is the sole answer location.
        pass
md=re.sub(r'^\*\*类型与数量：\*\*.*$', '**类型与数量：**'+'、'.join(f'{k} {v}个' for k,v in Counter(s['type'] for s in data['spaces']).items())+'。',md,flags=re.M)
md=re.sub(r'^\*\*名称待确认：\*\*.*$','**名称待确认：**剩39项；本轮297项照片识读已同步，详情及确认栏见上方原表。',md,flags=re.M)
md=re.sub(r'^\*\*相对规模：\*\*.*$','**相对规模：**排除11处绿化及S274中庭后，414个室内空间／区域参与归一化，`area_ratio`合计为1。轮廓不变，不保存实测平方米。',md,flags=re.M)
md=re.sub(r'^\*\*面积说明：\*\*.*$','**面积说明：**已落实用户确认的挑空、上空、露天区域不计室内面积口径。S274保留轮廓与稳定编号，`type: courtyard`、`level: open_space`且不保存`area_ratio`；具体名称仍为未确认。其余非绿化室内空间占比已重算。',md,flags=re.M)
md=re.sub(r'^\*\*当前状态：\*\*.*$','**当前状态：**标注草稿；本轮同步297项名称，剩39项，楼层与门洞／主要连通复核仍未收尾。结构通过不代表整图完成。原S001—S426及核对号01—336全部保留，本轮照片、识读记录与修改前备份在`../../临时核对/15_盐城市妇幼保健院_照片同步_20261103/`。',md,flags=re.M)
# Restore Chinese type labels in the overview.
types=json.loads(Path('/Users/hushili/.codex/skills/outpatient-plan-annotation/references/space-types.json').read_text())
md=re.sub(r'^\*\*类型与数量：\*\*.*$', '**类型与数量：**'+'、'.join(f'{types[k]} {v}个' for k,v in Counter(s['type'] for s in data['spaces']).items())+'。',md,flags=re.M)
(P/'annotation.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
(P/'标注说明.md').write_text(md)
(R/'剩余名称核对.json').write_text(json.dumps([dict(r,candidate=uncertain[int(r['number'])][0],alternative=uncertain[int(r['number'])][1],reason=uncertain[int(r['number'])][2]) for r in remaining],ensure_ascii=False,indent=2)+'\n')
print('名称已同步',len(O),'剩余',len(remaining),'室内',len(indoor),'占比合计',sum(s['area_ratio'] for s in indoor))
