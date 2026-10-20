import email.policy
from email.parser import BytesParser
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch
import uuid
from PIL import Image, ImageDraw

from localstudio import projects, lipsync
from localstudio.brief import explicit_plan
from localstudio.engine import ffmpeg, plan, render, run
from localstudio.workflows import reference_frame_workflow, reference_video_workflow

BRIEF = '''Tạo video gia đình 25–30 giây. Căn bếp Việt Nam, ánh sáng ban ngày.
– 0–5 giây: Người phụ nữ cầm sản phẩm. Cô nói: “Giữ nguyên câu mở đầu.”
– 5–13 giây: Rút giấy. Cô nói: “Đây là câu thoại thứ hai.”
– 13–20 giây: Lau bàn. Cô nói: “Đây là câu thoại thứ ba.”
– 20–28 giây: Giới thiệu. Cô nói: “Xem liên kết sản phẩm nhé!”
Âm thanh: giọng nữ tiếng Việt, khớp chính xác chuyển động môi.
Yêu cầu hình ảnh: Không tự thêm chữ trên video.'''


class FixtureComfy:
    """Protocol/media fixture. It DOES NOT execute neural models."""
    def __init__(self, folder):
        self.folder, self.uploads, self.graphs, self.outputs = Path(folder), {}, [], {}
        self.server = None
    def start(self):
        fixture = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def json(self, data):
                self.send_response(200);self.end_headers();self.wfile.write(json.dumps(data).encode())
            def do_POST(self):
                raw = self.rfile.read(int(self.headers['Content-Length']))
                if self.path == '/upload/image':
                    message = BytesParser(policy=email.policy.default).parsebytes(('Content-Type: '+self.headers['Content-Type']+'\r\n\r\n').encode()+raw)
                    part = next(x for x in message.iter_parts() if x.get_param('name', header='content-disposition') == 'image')
                    name = part.get_filename();fixture.uploads[name] = part.get_payload(decode=True)
                    return self.json({'name':name,'subfolder':'','type':'input'})
                if self.path == '/free':
                    self.send_response(200);self.end_headers();return
                graph = json.loads(raw)['prompt'];fixture.graphs.append(graph)
                prompt_id = uuid.uuid4().hex
                if any(node['class_type'] == 'SaveImage' for node in graph.values()):
                    name = prompt_id+'.png'
                    product_node = graph['6']['inputs']['image']
                    fixture.outputs[name] = fixture.uploads[product_node]
                else:
                    frames = next(node['inputs']['length'] for node in graph.values() if node['class_type'] == 'Wan22ImageToVideoLatent')
                    path = fixture.folder / f'video-{frames}.webm'
                    if not path.is_file():
                        subprocess.run([ffmpeg(),'-v','error','-y','-f','lavfi','-i','testsrc2=size=180x320:rate=24','-frames:v',str(frames),'-c:v','libvpx-vp9',str(path)],check=True)
                    name = prompt_id+'.webm';fixture.outputs[name]=path.read_bytes()
                fixture.outputs[prompt_id] = name
                return self.json({'prompt_id':prompt_id})
            def do_GET(self):
                if self.path == '/object_info':
                    info={}
                    for graph in (reference_frame_workflow('x.png','y.png'),reference_video_workflow('x.png')):
                        for node in graph.values():
                            specs={key:['TEST_TYPE'] for key in node['inputs']}
                            info[node['class_type']]={'input':{'required':specs}}
                    return self.json(info)
                if self.path.startswith('/history/'):
                    pid=self.path.rsplit('/',1)[-1];name=fixture.outputs[pid]
                    return self.json({pid:{'status':{'status_str':'success'},'outputs':{'out':{'images':[{'filename':name,'subfolder':'','type':'output'}]}}}})
                if self.path.startswith('/view?'):
                    from urllib.parse import parse_qs,urlsplit
                    name=parse_qs(urlsplit(self.path).query)['filename'][0]
                    self.send_response(200);self.end_headers();self.wfile.write(fixture.outputs[name]);return
                self.send_response(404);self.end_headers()
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url=f'http://127.0.0.1:{self.server.server_port}'
        return self
    def stop(self):
        self.server.shutdown();self.server.server_close();self.thread.join()


