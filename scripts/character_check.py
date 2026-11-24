"""Проверка «один персонаж на весь ролик» (rules/character-continuity.md).

python3 scripts/character_check.py <video.mp4> [<video2.mp4> ...] [--out check/cast] [--max 18] [--jobs 4]

Для каждого ролика берёт по кадру из каждой сцены (смены плана по scene-detect + страховочный кадр раз в 2.5 c),
и кладёт в <out>/:
  <ролик>.jpg  — лист сцен по порядку, слева направо и сверху вниз (6 в ряд);
  <ролик>.txt  — таймкоды кадров листа (номер плитки → секунда).
И общий index.jpg — по строке на ролик (до 10 сцен), чтобы пробежать пачку глазами за минуту.

Скрипт ничего не решает сам: смотреть глазами по чек-листу правила. Ключевое место — переход
хук/говорящая голова → скринкаст/экран приложения: фото, аватар, примерка, «до/после», отражение в зеркале
на экране должны показывать того же человека, что и в хуке (пол, возрастная группа, цвет кожи, причёска, одежда).
"""
import argparse, pathlib, re, subprocess, tempfile
from concurrent.futures import ThreadPoolExecutor

ap = argparse.ArgumentParser()
ap.add_argument('videos', nargs='+'); ap.add_argument('--out', default='check/cast')
ap.add_argument('--max', type=int, default=18); ap.add_argument('--jobs', type=int, default=4)
ap.add_argument('--thr', type=float, default=0.28, help='порог scene-detect')
a = ap.parse_args()
out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)


def dur(v):
    return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', v]))


def scene_times(v, d):
    r = subprocess.run(['ffmpeg', '-v', 'info', '-i', v, '-vf', f"scale=160:-2,select='gt(scene,{a.thr})',showinfo",
                        '-f', 'null', '-'], capture_output=True, text=True).stderr
    cuts = [float(x) for x in re.findall(r'pts_time:([0-9.]+)', r)]
    ts, prev = [0.4], 0.0
    for c in cuts + [d]:                       # середина каждой сцены
        if c - prev > 0.5: ts.append((prev + c) / 2)
        prev = c
    t = 2.5                                    # страховка на длинные планы без склеек
    while t < d - 0.3:
        if all(abs(t - x) > 1.2 for x in ts): ts.append(t)
        t += 2.5
    ts = sorted(set(round(x, 2) for x in ts if x < d - 0.1))
    if len(ts) > a.max:                        # прореживаем равномерно, первая сцена (хук) остаётся всегда
        step = len(ts) / a.max; ts = [ts[int(i * step)] for i in range(a.max)]
    return ts


def one(v):
    v = str(v); name = pathlib.Path(v).stem; d = dur(v); ts = scene_times(v, d)
    tmp = pathlib.Path(tempfile.mkdtemp())
    for i, t in enumerate(ts):
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(t), '-i', v, '-frames:v', '1',
                        '-vf', 'scale=240:426:force_original_aspect_ratio=decrease,pad=240:426:(ow-iw)/2:(oh-ih)/2',
                        str(tmp / f'f{i:03d}.png')], check=True)
    rows = (len(ts) + 5) // 6
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-framerate', '1', '-i', str(tmp / 'f%03d.png'),
                    '-vf', f'tile=6x{rows}:padding=4:color=white', '-frames:v', '1', '-q:v', '3', str(out / f'{name}.jpg')],
                   check=True)
    (out / f'{name}.txt').write_text('\n'.join(f'{i + 1:2d}  {t:6.2f}s' for i, t in enumerate(ts)) + '\n')
    n = min(10, len(ts)); idx = [int(i * len(ts) / n) for i in range(n)]
    row = tmp / 'row.png'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', *sum([['-i', str(tmp / f'f{i:03d}.png')] for i in idx], []),
                    '-filter_complex', ''.join(f'[{k}]' for k in range(n)) + f'hstack={n}' if n > 1 else 'null',
                    str(row)], check=True)
    return name, row, len(ts)


with ThreadPoolExecutor(a.jobs) as ex:
    res = list(ex.map(one, a.videos))
for name, _, n in res:
    print(f'{name}: {n} сцен → {out / (name + ".jpg")}')
w = max(int(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'stream=width', '-of', 'csv=p=0', str(r)]))
        for _, r, _ in res)
ins = sum([['-i', str(r)] for _, r, _ in res], [])
pads = ''.join(f'[{i}]pad={w}:426:0:0:white[p{i}];' for i in range(len(res)))
subprocess.run(['ffmpeg', '-v', 'error', '-y', *ins, '-filter_complex',
                pads + ''.join(f'[p{i}]' for i in range(len(res))) + f'vstack={len(res)}' if len(res) > 1 else 'null',
                '-q:v', '4', str(out / 'index.jpg')], check=True)
print('index:', out / 'index.jpg')
