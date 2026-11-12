"""Ворота перед выгрузкой ролика (обязательно, обойти нельзя): rules/end-card.md, SKILL.md «Порядок работы».

python3 scripts/release_gate.py <final.mp4> <dest> --review <endcard_review.md> --endcard <html> <cfg.json> <t0> <t1>
                               [--lint <html> <words|-> <t0> <t1> <cfg.json>]... [--ref <оригинал.mp4>]

Копирует final.mp4 в dest ТОЛЬКО если (и потом обязательно scripts/final_endcard_sheet.py по выложенному файлу):
  1) scripts/cut_check.py → 0;
  2) scripts/endcard_check.py для эндкарты ЭТОГО ролика → 0 (фон и продукт у каждого ролика свои);
  3) scripts/design_lint.py для каждого --lint → 0;
  4) в endcard_review.md все 7 оценок заполнены и каждая ≥ 4;
  5) шов: первый кадр эндкарты (--seam) не отличается от последнего кадра ролика (разница ≤ 5).
Иначе печатает, что не прошло, и выходит с кодом 1, ничего не копируя.
"""
import sys, re, shutil, subprocess, pathlib, argparse
SK = pathlib.Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument('final'); ap.add_argument('dest'); ap.add_argument('--review', required=True)
ap.add_argument('--endcard', nargs=4, required=True); ap.add_argument('--lint', nargs=5, action='append', default=[])
ap.add_argument('--ref'); ap.add_argument('--seam', type=int, required=True, help='номер первого кадра эндкарты')
a = ap.parse_args()
fails = []
def run(name, cmd):
    r = subprocess.run([sys.executable, *cmd], capture_output=True, text=True)
    if r.returncode: fails.append(f'{name}:\n' + (r.stdout[-800:] or r.stderr[-800:]))
run('cut_check', [str(SK / 'cut_check.py'), a.final] + (['--ref', a.ref] if a.ref else []))
h, cfg, t0, t1 = a.endcard
run('endcard_check', [str(SK / 'endcard_check.py'), h, cfg, t0, t1])
for h, w, t0, t1, cfg in a.lint:
    run(f'design_lint {pathlib.Path(h).name}', [str(SK / 'design_lint.py'), h, w, t0, t1, '--cfg', cfg])
# шов ролик→эндкарта: первый кадр эндкарты должен совпадать с последним кадром ролика (переход начинается с него)
import numpy as np
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', a.final, '-vf', f"select='between(n\\,{a.seam - 1}\\,{a.seam})',scale=270:480",
                      '-vsync', '0', '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], capture_output=True).stdout
fr = np.frombuffer(raw, np.uint8).reshape(-1, 480, 270).astype(float)
if len(fr) == 2:
    sd = float(np.abs(fr[1] - fr[0]).mean())
    if sd > 5: fails.append(f'SEAM: скачок на первом кадре эндкарты (кадр {a.seam}): разница {sd:.1f} > 5 — масштаб/сдвиг/чужой кадр')
else:
    fails.append('SEAM: не удалось прочитать кадры шва')
rv = pathlib.Path(a.review)
if not rv.exists():
    fails.append('нет файла глазной проверки (scripts/endcard_review.py)')
else:
    scores = [int(m) for m in re.findall(r':\s*([1-5])\s*$', rv.read_text(), flags=re.M)]
    if len(scores) < 7: fails.append(f'в {rv.name} заполнено {len(scores)} оценок из 7')
    elif min(scores) < 4: fails.append(f'в {rv.name} есть оценка < 4: {scores} — переделать эндкарту')
if fails:
    print('НЕ ВЫПУЩЕН', a.final); [print(' -', f) for f in fails]; sys.exit(1)
shutil.copyfile(a.final, a.dest); print('ВЫПУЩЕН', a.final, '→', a.dest)
print('ДАЛЬШЕ ОБЯЗАТЕЛЬНО: python3 scripts/final_endcard_sheet.py', repr(a.dest), a.seam, '<папка> — и посмотреть каждый кадр')
