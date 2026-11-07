from pathlib import Path
import collections
import html
import importlib.util
import json
import re
import xml.etree.ElementTree as ET

from shapely.geometry import Polygon, Point

WORK=Path(__file__).resolve().parent
ROOT=WORK.parents[3]
SAMPLE=ROOT/'p-平面标注与数据处理/标注试样'/WORK.parent.name
SKILL=Path('/Users/hushili/.codex/skills/outpatient-plan-annotation')
spec=importlib.util.spec_from_file_location('annotation_tools',SKILL/'scripts/annotation_tools.py')
at=importlib.util.module_from_spec(spec)
spec.loader.exec_module(at)
NS='http://www.w3.org/2000/svg'
ET.register_namespace('',NS)
ET.register_namespace('xlink','http://www.w3.org/1999/xlink')


def place_opening_labels(tree):
    groups=tree.findall('.//{'+NS+'}g');obstacles=[];labels=[];audit=[]
    for g in groups:
        if (g.get('id') or '').startswith(('S','E')):
            for r in g.findall('{'+NS+'}rect'):
                x,y,w,h=[float(r.get(k)) for k in ['x','y','width','height']]
                from shapely.geometry import box
                obstacles.append(box(x,y,x+w,y+h))
    for g in groups:
        oid=g.get('data-opening-id')
        if not oid:continue
        circle=g.find('{'+NS+'}circle');x=float(circle.get('cx'));y=float(circle.get('cy'))
        text=g.find('{'+NS+'}text')
        for k in ['stroke','stroke-width','paint-order']:text.attrib.pop(k,None)
        font=8.5;width=4*font*.6+3;height=font+3
        offsets=[(5,-height-3),(5,3),(-width-5,-height-3),(-width-5,3),
                 (5,-height-15),(5,15),(-width-5,-height-15),(-width-5,15)]
        choices=[]
        for i,(dx,dy) in enumerate(offsets):
            from shapely.geometry import box
            rect=box(x+dx,y+dy,x+dx+width,y+dy+height)
            overlap=sum(rect.intersection(o).area for o in obstacles+labels)
            choices.append((overlap*100+i,x+dx,y+dy,rect,overlap))
        score,left,top,rect,overlap=min(choices,key=lambda v:v[0])
        bg=ET.Element('{'+NS+'}rect',{'x':str(left),'y':str(top),'width':str(width),
            'height':str(height),'fill':'white','fill-opacity':'.94','rx':'1'})
        g.insert(list(g).index(text),bg)
        text.set('x',str(left+1.5));text.set('y',str(top+font));text.set('font-size',str(font))
        text.set('font-weight','700');text.set('fill','#b91c1c')
        labels.append(rect);audit.append({'id':oid,'overlap_area':overlap})
    (WORK/'P编号排版核验.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
    assert all(x['overlap_area']<.01 for x in audit)


if __name__=='__main__':
    path=SAMPLE/'annotation.json'
    for name in ['annotation.json','标注.svg','标注说明.md']:
        assert (SAMPLE/name).read_bytes()==(WORK/'修改前备份'/name).read_bytes(),f'{name} changed after backup'
    original=json.loads(path.read_text());data=json.loads(path.read_text())
    text=html.unescape((SAMPLE/'标注说明.md').read_text())
    assert '**请做这一步：**值班' in text
    assert '**我的补充／备注（08／S023）：辅助用房**' in text
    assert '不计入室内面积，功能也删除，我们只统计室内' in text
    # Concrete room name 值班 and the generic support-room confirmation agree.
    # The final chat reply explicitly classified both 33 and 34 as 辅助用房.
    updates={'S023':('值班','staff_support'),'S081':('辅助用房','auxiliary_room'),'S082':('辅助用房','auxiliary_room')}
    for s in data['spaces']:
        if s['id'] in updates:s['name'],s['type']=updates[s['id']]
    removed=next(s for s in data['spaces'] if s['id']=='S079')
    assert not any('S079' in [r.get('source'),r.get('target')] for r in data['relations'])
    data['spaces']=[s for s in data['spaces'] if s['id']!='S079']
    assert data['relations']==original['relations']
    assert [(s['id'],s['polygon_px']) for s in data['spaces']]==[(s['id'],s['polygon_px']) for s in original['spaces'] if s['id']!='S079']
    at.normalize(data)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    at.render(data,path,SAMPLE/'标注.svg')
    tree=ET.parse(SAMPLE/'标注.svg');headers=tree.getroot().findall('{'+NS+'}text')
    headers[0].text='18号东营市人民医院 · 一层概念级空间标注'
    headers[1].text='132个具名室内空间；137处定位开口；室外坡道已排除'
    place_opening_labels(tree)
    tree.write(SAMPLE/'标注.svg',encoding='unicode')
    at.summary(data,WORK/'标准概览.md')
    overview=(WORK/'标准概览.md').read_text().replace('# 平面标注概览','# '+SAMPLE.name+'｜一层概念级标注',1)
    relative=Path('../../临时核对')/WORK.parent.name/WORK.name
    audit=json.loads((WORK.parent/'连通复核_20261103_150036/关系增量及依据.json').read_text())
    by_id={r['id']:r for r in data['relations']}
    lines=[overview,'','**状态：**最终核验中。','',
        '**范围与编号：**仅18号原图完整一层的室内空间。按用户“只统计室内”的确认，原S079西侧下行坡道已从空间数据、功能标注及面积分母删除；S079不重用，其余S编号及轮廓保持稳定。原图文件不改动。',
        '', '**最终确认：**08／S023采用回填的具体名称“值班”，归入工作人员支持用房；33／S081、34／S082按用户最终回复统一记为“辅助用房”，保留两个独立空间，采用共享类别auxiliary_room。K01已确认整个S027沿用“病员更衣”，不再拆分。A01坡道排除已落实，室内面积比例已重新归一化。',
        '', '**连通精度：**门洞、无门开口记录原图近似像素位置，并与SVG红点一一对应。服务窗口、共墙不作为人员通行；不同入口不通过室外总节点互连。交通核与成组支持房按现有整体节点记录，内部施工细节不继续细分。未记关系不自动表示不可达。',
        '', '**入口复核：**6个建筑入口有本图依据。原E007是S125室内门厅的误记，已撤销；S125仍与厅内S123及交通核S124相连。办公门厅南侧入口沿用E005。',
        '', '**无定位概念连接的依据：**','',
        '| 关系 | 空间对 | 依据 |','| --- | --- | --- |']
    for rid,basis in audit['retained_concept'].items():
        r=by_id[rid];lines.append(f'| {rid} | {r["source"]}—{r["target"]} | {basis} |')
    lines += ['',f'**核对记录：**[用户最新回填原样归档]({relative}/用户最新回填原样归档.md)；[最终补充及落实记录]({relative}/最终确认落实.md)。核对号01—50、K01、A01及历次填写均在外部核对目录保留，正式说明收敛为本概览。',
        '', '[查看原图]('+data['image']['file']+')｜[查看SVG标注](标注.svg)｜[查看全图红点]('+str(relative)+'/终版全图.png)',
        '', '**适用精度：**医院一层概念级房间布局与人员可达关系；轮廓、面积比例和开口位置不作为施工测绘数据。', '']
    (SAMPLE/'标注说明.md').write_text('\n'.join(lines))
    (WORK/'最终确认落实.md').write_text('''# 18号最终补充及落实

- 08／S023：最新MD把提示处改为“值班”，补充栏写“辅助用房”。采用具体名称“值班”，类别staff_support；完整原文另存用户最新回填原样归档.md。
- 33／S081、34／S082：最新MD仍留“待填写”，随后用户在聊天中明确回复“两间均按‘辅助用房’记录”。两间均采用名称“辅助用房”、类别auxiliary_room，保持独立及原边界。
- A01／S079：用户填写“不计入室内面积，功能也删除，我们只统计室内”。从JSON和SVG功能标注删除S079，重算其他空间面积比例；稳定编号不重排。
- K01／S027：用户已明确“整个S027沿用此名称”，整间名称“病员更衣”及既有轮廓保持。
- 所有157条关系、137个开口的P编号／类型／坐标保持不变。
''')
    (WORK/'收尾数据增量.json').write_text(json.dumps({'updated_spaces':updates,'removed_space':removed,'relations_unchanged':True,'stable_ids_preserved':True,'old_area_sum':sum(s.get('area_ratio',0) for s in original['spaces']),'new_area_sum':sum(s.get('area_ratio',0) for s in data['spaces'])},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'spaces':len(data['spaces']),'relations':len(data['relations']),'openings':sum(len(r.get('openings',[])) for r in data['relations']),'unknown':len(at.unresolved(data)),'area_sum':sum(s.get('area_ratio',0) for s in data['spaces'])},ensure_ascii=False))
