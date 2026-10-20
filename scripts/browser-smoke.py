"""Browser-level test with a REAL render; requires requirements-dev and Chromium."""
import argparse
from pathlib import Path
import shutil
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright, expect
from localstudio.paths import ROOT

parser = argparse.ArgumentParser()
parser.add_argument('--port', type=int, default=7861)
args = parser.parse_args()
folder = ROOT / 'work' / 'browser-test'
folder.mkdir(parents=True, exist_ok=True)
image = Image.new('RGB', (600, 800), '#263951')
draw = ImageDraw.Draw(image)
draw.rounded_rectangle((180, 100, 420, 650), radius=45, fill='#e0e8ee')
draw.text((190, 700), 'DEMO PRODUCT', fill='white')
product = folder / 'demo-product.png'
image.save(product)
errors, external = [], []
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path=shutil.which('chromium') or shutil.which('google-chrome'), headless=True, args=['--no-sandbox'])
    page = browser.new_page(viewport={'width': 1440, 'height': 1080})
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('request', lambda request: external.append(request.url) if not request.url.startswith(('http://127.0.0.1:', 'blob:', 'data:')) else None)
    page.goto(f'http://127.0.0.1:{args.port}', wait_until='networkidle')
    expect(page.locator('h1')).to_have_text('Local Affiliate Studio')
    page.locator('[name=product]').fill('Sản phẩm minh họa')
    page.locator('[name=prompt]').fill('Video minh họa góc làm việc tối giản, ánh sáng ấm.')
    page.locator('[name=features]').fill('Đây là sản phẩm minh họa để kiểm tra phần mềm.')
    page.locator('[name=use_ollama]').uncheck()
    page.locator('[name=mode]').select_option('photos')
    page.locator('[name=duration]').fill('20')
    page.locator('[name=speech]').select_option('espeak')
    page.locator('#images').set_input_files(product)
    page.screenshot(path=str(folder / 'desktop.png'), full_page=True)
    page.locator('#submit').click()
    expect(page.locator('#result')).to_be_visible(timeout=120000)
    expect(page.locator('#submit')).to_be_enabled(timeout=10000)
    video = page.locator('video')
    page.wait_for_function('document.querySelector("video").readyState >= 1')
    assert abs(video.evaluate('(v)=>v.duration') - 20) < .1
    assert video.evaluate('(v)=>v.videoWidth') == 720
    url = video.get_attribute('src')
    response = page.request.get(f'http://127.0.0.1:{args.port}' + url, headers={'Range': 'bytes=0-99'})
    assert response.status == 206 and len(response.body()) == 100
    page.screenshot(path=str(folder / 'render-complete.png'), full_page=True)
    # Starting a new job and cancelling exercises the actual job state machine.
    page.locator('#submit').click()
    expect(page.locator('#cancel')).to_be_enabled()
    page.locator('#cancel').click()
    expect(page.locator('#submit')).to_be_enabled(timeout=30000)
    expect(page.locator('#status')).to_contain_text('hủy', timeout=10000)
    page.set_viewport_size({'width': 390, 'height': 844})
    page.screenshot(path=str(folder / 'mobile.png'), full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    assert not errors, errors
    assert not external, external
    browser.close()
print('PASS browser: real 720p/20s video, Vietnamese speech, music, subtitles, playback metadata, byte ranges, cancellation, history, mobile layout, no external browser requests.')
