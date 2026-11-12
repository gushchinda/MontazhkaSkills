"""Проверка сгенерированного клипа на нейрослоп (правило: rules/ugc-video-from-photo.md, шаг «Проверка на нейрослоп»).

python3 scripts/slop_check.py <clip.mp4> [<clip2.mp4> ...] [--out <dir>] [--fps 5]

Для каждого клипа пишет в <out>/<имя>/:
  sheet.jpg      — все кадры с шагом 1/fps, плиткой 6 в ряд (общий вид: морфинг, мерцание, деформация лица);
  crop_<зона>.jpg — те же кадры, но кропы зон ×2: top (зеркала, потолок, окна), mid (лицо), low (руки, часы, экран),
                   left/right (края кадра, где чаще всего появляются «иероглифы» и плывущие предметы);
  flicker.txt    — кадры со скачком разницы (подозрение на мерцание/смену предмета).
Смотреть глазами ВСЕ листы. Что искать — в правиле. Скрипт ничего не решает сам.
"""
import sys, subprocess, pathlib, argparse, numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('clips', nargs='+'); ap.add_argument('--out', default='work/slop'); ap.add_argument('--fps', type=float, default=5)
a = ap.parse_args()
ZONES = {'top': (0, 0, 1, .34), 'mid': (.15, .2, .7, .4), 'low': (0, .55, 1, .45), 'left': (0, .15, .4, .7), 'right': (.6, .15, .4, .7)}

for clip in a.clips:
    q = pathlib.Path(clip).resolve(); o = pathlib.Path(a.out) / f'{q.parent.name}_{q.stem}'; o.mkdir(parents=True, exist_ok=True)
    dur = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', clip]))
    rows = max(1, int(np.ceil(dur * a.fps / 6)))
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', clip, '-vf', f'fps={a.fps},scale=300:-2,tile=6x{rows}', '-frames:v', '1',
                    str(o / 'sheet.jpg')], check=True)
    for z, (x, y, w, h) in ZONES.items():
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', clip, '-vf',
                        f'fps={a.fps},crop=iw*{w}:ih*{h}:iw*{x}:ih*{y},scale=420:-2,tile=6x{rows}', '-frames:v', '1',
                        str(o / f'crop_{z}.jpg')], check=True)
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', clip, '-vf', 'scale=90:160', '-f', 'rawvideo', '-pix_fmt', 'gray', '-'],
                         capture_output=True).stdout
    f = np.frombuffer(raw, np.uint8).reshape(-1, 160, 90).astype(float)
    d = np.abs(np.diff(f, axis=0)).mean(axis=(1, 2)); thr = d.mean() + 4 * d.std()
    spikes = [f'{(i + 1) / 30:.2f}s diff={v:.1f}' for i, v in enumerate(d) if v > thr]
    (o / 'flicker.txt').write_text('\n'.join(spikes) or 'нет скачков')
    print(o, f'{len(spikes)} скачков')
