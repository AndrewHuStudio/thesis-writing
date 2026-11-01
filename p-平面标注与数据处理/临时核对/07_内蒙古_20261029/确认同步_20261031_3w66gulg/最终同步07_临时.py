from pathlib import Path
import json,copy,hashlib,re,shutil,subprocess,sys,os
B=Path(__file__).resolve().parent;P=Path((B/'项目路径.txt').read_text());SK=Path('/Users/hushili/.codex/skills/outpatient-plan-annotation')
backup=B/'最终确认前备份';backup.mkdir(exist_ok=False)
for f in P.iterdir():
 if f.suffix in {'.json','.md','.svg'}:shutil.copy2(f,backup/f.name)
oldmd=(P/'标注说明.md').read_text();D=json.loads((P/'annotation.json').read_text());by={s['id']:s for s in D['spaces']}
for sid in ['S155','S402','S404']:
 s=by[sid];s.update(type='courtyard',level='open_space');s.pop('area_ratio',None)
by['S165'].update(name='休息间',type='staff_support',level='room')
by['S278'].update(name='值班台',type='service_work_area',level='semi_open_space')
assert by['S151']['name']==by['S154']['name']=='儿科取药窗口' and by['S153']['name']=='门诊药房'
# 原200号横向隔墙在原图y=1605—1609，保留上方S289值班，下方新增S410阅片室。
original=copy.deepcopy(by['S289']);by['S289'].update(name='值班',type='staff_support',level='room',polygon_px=[[1538,1548],[1614,1548],[1614,1604],[1538,1604]])
assert max(int(s['id'][1:]) for s in D['spaces'])==409
new=copy.deepcopy(original);new.update(id='S410',name='阅片室',type='office',level='room',polygon_px=[[1538,1610],[1614,1610],[1614,1683],[1538,1683]])
D['spaces'].append(new)
rnum=max(int(r['id'][1:]) for r in D['relations'] if r['id'].startswith('R'))+1
D['relations'].append({'id':f'R{rnum:03}','source':'S410','target':'S268','type':'access'})
# 开放庭院不作为室内通行节点，剔除可能残留的人员可达关系。
D['relations']=[r for r in D['relations'] if not(r['type']=='access' and ({r['source'],r['target']} & {'S155','S402','S404'}))]
(P/'annotation.json').write_text(json.dumps(D,ensure_ascii=False,indent=2)+'\n')
tool=SK/'scripts/annotation_tools.py'
for args in [['normalize',str(P/'annotation.json')],['render',str(P/'annotation.json'),'--output',str(P/'标注.svg')],['summary',str(P/'annotation.json'),'--output',str(B/'最终概览_临时.md')],['validate',str(P/'annotation.json'),'--check-dir']]:
 res=subprocess.run([sys.executable,str(tool)]+args,capture_output=True,text=True)
 (B/('最终_'+args[0]+'_结果.txt')).write_text(res.stdout+'\n'+res.stderr)
 print(args[0],res.returncode,res.stdout[:750])
 assert res.returncode==0,(args,res.stdout,res.stderr)
# 原填写表迁至样本之外，保留原稿与最终补充，不丢失填写历史。
archive=B/'最终核对记录.md'
body=oldmd[oldmd.index('### 01—39'):]
corrections={
 '112':'儿科取药窗口；已确认，与114同名窗口，113药房保持独立。',
 '113':'门诊药房；已确认，独立保留。',
 '114':'儿科取药窗口；已确认，与112同名窗口，113药房保持独立。',
 '115':'内庭院；已确认，露天／挑空，不计室内面积。',
 '118':'休息间；已确认，仅一个休息间。',
 '195':'值班台；已确认，S278按半开放服务工作区记录。',
 '200':'上方值班、下方阅片室，中间隔墙；已确认，S289值班、S410阅片室。',
 '268':'内天井；已确认，露天／挑空，不计室内面积。',
 '269':'儿童活动区；已确认，按庭院／中庭处理，不计室内面积。'
}
newlines=[]
for line in body.splitlines():
 if re.match(r'^\|\s*\d+\s*\|',line):
  c=[x.strip() for x in line.split('|')[1:-1]];n=str(int(c[0]))
  if n in corrections:c[5]=corrections[n]
  c[6]=c[0];line='| '+' | '.join(c)+' |'
 newlines.append(line)
# 原说明表格图片路径相对样本目录，此归档位于外部核对目录，转换相对链接。
archive_body='\n'.join(newlines)
def relink(match):
 target=match.group(1)
 return ']('+Path(os.path.relpath((P/target).resolve(),B)).as_posix()+')'
archive_body=re.sub(r'\]\(([^)]+)\)',relink,archive_body)
archive.write_text('# 07号最终核对记录\n\n2026-10-31完成本轮名称确认；原核对号保持01—269。此表保留历史候选及证据，最终事实以当前JSON、SVG和用户补充为准。\n\n'+archive_body+'\n')
summary=(B/'最终概览_临时.md').read_text().replace('# 平面标注概览','# 07 内蒙古自治区儿童医院、妇产医院、妇幼保健院外迁合建项目门诊医技楼一层标注',1)
summary=summary.replace('空间名称已齐；结构与关系仍以原图及人工核对为依据。','本张图已完成名称确认与正式四文件校验（2026-10-31），无未确认功能。',1)
summary=summary.replace('室内非重叠标注区域的 `area_ratio` 合计为 1；绿化不参与。','406个室内概念区域的 `area_ratio` 合计约为 1；3处庭院／中庭不参与室内面积归一化。',1)
summary += '''
**范围与精度：**本次完成仅限07号门诊医技楼一层这张平面，包含儿科急诊、妇产科急诊、输液中心、门诊药房、产科门诊、发热门诊与哮喘中心、影像中心、产科超声与围产保健及公共医疗街。空间统计包括房间、开放空间、半墙服务区、交通核及通道分区，不等同于独立房间数。原图未修改。

**庭院与面积：**核对115／S155“内庭院”、268／S402“内天井”、269／S404“儿童活动区”均按用户确认的庭院／中庭处理，类型为 `courtyard`、层级为 `open_space`，不保存 `area_ratio`，不作为室内通行节点。

**边界修正：**66拆分为S084刷手、S407更衣、S408准备间；200拆分为S289值班、S410阅片室；203拆分为S295阅片室与S409办公室，208原S302已并入S409。112、114分别保留为儿科取药窗口，113为独立门诊药房。其余稳定S编号沿用。

**关系精度：**关系记录可辨开口、已确认连续区域及服务联系；相邻不自动表示可达，未记录关系不自动表示不可达。此图为概念级标注，未补造施工门构造、门禁权限或完整通行网络；正式校验通过表示名称和数据结构等交付检查通过。

'''
archive_rel=Path(os.path.relpath(archive,P)).as_posix()
summary+=f'**核对记录：**[查看01—269最终核对记录]({archive_rel})。用户填写过程和修改前备份保存在样本目录之外。\n'
(P/'标注说明.md').write_text(summary)
assert hashlib.sha256((P/D['image']['file']).read_bytes()).hexdigest()==(B/'原图哈希.txt').read_text()
assert len(list(P.iterdir()))==4
print('FINAL_COUNTS',len(D['spaces']),len(D['relations']))
print('ARCHIVE',archive)
