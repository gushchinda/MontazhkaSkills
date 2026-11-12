"""Проверка эндкарты (rules/end-card.md, обязательна в финальной проверке).

python3 scripts/endcard_check.py <end_card.html> <cfg.json> <t0> <t1> [--width 1080] [--out dir]

Рендерит шаблон в браузере слоями (полный кадр / без нашего текста / только фон) и проверяет:
  BG_TEXT  на фоне (без нашего слоя) OCR находит текст — фон «грязный» (вшитые титры, старые надписи);
  GHOST    во время перехода из ролика наш текст уже виден, а в растворяющемся кадре есть текст — двойная экспозиция
           (BIOLOGICAL AGE_02_v2, 12.11.2026: «Same WHOOP.» просвечивал под «Know your real biological age»);
  CONTRAST контраст WCAG текста к реальному фону под ним (90-й перцентиль худших пикселей) < 4.5 (мелкий) / 3.0 (≥ 36 px);
  BUSY     под заголовком пёстрый фон (плотность контуров выше порога) — нужна подложка или сдвиг продукта;
  OPACITY  за 1 c до конца не все элементы полностью видимы.
Код выхода 1 при любой ошибке. В --out кладутся кадры, по которым проверял.
"""
import sys, json, argparse, pathlib, subprocess, tempfile, re, io
import numpy as np
from PIL import Image, ImageFilter
from playwright.sync_api import sync_playwright

ap = argparse.ArgumentParser()
ap.add_argument('html'); ap.add_argument('cfg'); ap.add_argument('t0', type=float); ap.add_argument('t1', type=float)
ap.add_argument('--width', type=int, default=1080); ap.add_argument('--out'); ap.add_argument('--debug', action='store_true')
a = ap.parse_args()
DEBUG = a.debug
K = a.width / 720
TEXT = ['#head', '#sub', '#meta .chip', '#cta']
BUSY = 0.02
out = pathlib.Path(a.out) if a.out else pathlib.Path(tempfile.mkdtemp()); out.mkdir(parents=True, exist_ok=True)
errs = []

def ocr(img):
    """Слова, которые tesseract уверенно читает (≥ 3 буквы, conf ≥ 70)."""
    p = out / '_ocr.png'; img.save(p)
    r = subprocess.run(['tesseract', str(p), '-', '--psm', '11', 'tsv'], capture_output=True, text=True).stdout
    words = []
    for line in r.splitlines()[1:]:
        f = line.split('\t')
        if len(f) >= 12 and f[11].strip() and float(f[10]) >= 70 and len(re.sub(r'[^A-Za-z]', '', f[11])) >= 3:
            words.append(f[11].strip())
    return words

def lum(rgb):
    c = np.asarray(rgb, float) / 255
    c = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]

STATE = """(sel) => [...document.querySelectorAll(sel)].map(el => { let op = 1;
  for (let e = el; e && e.nodeType === 1; e = e.parentElement) op *= parseFloat(getComputedStyle(e).opacity);
  const r = el.getBoundingClientRect(), cs = getComputedStyle(el);
  return {op, x: r.left, y: r.top, w: r.width, h: r.height, color: cs.color, size: parseFloat(cs.fontSize),
          bg: cs.backgroundColor, disp: cs.display}; })"""

