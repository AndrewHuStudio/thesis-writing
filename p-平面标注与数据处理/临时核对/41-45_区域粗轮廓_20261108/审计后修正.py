from pathlib import Path
import json
O=Path(__file__).resolve().parent

def edit(n,fn):
 p=O/f'配置{n}.json';d=json.loads(p.read_text());fn(d);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def a(d):
 d['update_relations'].update({'38':{'target':'S029'},'39':{'target':'S029'}})
 d['doors']['54']=[1470,830];d['doors']['91']=[1590,1900]
 d['remove_relations']={'57':'原关系跨越设备间S052，公共带并不在此直接连接。','76':'便民服务中心东侧由扶梯核隔开，保留其北侧实际入口R075。'}
edit('41',a)
def b(d):
 for k,v in {'8':[1790,1916,'open_passage'],'14':[1561,2130],'22':[1650,2316],
 '28':[1640,2050],'62':[925,1105,'open_passage'],'65':[880,1809,'open_passage']}.items():d['doors'][k]=v
 d['doors'].pop('38')
edit('42',b)
def c(d):
 d['regions'][2][1].remove(10)
edit('43',c)
def e(d):
 d.setdefault('update_relations',{}).update({'2':{'target':'S007'},'8':{'source':'S011'}})
 d['doors']['1']=[1930,1101,'open_passage'];d['doors']['8']=[1800,2050]
edit('44',e)
def f(d):
 d.setdefault('update_relations',{}).update({'69':{'source':'S047'}})
 d['doors']['40']=[1136,300,'open_passage'];d['doors']['69']=[495,875,'open_passage']
 d['new_relations'][2][1]=76;d['new_relations'][2][3]='两小格东侧短通道南端连续接放射科通道'
 d['new_relations'][-1][1]=76;d['new_relations'][-1][3]='CT北侧墙可辨门洞接放射科通道'
 d['subtract'].append([37,[548,566,576,608]])
 d['extend']=[[37,[422,550,430,626]]]
edit('45',f)
