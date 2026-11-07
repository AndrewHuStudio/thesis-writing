from pathlib import Path
import json,re,shutil
import pymupdf
P=next(Path('/Users/hushili/Documents/研究-论文写作/大论文/p-平面标注与数据处理/标注试样').glob('28_*'));BASE=P.parents[1]/'临时核对'/P.name;O=BASE/'20261105_照片补充';T=BASE/'20261105_33项诊室确认同步';T.mkdir(exist_ok=True);B=T/'同步前备份';B.mkdir(exist_ok=True)
for f in P.iterdir():
 if f.is_file() and not (B/f.name).exists():shutil.copy2(f,B/f.name)
d=json.loads((P/'annotation.json').read_text());before=json.loads((B/'annotation.json').read_text());ids={f'S{n:03d}' for n in list(range(165,189))+list(range(196,205))};assert len(ids)==33
for s in d['spaces']:
 if s['id'] in ids:s.update(name='诊室',type='consultation')
(P/'annotation.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
md=(P/'标注说明.md').read_text();md=md.replace('44个名称待确认，其中33个可用一次统一命名处理','11个名称／属性待确认，33个重复门诊小间已由用户确认统一为“诊室”')
md=md.replace('待确认名称从104项净降至44项。','照片识读先将待确认名称从104项降至44项；本次依据用户明确回复，再同步33项，现剩11项。')
md=md.replace('## 先处理这一项，可一次减少33项','## 33项统一名称已确认')
md=md.replace('**问题：**是否接受上述33项统一记录为“诊室”（type=consultation），分别保留原S编号和轮廓？','**处理：**S165—S188、S196—S204共33项已统一为“诊室”（type=consultation），原S编号、空间轮廓和连通关系保留。')
md=md.replace('**我的确认／备注（33项统一名称）：**待填写（可填“接受，统一为诊室”；不必逐行写33次）','**我的确认／备注（33项统一名称）：**接受，统一为“诊室”（用户在聊天中明确确认；已同步）')
md=md.replace('## 少量字形、空间属性与成排小间','## 剩余11项字形与空间属性')
md=md.replace('33个成排小间可只回答上方一次统一命名问题。','33个已确认小间已移至下方已解决记录，无需重复填写。')
start=md.index('## 剩余11项');end=md.index('## 关键空间属性与连通核对');section=md[start:end];head,*parts=section.split('### ');kept=[];resolved=[]
for part in parts:
 lines=part.splitlines();out=[];pending=[]
 for line in lines:
  cells=[c.strip() for c in line.split('|')]
  if len(cells)==9 and cells[1].isdigit():
   if cells[2] in ids:
    resolved.append(f'| {cells[1]} | {cells[2]} | 诊室 | — | 用户明确接受粗名称“诊室”，不区分具体专科；已同步JSON与SVG。 | 已确认（用户统一确认） | {cells[1]} |');continue
   pending.append(cells[1])
  out.append(line)
 if not pending:continue
 title=lines[0].split('｜',1)[1];out[0]=(pending[0] if len(pending)==1 else pending[0]+'—'+pending[-1])+'｜'+title
 kept.append('### '+'\n'.join(out).rstrip()+'\n\n')
md=md[:start]+head+''.join(kept)+md[end:]
assert len(resolved)==33
md=md.replace('\n</details>', '\n'+'\n'.join(resolved)+'\n\n</details>')
# 已解决行按原核对号排列，保留所有原字段及现有填写。
a=md.index('<details>');z=md.index('</details>');sub=md[a:z];allrows=[];others=[]
for line in sub.splitlines():
 if re.match(r'\| \d+ \| S\d+',line):allrows.append(line)
 else:others.append(line)
sub='\n'.join(others).rstrip()+'\n'+'\n'.join(sorted(allrows,key=lambda x:int(x.split('|')[1])))+'\n\n';md=md[:a]+sub+md[z:]
(P/'标注说明.md').write_text(md)
r=json.loads((O/'固定核对映射.json').read_text())
for q in r:
 if q['id'] in ids:q.update(candidate='诊室',basis='用户明确确认33个重复门诊小间统一按粗名称诊室记录',confidence='高',status='user_confirmed')
(T/'固定核对映射.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
unknown={s['id'] for s in d['spaces'] if s['type']=='unknown'};pending=[q for q in r if q['id'] in unknown];assert len(pending)==11
(T/'剩余核对映射.json').write_text(json.dumps(pending,ensure_ascii=False,indent=2)+'\n')
# 持久保留上轮映射快照，本轮从新映射生成剩余11项总图。
s=(BASE/'20261105_首次补充/历史取证/99_command.txt').read_text().split("<<'PY'\n",1)[1].split('\nPY\n',1)[0]
s=s.replace('p-写作过程','p-平面标注与数据处理').replace("Path('/tmp/outpatient28-review')",f'Path({str(T)!r})').replace("T/'review-map.json'","T/'剩余核对映射.json'")
s=s.replace("'标注草稿 · 125项待确认 · 完整原图居中 · 黄色框内为本轮核对号'","'剩余11项待确认；33个门诊小间已确认诊室；沿用原核对号'")
s=s.split("md=['# 28号名称核对表'",1)[0]+"print('remaining labels',len(paths),'crossings',len(cross))";exec(s,{})
rev=pymupdf.open(T/'28_核对总图.svg');rev[0].get_pixmap(matrix=pymupdf.Matrix(2,2)).save(T/'28_剩余11项核对总图.png');rev[0].get_pixmap(matrix=pymupdf.Matrix(.5,.5)).save(T/'28_剩余11项核对总图_预览.png')
md=(P/'标注说明.md').read_text();md=md.replace('../../临时核对/'+P.name+'/20261105_照片补充/28_剩余核对总图_高清.png','../../临时核对/'+P.name+'/20261105_33项诊室确认同步/28_剩余11项核对总图.png');(P/'标注说明.md').write_text(md)
(T/'用户确认记录.json').write_text(json.dumps(dict(answer='接受，统一为“诊室”',space_ids=sorted(ids),names_complete=False,remaining_unknown=sorted(unknown)),ensure_ascii=False,indent=2)+'\n')
shutil.copy2('/tmp/confirm28_consultations.py',T/'同步33项诊室.py')
print('confirmed',len(ids),'remaining',sorted(unknown),'geometry and relations unchanged',d['relations']==before['relations'] and all(x['polygon_px']==y['polygon_px'] for x,y in zip(d['spaces'],before['spaces'])))
