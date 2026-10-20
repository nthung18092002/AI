"""UI + real HTTP/media integration. Neural outputs are explicitly FIXTURES."""
import argparse
from pathlib import Path
import shutil
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
from test_reference import FixtureComfy,BRIEF
from PIL import Image,ImageDraw
from playwright.sync_api import sync_playwright,expect
from localstudio.paths import ROOT

parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=7864);args=parser.parse_args()
folder=ROOT/'work/reference-browser';folder.mkdir(parents=True,exist_ok=True)
photo=folder/'fixture-product.png';image=Image.new('RGB',(121,221),'#fff0bb');ImageDraw.Draw(image).rectangle((5,5,30,210),fill='#ff9966');image.save(photo)
errors=[]
with tempfile.TemporaryDirectory() as tmp:
    fixture=FixtureComfy(tmp).start()
    try:
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch(executable_path=shutil.which('chromium'),headless=True,args=['--no-sandbox'])
            page=browser.new_page(viewport={'width':1440,'height':1080})
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.goto(f'http://127.0.0.1:{args.port}',wait_until='networkidle')
            page.locator('[name=mode]').select_option('reference')
            page.locator('[name=product]').fill('Reference transport test')
            page.locator('[name=prompt]').fill(BRIEF)
            page.locator('summary').filter(has_text='Dùng file âm thanh').click()
            page.locator('[name=comfy_url]').fill(fixture.url)
            page.locator('[name=speech]').select_option('espeak')
            page.locator('[name=quality]').select_option('draft')
            page.locator('[name=auto_music]').uncheck()
            page.locator('#images').set_input_files(photo)
            page.locator('#submit').click()
            expect(page.locator('.frame-review')).to_have_count(4,timeout=60000)
            expect(page.locator('#reference-state')).to_contain_text('28 giây')
            expect(page.locator('#preview-scenes')).to_be_disabled()
            for item in page.locator('.frame-review').all():item.check()
            page.locator('#approve-frames').click()
            expect(page.locator('#preview-scenes')).to_be_enabled()
            page.locator('#preview-scenes').click()
            expect(page.locator('.motion-review')).to_have_count(4,timeout=120000)
            expect(page.locator('#preview-scenes')).to_be_enabled(timeout=10000)
            for item in page.locator('.motion-review').all():item.check()
            page.locator('#approve-motion').click()
            expect(page.locator('#reference-state')).to_contain_text('motion_approved')
            # A missing local lip module must block, not silently downgrade the prompt.
            expect(page.locator('#export-reference')).to_be_disabled()
            expect(page.locator('#export-requirement')).to_contain_text('khớp môi')
            page.locator('#reference-review').screenshot(path=str(folder/'review.png'))
            page.locator('#project-delivery').select_option('voiceover')
            expect(page.locator('#export-reference')).to_be_enabled()
            page.locator('#export-reference').click()
            expect(page.locator('#result')).to_be_visible(timeout=120000)
            page.wait_for_function('document.querySelector("#result video").readyState >= 1')
            video=page.locator('#result video')
            assert abs(video.evaluate('(v)=>v.duration')-28)<.05
            assert video.evaluate('(v)=>v.videoWidth')==720
            assert len(fixture.graphs)>4
            assert fixture.uploads
            assert not errors,errors
            browser.close()
    finally:fixture.stop()
print('PASS reference UI: product upload -> four conditioned frame fixtures -> review -> four I2V clip fixtures -> review -> blocked missing lip-sync -> explicit voiceover choice -> real 28s/720p mux. Neural quality NOT tested.')
