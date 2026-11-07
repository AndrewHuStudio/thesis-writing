from pathlib import Path
from collections import Counter
import json,re,hashlib,xml.etree.ElementTree as ET
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parent
P=R.parent.parent/'标注试样/15_盐城市妇幼保健院'
B=Path((R/'本轮备份路径.txt').read_text().strip())
original=json.loads((B/'annotation.json').read_text());data=json.loads((P/'annotation.json').read_text())
old={s['id']:s for s in original['spaces']};current={s['id']:s for s in data['spaces']}
assert list(old)==list(current)
assert data['image']==original['image']
assert data['relations']==original['relations']
for sid,s in current.items():
    assert s['polygon_px']==old[sid]['polygon_px']
    if old[sid]['type']!='unknown':
        for key in ['name','type','level','scope']:assert s[key]==old[sid][key],(sid,key)
assert (P/'15_盐城市妇幼保健院_原图.jpg').read_bytes()==(B/'15_盐城市妇幼保健院_原图.jpg').read_bytes()
remaining=json.loads((R/'剩余名称核对.json').read_text())
# Unchanged source plan plus only remaining original review numbers.
im=Image.open(P/'15_盐城市妇幼保健院_原图.jpg').convert('RGB').resize((4888,6520))
draw=ImageDraw.Draw(im);font=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',25)
for row in remaining:
    pts=[tuple(v*2 for v in q) for q in current[row['id']]['polygon_px']]
    draw.line(pts+[pts[0]],fill='#d97706',width=4)
    x=min(v[0] for v in pts)+3;y=min(v[1] for v in pts)+3
    label=row['number'];bounds=draw.textbbox((x,y),label,font=font)
    draw.rectangle((bounds[0]-2,bounds[1]-2,bounds[2]+2,bounds[3]+2),fill='white',outline='#d97706',width=2)
    draw.text((x,y),label,fill='#9a3412',font=font)
im.save(R/'剩余39项定位总图.png')
md=(P/'标注说明.md').read_text();rows=[]
for line in md.splitlines():
    c=[v.strip() for v in line.strip().strip('|').split('|')]
    if len(c)==7 and re.fullmatch(r'S\d+',c[1]):rows.append(c)
assert len(rows)==336 and len(set(r[0] for r in rows))==336
initial=[]
for line in (B/'标注说明.md').read_text().splitlines():
    c=[v.strip() for v in line.strip().strip('|').split('|')]
    if len(c)==7 and re.fullmatch(r'S\d+',c[1]):initial.append(c)
assert [(r[0],r[1],r[6]) for r in rows]==[(r[0],r[1],r[6]) for r in initial]
assert sum(r[5]=='照片识读已同步；非用户填写' for r in rows)==297
pending_ids={s['id'] for s in data['spaces'] if s['type']=='unknown' or '未确认' in s['name']}
assert pending_ids=={r['id'] for r in remaining}
for row in rows:
    if row[5]=='照片识读已同步；非用户填写':assert row[2]==current[row[1]]['name']
links=re.findall(r'!\[[^\]]*\]\(([^)]+)\)',md)
assert all((P/link).resolve().is_file() for link in links)
assert 'area_ratio' not in current['S274']
assert len([s for s in data['spaces'] if 'area_ratio' in s])==414
assert abs(sum(s.get('area_ratio',0) for s in data['spaces'])-1)<1e-6
assert len(list(P.iterdir()))==4
svg=ET.parse(P/'标注.svg');groups={e.get('id'):e for e in svg.iter() if e.get('data-space-name') is not None}
assert set(groups)==set(current)
for sid,s in current.items():
    assert groups[sid].get('data-space-name')==s['name']
    assert groups[sid].get('data-space-type')==s['type']
    labels=''.join(e.text or '' for e in groups[sid].iter() if e.tag.endswith('}text'))
    assert sid in labels
    if sid not in pending_ids:
        assert s['name'] in labels,(sid,s['name'],labels)
result={'spaces':len(current),'names_added':297,'pending_names':len(pending_ids),'indoor_spaces':414,'excluded_spaces':12,'area_sum':sum(s.get('area_ratio',0) for s in data['spaces']),'stable_ids':True,'polygons_unchanged':True,'prior_names_preserved':True,'source_unchanged':True,'relations_unchanged':True,'review_rows_preserved':True,'embedded_images_valid':len(links),'svg_labels_match':True}
(R/'本轮同步核验.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
