from coarse_common import Plan,SKILL
from pathlib import Path
import json,sys,os,subprocess,hashlib
from collections import Counter
from shapely.geometry import Polygon,Point

def run(n,verified=False):
 p=Plan(n);p.d=json.loads((p.root/'annotation.json').read_text());p.st=json.loads((p.review/'review_state.json').read_text())
 current={s['id']:s for s in p.d['spaces']};old={s['id']:s for s in p.old['spaces']}
 assert set(old)<=set(current),'old IDs disappeared'
 assert hashlib.sha256((p.root/p.d['image']['file']).read_bytes()).digest()==hashlib.sha256((p.out/'修改前备份'/p.d['image']['file']).read_bytes()).digest()
 oldpoints={o['id']:o['position_px'] for r in p.old['relations'] for o in r.get('openings',[])}
 points={o['id']:o['position_px'] for r in p.d['relations'] for o in r.get('openings',[])}
 assert all(points[k]==v for k,v in oldpoints.items()),'existing point ID/position changed'
 # 图像证据检查之后才写人工实查状态。
 if verified:
  p.st['checks'].update(individual_outline_reviewed=True,region_outline_reviewed=True,connectivity_reviewed=True,visual_reviewed=True)
  p.st['visual_evidence']=[str(q.relative_to(p.review)) for q in p.out.glob('正式SVG*.png')]+[str((p.out/'区域轮廓概览.png').relative_to(p.review))]
  p.st['current_scope_review']='已检查本图原图、逐间粗框、区域外轮廓、已有门洞及拆分后两端关系；房名和辅助入口缺失保留原始信息局限。'
 (p.review/'review_state.json').write_text(json.dumps(p.st,ensure_ascii=False,indent=2)+'\n')
 counts=Counter(r['type'] for r in p.d['relations']);unknown=sum(s['type']=='unknown' for s in current.values());located=sum(r['type']=='access' and bool(r.get('openings')) for r in p.d['relations']);concept=counts['access']-located
 rel=os.path.relpath(p.out,p.root)
 limitations=p.st['source_limitations']
 text=[f'# {p.root.name}｜区域级粗轮廓标注','', '<!-- annotation:summary:start -->','<!-- annotation:summary:end -->','',
 f'**范围：**{len(p.st["regions"])}个区域外轮廓，内部可辨围合逐个保留S编号；本轮由{len(old)}个空间细分为{len(current)}个，新增编号续接。区域叠加不进入spaces，不重复计面积。','',
 f'**连通：**{counts["access"]}条人员可达，{counts["service"]}条服务联系，{counts["entrance"]}个入口；{located}条可达关系定位{len(points)}个门洞／开口，另{concept}条为无定位概念连接。服务窗口及共墙不自动作为通行。','',
 f'**资料缺失：**{unknown}项专门房名继续保留unknown，`names_complete=false`；本轮完成口径是区域级粗轮廓，不能解释为全部房名已识别。旧名称候选、固定核对号和原填写均保存在本轮备份及review_state，无需逐项猜名。','',
 f'![区域外轮廓与逐空间概览]({rel}/区域轮廓概览.png)','',f'[打开概览原尺寸]({rel}/区域轮廓概览.png)','',
 '已知区域标题保存在区域成员映射；拆出的无名小间不把整科室名称当成具体用途。交通核整体保留，家具、床位、柜台及厕位不拆成房间。已确定的庭院／绿化继续不计室内面积；用途未明的空白块不擅自认作庭院。','',
 '**仍保留未知：**','']+['- '+v for v in limitations]+['',
 '原连通核对题已按本轮范围复核：辅助房门或内部捷径未画清时保留未知，不等同于已确认不相通；相应依据和原题保存在外部记录。未记录关系不能用作不连通负例。','']
 (p.root/'标注说明.md').write_text('\n'.join(text))
 r=subprocess.run([sys.executable,str(SKILL/'annotation_tools.py'),'summary',str(p.root/'annotation.json'),'--output',str(p.root/'标注说明.md'),'--review-state',str(p.review/'review_state.json')],text=True,capture_output=True)
 assert r.returncode==0,r.stdout+r.stderr
 r=subprocess.run([sys.executable,str(SKILL/'annotation_tools.py'),'validate',str(p.root/'annotation.json'),'--check-dir','--review-state',str(p.review/'review_state.json')],text=True,capture_output=True)
 (p.out/'本轮范围正式校验.json').write_text(r.stdout)
 data=json.loads(r.stdout);print(n,'exit',r.returncode,json.dumps({k:v for k,v in data.items() if k!='pending_name_ids'},ensure_ascii=False))
 if verified:assert r.returncode==0 and data['complete'] and not data['names_complete'],r.stdout
 # 自定义端点审计逐P检查，技能结构检查不替代此证据。
 polys={sid:Polygon(s['polygon_px']) for sid,s in current.items()};errors=[]
 for rr in p.d['relations']:
  for o in rr.get('openings',[]):
   point=Point(o['position_px']);dd=[polys[x].distance(point) for x in [rr['source'],rr['target']]]
   if max(dd)>3:errors.append([o['id'],rr['id'],dd])
 assert not errors,errors
 audit={'original_ids_preserved':True,'original_opening_ids_and_coordinates_preserved':True,'image_hash_unchanged':True,'spaces':len(current),'unknown':unknown,'relations':dict(counts),'openings':len(points),'regions':len(p.st['regions']),'opening_endpoint_exceptions':errors,'directory_files':[q.name for q in p.root.iterdir() if q.is_file()]}
 assert len(audit['directory_files'])==4
 (p.out/'交付一致性检查.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
for n in [a for a in sys.argv[1:] if a!='--verified']:run(int(n),verified='--verified' in sys.argv)
