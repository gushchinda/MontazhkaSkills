"""Рендер HTML-сцены с window.render(t) в mp4 (без звука).

python3 scripts/render_html.py scene.html words.json t0 t1 out.mp4 [--fps 30] [--size 1440x2560] [--preview 5.6,7.5]

words.json: [{"w":"word","s":start,"e":end}] — слова озвучки во времени ролика (whisper word timestamps);
сцена получает их в window.WORDS. --preview вместо видео пишет PNG кадров out_<t>.png.
"""
import sys, json, subprocess, pathlib, tempfile, argparse
from playwright.sync_api import sync_playwright

ap = argparse.ArgumentParser()
ap.add_argument('html'); ap.add_argument('words'); ap.add_argument('t0', type=float); ap.add_argument('t1', type=float); ap.add_argument('out')
ap.add_argument('--fps', type=int, default=30); ap.add_argument('--size', default='1440x2560'); ap.add_argument('--preview')
ap.add_argument('--alpha', action='store_true', help='прозрачный фон -> .mov ProRes 4444 для оверлея')
ap.add_argument('--cfg', help='JSON-файл -> window.CFG (параметры шаблона)')
a = ap.parse_args()
W_, H_ = map(int, a.size.split('x')); scale = W_ / 720

words = json.load(open(a.words)) if a.words != "-" else []
for i, w in enumerate(words):  # n = до какого момента слово «горит» в субтитре
    nxt = words[i + 1]['s'] if i + 1 < len(words) else None
    w['n'] = nxt if nxt is not None and nxt - w['e'] < 0.6 else w['e'] + 0.4

with sync_playwright() as pw:
    b = pw.chromium.launch()
    pg = b.new_page(viewport={'width': 720, 'height': 1280}, device_scale_factor=scale)
    pg.add_init_script(f"window.WORDS={json.dumps(words)}")
    if a.cfg: pg.add_init_script(f"window.CFG={open(a.cfg).read()}")
    pg.goto(pathlib.Path(a.html).resolve().as_uri()); pg.wait_for_load_state('networkidle')
    pg.evaluate("document.fonts.ready.then(()=>1)")
    if a.preview:
        for t in map(float, a.preview.split(',')):
            pg.evaluate(f"render({t})"); pg.screenshot(path=f"{a.out}_{t:05.2f}.png", omit_background=a.alpha)
        sys.exit()
    d = tempfile.mkdtemp(); n = round((a.t1 - a.t0) * a.fps)
    for i in range(n):
        pg.evaluate(f"render({a.t0 + i / a.fps})"); pg.screenshot(path=f"{d}/f{i:05d}.png", omit_background=a.alpha)
    b.close()
enc = (['-c:v', 'prores_ks', '-profile:v', '4444', '-pix_fmt', 'yuva444p10le'] if a.alpha
       else ['-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '16', '-preset', 'medium'])
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-framerate', str(a.fps), '-i', f'{d}/f%05d.png', *enc, a.out], check=True)
print(a.out, n, 'frames')
