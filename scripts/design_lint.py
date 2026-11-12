"""Линтер экрана графики (rules/design-pass.md). Открывает HTML-шаблон с CFG/WORDS так же, как render_html.py,
проходит по таймлайну и проверяет каждый кадр.

python3 scripts/design_lint.py <scene.html> <words.json|-> <t0> <t1> [--cfg cfg.json] [--fps 5] [--width 1080]

Ошибки (код выхода 1):
  FONT     шрифт не из списка (Inter Tight, Inter, Manrope, Space Grotesk) или не загрузился (fallback на системный);
  SIZE     видимый текст меньше 32 px в кадре шириной 1080;
  STROKE   у текста обводка (-webkit-text-stroke) или жёсткая тень-«обводка» (blur ≤ 1 px без смещения);
  SAFE     текст в верхних 220 px или нижних 380 px кадра 1080×1920 (кроме элементов с data-lint-allow="bottom|top");
  STATIC   кадр с текстом не меняется дольше 1.5 c.
Предупреждения (код 0): LAYERS — больше 4 текстовых групп одновременно (проверь «один смысл на кадр»).
"""
import sys, json, argparse, pathlib, hashlib
from playwright.sync_api import sync_playwright

OK_FONTS = {'Inter Tight', 'Inter', 'Manrope', 'Space Grotesk'}
ap = argparse.ArgumentParser()
ap.add_argument('html'); ap.add_argument('words'); ap.add_argument('t0', type=float); ap.add_argument('t1', type=float)
ap.add_argument('--cfg'); ap.add_argument('--fps', type=float, default=5); ap.add_argument('--width', type=int, default=1080)
a = ap.parse_args()
K = a.width / 720                        # css px → px кадра
TOP, BOTTOM, H = 220 / K * (a.width / 1080), 380 / K * (a.width / 1080), 1280

PROBE = """() => {
 const fams = new Set([...document.fonts].filter(f => f.status === 'loaded').map(f => f.family.replace(/["']/g, '')));
 const out = [];
 for (const el of document.querySelectorAll('body *')) {
  const own = [...el.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent.trim()).join(' ').trim();
  if (!own) continue;
  const cs = getComputedStyle(el); if (cs.display === 'none' || cs.visibility === 'hidden') continue;
  let op = 1; for (let e = el; e && e.nodeType === 1; e = e.parentElement) op *= parseFloat(getComputedStyle(e).opacity);
  if (op < 0.05) continue;
  const r = el.getBoundingClientRect(); if (r.width < 1 || r.bottom < 0 || r.top > innerHeight || r.right < 0 || r.left > innerWidth) continue;
  const fam = cs.fontFamily.split(',')[0].replace(/["']/g, '').trim();
  const al = el.closest('[data-lint-allow]');
  out.push({t: own.slice(0, 40), fam, loaded: fams.has(fam), size: parseFloat(cs.fontSize), stroke: parseFloat(cs.webkitTextStrokeWidth || 0),
            shadow: cs.textShadow, top: r.top, bottom: r.bottom, allow: al ? al.dataset.lintAllow : ''});
 }
 return out;
}"""

words = json.load(open(a.words)) if a.words != '-' else []
for i, w in enumerate(words):
    nxt = words[i + 1]['s'] if i + 1 < len(words) else None
    w['n'] = nxt if nxt is not None and nxt - w['e'] < 0.6 else w['e'] + 0.4
errs, warns = {}, {}
def add(d, k, msg, t):
    d.setdefault((k, msg), []).append(round(t, 2))

with sync_playwright() as pw:
    b = pw.chromium.launch(); pg = b.new_page(viewport={'width': 720, 'height': 1280}, device_scale_factor=1)
    pg.add_init_script(f"window.WORDS={json.dumps(words)}")
    if a.cfg: pg.add_init_script(f"window.CFG={open(a.cfg).read()}")
    pg.goto(pathlib.Path(a.html).resolve().as_uri()); pg.wait_for_load_state('networkidle'); pg.evaluate("document.fonts.ready.then(()=>1)")
    n = int((a.t1 - a.t0) * a.fps); prev, still_from = None, None
    for i in range(n + 1):
        t = a.t0 + i / a.fps
        pg.evaluate(f"render({t})")
        items = pg.evaluate(PROBE)
        for it in items:
            if it['fam'] not in OK_FONTS or not it['loaded']:
                add(errs, 'FONT', f"«{it['t']}»: {it['fam']}{'' if it['loaded'] else ' (не загружен)'}", t)
            if it['size'] * K < 32:
                add(errs, 'SIZE', f"«{it['t']}»: {it['size'] * K:.0f}px", t)
            if it['stroke'] > 0:
                add(errs, 'STROKE', f"«{it['t']}»: -webkit-text-stroke", t)
            for sh in (it['shadow'] or '').split('), '):
                nums = [p for p in sh.replace(')', ' ').split() if p.endswith('px')]
                if len(nums) >= 3 and float(nums[2][:-2]) <= 1 and nums[0] == nums[1] == '0px':
                    add(errs, 'STROKE', f"«{it['t']}»: тень-обводка {sh}", t)
            if 'top' not in it['allow'] and it['top'] < TOP:
                add(errs, 'SAFE', f"«{it['t']}»: в верхних 220 px", t)
            if 'bottom' not in it['allow'] and it['bottom'] > H - BOTTOM:
                add(errs, 'SAFE', f"«{it['t']}»: в нижних 380 px", t)
        groups = sorted({round(it['top'] / 60) for it in items})
        if len(groups) > 4:
            add(warns, 'LAYERS', f"{len(groups)} текстовых групп", t)
        h = hashlib.md5(pg.screenshot()).hexdigest()
        if items and h == prev:
            still_from = still_from if still_from is not None else t - 1 / a.fps
            if t - still_from > 1.5:
                add(errs, 'STATIC', 'кадр с текстом стоит > 1.5 c', t)
        else:
            still_from = None
        prev = h
    b.close()

def show(d, title):
    for (k, msg), ts in sorted(d.items()):
        print(f"{title} {k:6} {msg}  [{ts[0]}…{ts[-1]} c, кадров {len(ts)}]")
show(errs, 'ERROR'); show(warns, 'WARN ')
print(f"итог: ошибок {len(errs)}, предупреждений {len(warns)}")
sys.exit(1 if errs else 0)
