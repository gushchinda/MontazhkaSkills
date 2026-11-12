"""Проверка склеек готового ролика (финальная проверка, rules/ugc-video-from-photo.md и rules/end-card.md).

python3 scripts/cut_check.py <final.mp4> [<final2.mp4> ...] [--ref <оригинал.mp4>]
  --ref: щелчок, который есть и в оригинале в ту же секунду (звук взят из оригинала целиком), не считается ошибкой.

Ошибки (код выхода 1):
  FLASH   «вспышка»: кусок 1–6 кадров (< 0.25 c) резко отличается от соседей — между двумя склейками подряд.
          Типичная причина: точка склейки округлена вверх на кадр, и в ролик попал кадр из оригинала
          (BIOLOGICAL AGE_08_v2, 12.11.2026: кадр старой эндкарты перед новой).
  FREEZE  стоп-кадр перед склейкой: 6+ полностью одинаковых кадров, кончающихся в пределах 0.5 c до склейки
          (клип короче отрезка и добит последним кадром). Спокойная графика с «дышащим» фоном сюда не попадает.
  BLACK   чёрный кадр (средняя яркость < 8).
  CLICK   щелчок в звуке на склейке: скачок отсчёта ≥ 10× медианы в ±10 мс от склейки.
Список склеек печатается всегда — сверь его с монтажным планом.
"""
import sys, subprocess, argparse, numpy as np

ap = argparse.ArgumentParser(); ap.add_argument('videos', nargs='+'); ap.add_argument('--fps', type=float, default=30); ap.add_argument('--ref')
a = ap.parse_args()
bad_total = 0
for v in a.videos:
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', v, '-vf', 'scale=90:160', '-f', 'rawvideo', '-pix_fmt', 'gray', '-'],
                         capture_output=True).stdout
    f = np.frombuffer(raw, np.uint8).reshape(-1, 160, 90).astype(np.float32)
    d = np.abs(np.diff(f, axis=0)).mean(axis=(1, 2))           # d[i] = разница кадров i и i+1
    thr = max(25.0, 6 * float(np.median(d)))
    cuts = [i + 1 for i, x in enumerate(d) if x > thr]           # индекс первого кадра после склейки
    errs = []
    flashes = set()
    for c1, c2 in zip(cuts, cuts[1:]):
        if c2 - c1 <= 6: flashes.add((c1, c2))
    # вторая, «тихая» склейка сразу после большой: кадр-другой из оригинала на похожем фоне
    # (BIOLOGICAL AGE_10_v2: 2 кадра старой эндкарты, потом новая — скачок мал для общего порога)
    for c in cuts:
        for j in range(c, min(c + 6, len(d) - 1)):
            after = float(np.median(d[j + 1:j + 9]))
            # второй скачок ≥ 12 и в 3+ раза больше движения после него (дальше картинка «другая и спокойная»)
            if d[j] >= 12 and d[j] > 3 * max(after, 1.0): flashes.add((c, j + 1)); break
    for c1, c2 in sorted(flashes):
        errs.append(f'FLASH  {c1 / a.fps:.3f}–{c2 / a.fps:.3f} c ({c2 - c1} кадр.)')
    # стоп-кадр: побайтно одинаковые кадры в 360×640 (добивка клипа последним кадром); «дышащая» графика сюда не попадает
    raw2 = subprocess.run(['ffmpeg', '-v', 'error', '-i', v, '-vf', 'scale=360:640', '-f', 'rawvideo', '-pix_fmt', 'gray', '-'],
                          capture_output=True).stdout
    g = np.frombuffer(raw2, np.uint8).reshape(-1, 640, 360)
    same = [bool(np.array_equal(g[i], g[i + 1])) for i in range(len(g) - 1)]
    run = 0
    for i, x in enumerate(same):
        run = run + 1 if x else 0
        if run >= 5 and any(0 <= c - (i + 1) <= a.fps * .5 for c in cuts) and (i + 1 >= len(same) or not same[i + 1]):
            errs.append(f'FREEZE {(i - run + 1) / a.fps:.2f}–{(i + 1) / a.fps:.2f} c перед склейкой')
    for i, m in enumerate(f.mean(axis=(1, 2))):
        if m < 8:
            errs.append(f'BLACK  {i / a.fps:.3f} c'); break
    def clicks(src, at):
        pcm = subprocess.run(['ffmpeg', '-v', 'error', '-i', src, '-vn', '-ac', '1', '-ar', '48000', '-f', 'f32le', '-'],
                             capture_output=True).stdout
        x = np.frombuffer(pcm, np.float32)
        if not len(x): return set()
        ds = np.abs(np.diff(x)); med = float(np.median(ds)) + 1e-6; out = set()
        for c in at:
            k = int(c / a.fps * 48000); w = ds[max(0, k - 480):k + 480]
            if len(w) and w.max() > 10 * med and w.max() > 0.3: out.add(c)
        return out
    cl = clicks(v, cuts) - (clicks(a.ref, cuts) if a.ref else set())
    for c in sorted(cl): errs.append(f'CLICK  {c / a.fps:.3f} c')
    print(f'== {v}\n   склейки: ' + ', '.join(f'{c / a.fps:.2f}' for c in cuts))
    for e in errs: print('   ERROR', e)
    print('   OK' if not errs else f'   ошибок: {len(errs)}')
    bad_total += bool(errs)
sys.exit(1 if bad_total else 0)