with sync_playwright() as pw:
    b = pw.chromium.launch(); pg = b.new_page(viewport={'width': 720, 'height': 1280}, device_scale_factor=K)
    pg.add_init_script(f"window.CFG={open(a.cfg).read()}")
    pg.goto(pathlib.Path(a.html).resolve().as_uri()); pg.wait_for_load_state('networkidle'); pg.evaluate("document.fonts.ready.then(()=>1)")
    def shot(t, hide=(), clear_text=False):
        pg.evaluate(f"render({t})")
        css = ''.join(f"{s}{{visibility:hidden!important}}" for s in hide)
        if clear_text: css += ''.join(f"{s}, {s} *{{color:transparent!important;text-shadow:none!important}}" for s in TEXT) + '#sh{display:none!important}'
        pg.evaluate(f"(c)=>{{let s=document.getElementById('_lint');if(!s){{s=document.createElement('style');s.id='_lint';document.head.appendChild(s)}};s.textContent=c}}", css)
        img = Image.open(io.BytesIO(pg.screenshot())).convert('RGB')
        pg.evaluate("document.getElementById('_lint').textContent=''")
        return img
    state = lambda sel: pg.evaluate(STATE, sel)
    D = a.t1 - a.t0
    # 1) фон без нашего слоя и без кадра ролика: текста быть не должно
    bg = shot(a.t1 - .05, hide=['#icon', '#head', '#sub', '#meta', '#cta', '#from', '#phone']); bg.save(out / 'bg_only.png')
    w = ocr(bg)
    if w: errs.append(f'BG_TEXT  на фоне читается текст: {" ".join(w[:8])}')
    # 2) двойная экспозиция при переходе
    fr_words = []
    cfg = json.load(open(a.cfg))
    if cfg.get('from'):
        fr_words = ocr(Image.open(cfg['from']).convert('RGB'))
    if fr_words:
        for i in range(1, 16):
            t = a.t0 + i / 30
            pg.evaluate(f"render({t})")
            fo = pg.evaluate("parseFloat(getComputedStyle(document.getElementById('from')).opacity)")
            txt = max([s['op'] for sel in TEXT for s in state(sel)] or [0])
            if fo > .12 and txt > .12:
                errs.append(f'GHOST    {i / 30:.2f} c от начала: кадр ролика с текстом «{" ".join(fr_words[:4])}» (непрозр. {fo:.2f}) '
                            f'просвечивает под нашим текстом (непрозр. {txt:.2f})'); break
    # 3) контраст и пестрота в финальном состоянии
    tf = a.t1 - .05
    full = shot(tf); full.save(out / 'final.png')
    under = shot(tf, clear_text=True); under.save(out / 'under_text.png')
    U = np.asarray(under); BGA = np.asarray(shot(tf, hide=['#icon', '#head', '#sub', '#meta', '#cta', '#phone']))
    for sel in TEXT:
        for s in state(sel):
            if s['op'] < .5 or s['w'] < 2: continue
            x0, y0 = int(s['x'] * K), int(s['y'] * K); x1, y1 = int((s['x'] + s['w']) * K), int((s['y'] + s['h']) * K)
            if sel in ('#cta', '#meta .chip'):   # у плашки свой фон: берём середину, без скруглённых углов
                dx, dy = int((x1 - x0) * .2), int((y1 - y0) * .25); x0, x1, y0, y1 = x0 + dx, x1 - dx, y0 + dy, y1 - dy
            reg = U[max(0, y0):y1, max(0, x0):x1].reshape(-1, 3)
            if not len(reg): continue
            tc = [int(v) for v in re.findall(r'\d+', s['color'])[:3]]
            lt = float(lum(tc)); lb = lum(reg)
            worst = np.percentile(lb, 90) if lt > .5 else np.percentile(lb, 10)
            cr = (max(lt, worst) + .05) / (min(lt, worst) + .05)
            need = 3.0 if s['size'] * K >= 36 else 4.5
            if cr < need:
                errs.append(f'CONTRAST {sel}: {cr:.1f} < {need} (текст {tuple(tc)}, фон под ним 90-й перц.)')
            if sel in ('#head', '#sub', '#meta .chip'):
                # пестрота считается по фону БЕЗ нашего слоя (подложка-скрим остаётся), зерно убираем лёгким размытием
                crop = BGA[max(0, y0):y1, max(0, x0):x1]
                L = np.asarray(Image.fromarray(crop).convert('L').filter(ImageFilter.GaussianBlur(3)), float)
                gm = np.hypot(np.diff(L, axis=1)[:-1], np.diff(L, axis=0)[:, :-1]) if L.size > 4 else np.zeros(1)
                dens = float((gm > 2.5).mean())   # доля пикселей с заметным перепадом яркости (контуры предмета, линии)
                if DEBUG: print(f'  debug busy {sel}: {dens:.3f}')
                if dens > BUSY: errs.append(f'BUSY     {sel}: под текстом пёстрый фон или продукт (контуры {dens:.1%}) — затемнить/размыть фон, сдвинуть продукт')
    # 3б) продукт в своей зоне: зазор ≥ 48 px (при 1080) до плашек и до кнопки, без пересечения с текстом
    pg.evaluate(f"render({tf})")
    box = lambda sel: pg.evaluate("(s)=>{const e=document.querySelector(s);if(!e||getComputedStyle(e).display==='none')return null;const r=e.getBoundingClientRect();return [r.left,r.top,r.right,r.bottom]}", sel)
    pc = box('#pcard') or box('#phone')
    if pc:
        GAP = 48 / K
        for sel in ['#head', '#sub', '#meta', '#cta']:
            o = box(sel)
            if not o: continue
            gap = max(o[1] - pc[3], pc[1] - o[3])     # вертикальный зазор (отрицательный — пересечение)
            if gap < GAP and not (o[2] < pc[0] or o[0] > pc[2]):
                errs.append(f'PRODUCT  продукт ближе {GAP * K:.0f} px к {sel}: зазор {gap * K:.0f} px — уменьшить продукт, не перекрывать')
    # 4) всё видно за 1 c до конца
    for i in range(0, 6):
        t = a.t1 - 1 + i * .2
        pg.evaluate(f"render({t})")
        low = [f"{sel}:{s['op']:.2f}" for sel in TEXT + ['#icon'] for s in state(sel) if s['disp'] != 'none' and s['op'] < .99]
        if low: errs.append(f'OPACITY  {t - a.t0:.2f} c: не до конца видимы {", ".join(low)}'); break
    b.close()

for e in errs: print('ERROR', e)
print(f'итог: ошибок {len(errs)} (кадры: {out})')
sys.exit(1 if errs else 0)
