"""Одна финальная проверка всей пачки после монтажа (SKILL.md → «Порядок работы», шаг 5).

python3 scripts/check_all.py <final1.mp4> [<final2.mp4> ...] [--out check] [--endcard-sec 4] [--jobs 4]

Делает за один проход, параллельно по роликам:
  1) cut_check.py по каждому ролику (склейки, вспышки, стоп-кадры, чёрные кадры, щелчки);
  2) contact.jpg — лист кадров пачки: по строке на ролик, 8 кадров равномерно по длине (смотреть глазами);
  3) seams.jpg — стык ролик→эндкарта у каждого ролика: последний кадр ролика, 1-й/6-й кадр эндкарты, финал.
     Начало эндкарты = длительность − --endcard-sec (или задать точно: final.mp4@<кадр>).
  4) for_editor.md — сигнал монтажёру по каждой ошибке: что, где, почему, лист кадров и строка для ответа
     «Всё окей» (rules/check-override.md). Ошибки, на которые монтажёр ответил «Всё окей» в check_acks.txt,
     печатаются как ACK и не валят проверку.
  5) имя каждого ролика — только английский/ASCII (SKILL.md → «Имена файлов»).
Печатает короткую таблицу OK/FAIL. Ничего не блокирует и не копирует — это быстрая проверка перед отдачей.
Тяжёлые ворота (release_gate.py и т.д.) — только для выкладки заказчику.
"""
import argparse, pathlib, re, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor

SK = pathlib.Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument('videos', nargs='+'); ap.add_argument('--out', default='check')
ap.add_argument('--endcard-sec', type=float, default=4.0); ap.add_argument('--jobs', type=int, default=4)
ap.add_argument('--acks', action='append', default=[], help='файл с ответами «Всё окей» (по умолчанию check_acks.txt рядом с роликом)')
a = ap.parse_args()
out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
tmp = pathlib.Path(tempfile.mkdtemp())


def probe(v):
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_packets', '-show_entries',
                        'stream=nb_read_packets,r_frame_rate', '-of', 'csv=p=0', v], capture_output=True, text=True).stdout
    rate, n = r.strip().split(',')[:2]
    num, den = map(int, rate.split('/'))
    return int(n), num / den


def one(i_spec):
    i, spec = i_spec
    v, _, ef = spec.partition('@')
    n, fps = probe(v)
    e = int(ef) if ef else n - round(a.endcard_sec * fps)
    cc = subprocess.run([sys.executable, str(SK / 'cut_check.py'), v, '--signals', str(out / 'signals'),
                         *sum([['--acks', x] for x in a.acks], [])], capture_output=True, text=True)
    lines = [l.strip() for l in cc.stdout.splitlines()]
    errs = [l for l in lines if l.startswith('ERROR')]
    acks = [l for l in lines if l.startswith('ACK')]
    sig = [l for l in lines if l.startswith(('ERROR', 'СИГНАЛ', 'кадры', 'если так задумано'))]
    picks = [round(k * (n - 1) / 7) for k in range(8)]
    sel = '+'.join(f'eq(n\\,{k})' for k in picks)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', v, '-vf', f"select='{sel}',scale=135:-2,tile=8x1", '-vsync', '0',
                    '-frames:v', '1', tmp / f'c{i:03d}.png'])
    seam = [max(e - 1, 0), e, min(e + 5, n - 1), n - 1]
    sel = '+'.join(f'eq(n\\,{k})' for k in seam)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', v, '-vf', f"select='{sel}',scale=135:-2,tile=4x1", '-vsync', '0',
                    '-frames:v', '1', tmp / f's{i:03d}.png'])
    return i, v, cc.returncode, errs, acks, sig


with ThreadPoolExecutor(a.jobs) as ex:
    res = sorted(ex.map(one, enumerate(a.videos)))
for kind, name in (('c', 'contact.jpg'), ('s', 'seams.jpg')):
    ins = [x for i, *_ in res for x in ('-i', str(tmp / f'{kind}{i:03d}.png'))]
    k = len(res)
    fc = f"vstack=inputs={k}" if k > 1 else "null"
    subprocess.run(['ffmpeg', '-v', 'error', '-y', *ins, '-filter_complex', fc, '-frames:v', '1', '-q:v', '3', out / name])
bad = 0
md = ['# Сигнал монтажёру', '',
      'По каждой ошибке: посмотри лист кадров. Если это брак — поправь и пришли ролик заново.',
      'Если так задумано — добавь готовую строку в `check_acks.txt` (рядом с роликом), вписав себя, дату и почему.',
      'Без строки «Всё окей» ошибка остаётся FAIL. Правило: rules/check-override.md', '']
NAME_OK = re.compile(r'^[A-Za-z0-9._-]+$')  # SKILL.md → «Имена файлов»: только английский/ASCII
for i, v, rc, errs, acks, sig in res:
    nm = pathlib.Path(v.split('@')[0]).name
    if not NAME_OK.match(nm):
        e = f'NAME: имя файла не на английском/ASCII: {nm!r} — переименовать (SKILL.md → «Имена файлов»)'
        rc = rc or 1; errs = errs + [e]; sig = sig + [e]
    bad += rc != 0
    name = pathlib.Path(v.split('@')[0]).name
    print(f"{'OK  ' if rc == 0 else 'FAIL'} {name}" + (f"  {' | '.join(errs)}" if errs else '')
          + (f"  (подтверждено монтажёром: {len(acks)})" if acks else ''))
    if sig or acks:
        md += [f'## {name}', ''] + [f'- {l}' for l in sig] + [f'- {l}' for l in acks] + ['']
(out / 'for_editor.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
print(f"итог: {len(res) - bad}/{len(res)} OK · листы: {out / 'contact.jpg'}, {out / 'seams.jpg'} (открыть и посмотреть)"
      + (f" · сигнал монтажёру: {out / 'for_editor.md'}" if bad else ''))
sys.exit(1 if bad else 0)
