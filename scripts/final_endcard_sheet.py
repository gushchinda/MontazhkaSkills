"""ПОСЛЕДНИЙ шаг пайплайна (обязателен): покадровая проверка эндкарты в ОПУБЛИКОВАННОМ файле.

python3 scripts/final_endcard_sheet.py <опубликованный.mp4> <кадр начала эндкарты> <outdir>

Берёт файл оттуда, куда его выложили (Drive/папка креативов), а не локальный рендер, и пишет в <outdir>:
  seam.jpg        — КАЖДЫЙ кадр от −0.5 c до +0.7 c вокруг стыка ролик→эндкарта (30 fps, без пропусков);
  endcard_10fps.jpg — вся эндкарта с шагом 0.1 c до последнего кадра;
  final.png       — последний кадр 1:1;
  final_review.md — шаблон отчёта: агент ОТКРЫВАЕТ seam.jpg, endcard_10fps.jpg и final.png и описывает каждый ключевой кадр
                    (что видно, где текст, что под ним, есть ли пересечения, скачки, мелькания).
Печатает разницу соседних кадров на стыке: скачок на первом кадре эндкарты (масштаб, сдвиг, чужой кадр) виден как выброс.
Без заполненного final_review.md задача не считается сделанной.
"""
import sys, subprocess, pathlib, numpy as np
src, n0, out = sys.argv[1], int(sys.argv[2]), pathlib.Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
total = int(subprocess.check_output(['ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v', '-show_entries',
                                     'stream=nb_read_frames', '-of', 'csv=p=0', src]).decode().strip().strip(','))
a, b = max(0, n0 - 15), min(total - 1, n0 + 21)
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-vf', f"select='between(n\\,{a}\\,{b})',scale=180:-2,tile=12x{(b - a) // 12 + 1}",
                '-vsync', '0', '-frames:v', '1', '-update', '1', str(out / 'seam.jpg')], check=True)
idx = list(range(n0, total, 3)) + [total - 1]
sel = '+'.join(f'eq(n\\,{i})' for i in idx)
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-vf', f"select='{sel}',scale=180:-2,tile=10x{len(idx) // 10 + 1}", '-vsync', '0',
                '-frames:v', '1', '-update', '1', str(out / 'endcard_10fps.jpg')], check=True)
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-vf', f"select='eq(n\\,{total - 1})'", '-vsync', '0', '-frames:v', '1',
                '-update', '1', str(out / 'final.png')], check=True)
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', src, '-vf', f"select='between(n\\,{n0 - 10}\\,{n0 + 3})',scale=270:480", '-vsync', '0',
                      '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], capture_output=True).stdout
f = np.frombuffer(raw, np.uint8).reshape(-1, 480, 270).astype(float)
d = np.abs(np.diff(f, axis=0)).mean(axis=(1, 2))
print('разница соседних кадров (последний перед стыком → стык):', ' '.join(f'{x:.1f}' for x in d))
rv = out / 'final_review.md'
if not rv.exists():
    rv.write_text(f"""# Финальная покадровая проверка эндкарты
Файл: {src}
Открыть seam.jpg (каждый кадр вокруг стыка), endcard_10fps.jpg, final.png. Описать:
- стык ролик → эндкарта (кадры {n0 - 1}…{n0 + 2}):
- растворение 0–0.4 c:
- вход иконки/заголовка/плашки/кнопки:
- финальный кадр (где текст, что под ним, пересечения):
- найденные дефекты (если нет — «нет»):
""")
print(out / 'seam.jpg', out / 'endcard_10fps.jpg', out / 'final.png', rv)