class ReferenceTests(unittest.TestCase):
    def test_exact_dialogue_timeline_and_no_text_are_preserved_without_llm(self):
        with patch('localstudio.engine.request_json') as network:
            result=plan({'prompt':BRIEF,'duration':30,'use_ollama':True})
        network.assert_not_called()
        self.assertEqual(result['duration'],28)
        self.assertEqual([(x['start'],x['end']) for x in result['timeline']],[(0,5),(5,13),(13,20),(20,28)])
        self.assertEqual(result['lines'],['Giữ nguyên câu mở đầu.','Đây là câu thoại thứ hai.','Đây là câu thoại thứ ba.','Xem liên kết sản phẩm nhé!'])
        self.assertFalse(result['burn_subtitles'])
        self.assertTrue(result['requires_lipsync'])

    def test_legacy_render_cannot_claim_lipsync(self):
        with self.assertRaisesRegex(ValueError,'khớp môi'):
            render({'prompt':BRIEF,'duration':30,'mode':'wan'}, {}, lambda _:None)

    def test_lipsync_failure_never_creates_fake_output(self):
        import sys
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);video=root/'input.mp4';audio=root/'audio.wav';output=root/'output.mp4'
            video.write_bytes(b'input-video');audio.write_bytes(b'input-audio')
            with patch.object(lipsync,'status',return_value={'configured':True}),patch.object(lipsync,'configuration',return_value=(root,Path(sys.executable))),patch.object(lipsync,'RUNTIME',root/'runtime'),patch.object(lipsync,'execute'):
                with self.assertRaisesRegex(RuntimeError,'không tạo output'):
                    lipsync.apply(video,audio,output)
            self.assertFalse(output.exists())

    def test_wrong_vae_or_t2v_graph_is_not_used(self):
        graph=reference_video_workflow('actual-upload.png',73,seed=5)
        self.assertEqual(graph['3']['inputs']['vae_name'],'wan2.2_vae.safetensors')
        self.assertEqual(graph['7']['class_type'],'Wan22ImageToVideoLatent')
        self.assertEqual(graph['7']['inputs']['start_image'],['6',0])
        self.assertEqual(graph['6']['inputs']['image'],'actual-upload.png')
        self.assertNotIn('EmptyHunyuanLatentVideo',[n['class_type'] for n in graph.values()])
        with self.assertRaises(ValueError): reference_video_workflow('x.png',72)

    def test_editor_conditions_on_product_and_shared_anchor(self):
        graph=reference_frame_workflow('product.png','same-person.png')
        self.assertEqual(graph['6']['inputs']['image'],'product.png')
        self.assertEqual(graph['20']['inputs']['image'],'same-person.png')
        self.assertEqual(graph['15']['inputs']['positive'],['23',0])
        self.assertEqual(graph['23']['inputs']['conditioning'],['9',0])

    def test_tampered_reference_requires_review_again(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(projects,'PROJECTS',Path(tmp)):
            pid=uuid.uuid4().hex;folder=projects.project_folder(pid);folder.mkdir()
            image=Image.new('RGB',(20,30),'red');image.save(folder/'frame-0.png')
            manifest={'plan':{'timeline':[{}]},'approved_hashes':[projects.sha(folder/'frame-0.png')]}
            Image.new('RGB',(20,30),'blue').save(folder/'frame-0.png')
            with self.assertRaisesRegex(ValueError,'duyệt khung'): projects.ensure_approved(folder,manifest)

    def test_full_reference_transport_review_and_exact_28_second_export(self):
        # Real bytes cross HTTP, real FFmpeg mux/decode; image/video MODELS are fixtures.
        with tempfile.TemporaryDirectory() as tmp:
            fixture=FixtureComfy(tmp).start()
            try:
                with patch.object(projects,'PROJECTS',Path(tmp)/'projects'),patch('localstudio.lipsync.status',return_value={'configured':False,'missing':['fixture'],'inference_verified':False}),patch.object(projects,'run',wraps=run) as commands:
                    image=Image.new('RGB',(121,221),'#fff0bb');ImageDraw.Draw(image).rectangle((10,10,30,200),fill='#ee99bb')
                    blob=io.BytesIO();image.save(blob,'PNG');blob.seek(0)
                    data={'prompt':BRIEF,'duration':30,'mode':'reference','speech':'espeak','comfy_url':fixture.url,'quality':'draft','seed':'42','auto_music':False}
                    result=projects.prepare(data,{'images':[blob]},lambda _:None)
                    pid=result['project_id'];folder,manifest=projects.read(pid)
                    self.assertTrue(result['plan']['requires_lipsync'])
                    self.assertEqual(len(result['frames']),4)
                    first_graph=fixture.graphs[0]
                    uploaded=fixture.uploads[first_graph['6']['inputs']['image']]
                    with Image.open(io.BytesIO(uploaded)) as actual:
                        self.assertEqual(actual.tobytes(),image.tobytes())
                    # Later frames receive BOTH the original product and first frame.
                    for graph in fixture.graphs[1:4]:
                        self.assertIn('20',graph)
                        self.assertEqual(graph['6']['inputs']['image'],first_graph['6']['inputs']['image'])
                    with self.assertRaisesRegex(ValueError,'duyệt khung'):
                        projects.preview(pid,lambda _:None)
                    projects.approve_frames(pid,[frame['sha256'] for frame in result['frames']])
                    for index in range(4):
                        preview=projects.preview(pid,lambda _:None,scene_index=index)
                        current=next(x for x in preview['previews'] if x['index']==index)
                        projects.approve_preview(pid,current['sha256'],index)
                    graphs_before=len(fixture.graphs)
                    with self.assertRaisesRegex(ValueError,'MuseTalk'):
                        projects.export(pid,lambda _:None)
                    self.assertEqual(len(fixture.graphs),graphs_before)
                    # Only an EXPLICIT change permits voiceover. Keep frames/previews.
                    projects.set_delivery(pid,'voiceover')
                    exported=projects.export(pid,lambda _:None)
                    path=projects.ROOT/exported['video'].lstrip('/')
                    meta=json.loads(subprocess.run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)],capture_output=True,text=True,check=True).stdout)
                    self.assertAlmostEqual(float(meta['format']['duration']),28,delta=.05)
                    self.assertEqual({x['codec_type'] for x in meta['streams']},{'video','audio'})
                    video=next(x for x in meta['streams'] if x['codec_type']=='video')
                    self.assertEqual((video['width'],video['height']),(720,1280))
                    actual=json.loads((projects.ROOT/exported['storyboard'].lstrip('/')).read_text())
                    self.assertEqual(actual['actual_delivery'],'voiceover')
                    self.assertTrue(actual['plan']['requested_lipsync'])
                    self.assertFalse(actual['plan']['burn_subtitles'])
                    rendered=' '.join(str(call.args) for call in commands.call_args_list)
                    self.assertNotIn('overlay=',rendered)
                    self.assertNotIn('subtitles=',rendered)
                    self.assertNotIn('tpad=',rendered)
                    self.assertTrue(any(node['class_type']=='Wan22ImageToVideoLatent' for g in fixture.graphs for node in g.values()))
                    self.assertEqual(len(actual['approved_hashes']),4)
                    projects.require_frame_count(path,28*24)
            finally:
                fixture.stop()


if __name__=='__main__': unittest.main()
