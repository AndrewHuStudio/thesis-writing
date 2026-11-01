from pathlib import Path
import copy, json, subprocess, sys, tempfile, unittest, xml.etree.ElementTree as ET
import pymupdf

TOOL=Path(__file__).resolve().parents[1]/'scripts/annotation_tools.py'

class AnnotationContract(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.p=Path(self.tmp.name)
        pix=pymupdf.Pixmap(pymupdf.csRGB,pymupdf.IRect(0,0,200,100),False);pix.clear_with(255);pix.save(self.p/'source.png')
        self.data={'image':{'file':'source.png','width':200,'height':100},'spaces':[
            {'id':'S001','name':'大厅','type':'hall','level':'open_space','scope':'public_service','polygon_px':[[0,0],[100,0],[100,100],[0,100]],'area_ratio':0.55555556},
            {'id':'S002','name':'诊室','type':'consultation','level':'room','scope':'ordinary_outpatient','polygon_px':[[100,0],[180,0],[180,100],[100,100]],'area_ratio':0.44444444},
            {'id':'S003','name':'绿化','type':'landscape','level':'landscape','scope':'nonclinical','polygon_px':[[180,0],[200,0],[200,100],[180,100]]}],
            'relations':[{'id':'R001','source':'S001','target':'S002','type':'access'},
                         {'id':'E001','source':None,'target':'S001','type':'entrance','name':'门诊入口','entrance_type':'outpatient_main','position_px':[0,50]}]}
        self.f=self.p/'annotation.json';self.write()
    def tearDown(self):self.tmp.cleanup()
    def write(self):self.f.write_text(json.dumps(self.data,ensure_ascii=False))
    def run_tool(self,*args):
        if not TOOL.exists():self.skipTest('helper not implemented yet')
        return subprocess.run([sys.executable,str(TOOL),*args],capture_output=True,text=True)
    def test_00_tool_exists(self):self.assertTrue(TOOL.is_file(),'Reusable annotation helper is missing')
    def test_incomplete_name_blocks_completion(self):
        self.data['spaces'][1]['name']='名称未确认';self.data['spaces'][1]['type']='unknown';self.write()
        r=self.run_tool('validate',str(self.f));self.assertEqual(r.returncode,2);self.assertIn('S002',r.stdout+r.stderr)
    def test_known_type_does_not_hide_unconfirmed_name(self):
        self.data['spaces'][1]['name']='超声室（候选）';self.write()
        self.assertEqual(self.run_tool('validate',str(self.f)).returncode,2)
    def test_partial_render_shows_names_and_unresolved_notice(self):
        self.data['spaces'][1]['name']='未确认';self.data['spaces'][1]['type']='unknown';self.write()
        out=self.p/'标注.svg';r=self.run_tool('render',str(self.f),'--output',str(out));self.assertEqual(r.returncode,0,r.stderr)
        root=ET.parse(out).getroot();visible=''.join(t.text or '' for t in root.iter() if t.tag.endswith('}text'))
        self.assertIn('大厅',visible);self.assertIn('未确认',visible)
    def test_normalize_uses_indoor_ratio_and_removes_absolute_areas(self):
        for s in self.data['spaces']:s['area_m2']=12;s['area_px2']=300;s.pop('area_ratio',None)
        self.write();r=self.run_tool('normalize',str(self.f));self.assertEqual(r.returncode,0,r.stderr)
        d=json.loads(self.f.read_text());self.assertAlmostEqual(sum(s.get('area_ratio',0) for s in d['spaces']),1,places=6)
        self.assertNotIn('area_ratio',d['spaces'][2]);self.assertTrue(all('area_m2' not in s and 'area_px2' not in s for s in d['spaces']))
    def test_render_summary_and_final_validation_keep_four_files(self):
        svg=self.p/'标注.svg';md=self.p/'标注说明.md'
        for args in [('render',str(self.f),'--output',str(svg)),('summary',str(self.f),'--output',str(md)),('validate',str(self.f),'--check-dir')]:
            r=self.run_tool(*args);self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertEqual(len(list(self.p.iterdir())),4)
        root=ET.parse(svg).getroot();visible=''.join(t.text or '' for t in root.iter() if t.tag.endswith('}text'))
        self.assertIn('诊室',visible);self.assertIn('门诊入口',visible)
    def test_bad_relation_endpoint_rejected(self):
        self.data['relations'][0]['target']='S999';self.write()
        self.assertNotEqual(self.run_tool('validate',str(self.f)).returncode,0)
    def test_construction_fields_rejected(self):
        self.data['relations'][0]['door_width']=900;self.write()
        self.assertNotEqual(self.run_tool('validate',str(self.f)).returncode,0)

if __name__=='__main__':unittest.main(verbosity=2)
