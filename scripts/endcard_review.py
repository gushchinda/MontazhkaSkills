"""Лист кадров эндкарты для глазной проверки (rules/end-card.md → «Ворота перед выгрузкой»).

python3 scripts/endcard_review.py <final.mp4> <начало эндкарты, номер кадра> <outdir>

Пишет в <outdir>:
  endcard_sheet.jpg  — последний кадр ролика перед эндкартой, 3 кадра растворения (+2/+6/+10 кадров),
                       моменты входа элементов (0.5 / 0.8 / 1.1 c), финальный кадр — в одну полосу;
  endcard_final.png  — финальный кадр 1:1 (полное разрешение, без уменьшения);
  endcard_review.md  — шаблон оценок по рубрике (если его ещё нет). Агент ОТКРЫВАЕТ лист и финальный кадр
                       и сам ставит оценки 1–5. Любая оценка < 4 — переделка. Без файла с оценками
                       scripts/release_gate.py ролик не выпустит.
"""
import sys, subprocess, pathlib
src, n0, out = sys.argv[1], int(sys.argv[2]), pathlib.Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
fps = 30
total = int(subprocess.check_output(['ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v', '-show_entries',
                                     'stream=nb_read_frames', '-of', 'csv=p=0', src]).decode().strip().strip(','))
idx = [n0 - 1, n0 + 2, n0 + 6, n0 + 10, n0 + int(.5 * fps), n0 + int(.8 * fps), n0 + int(1.1 * fps), total - 1]
idx = [min(max(0, i), total - 1) for i in idx]
sel = '+'.join(f'eq(n\\,{i})' for i in idx)
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-vf', f"select='{sel}',scale=270:-2,tile={len(idx)}x1", '-vsync', '0',
                '-frames:v', '1', '-update', '1', str(out / 'endcard_sheet.jpg')], check=True)
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-vf', f"select='eq(n\\,{total - 1})'", '-vsync', '0', '-frames:v', '1',
                '-update', '1', str(out / 'endcard_final.png')], check=True)
rv = out / 'endcard_review.md'
if not rv.exists():
    rv.write_text("""# Глазная проверка эндкарты
Ролик: {src}
Открыть endcard_sheet.jpg и endcard_final.png, сравнить с good_examples/07–08. Оценки 1–5, всё должно быть ≥ 4.

читаемость текста на фоне:
чистый фон (нет чужого текста/графики):
нет пересечений продукта с текстом/плашками/кнопкой:
иерархия и шкала шрифтов:
выравнивание, отступы, безопасные зоны:
плавный переход без вспышек:
коммерческий вид:
комментарий:
""".format(src=src))
print(out / 'endcard_sheet.jpg', out / 'endcard_final.png', rv)
