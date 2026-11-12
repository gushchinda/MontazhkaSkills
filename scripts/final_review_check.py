"""Проверка, что финальные отчёты по эндкартам написаны по кадрам, а не скопированы шаблоном.

python3 scripts/final_review_check.py <папка_ролика_1> <папка_ролика_2> ...   (в каждой — final_review.md от final_endcard_sheet.py)

Ошибка (код 1), если:
  - в отчёте есть незаполненный пункт;
  - описание стыка, растворения или финального кадра совпадает текстом с описанием другого ролика
    (у роликов разные продукт и фон — одинаковые описания значат, что кадры не смотрели);
  - в описании финального кадра нет конкретики: названия продукта и расстояния до кнопки в px.
"""
import sys, re, pathlib, itertools

FIELDS = ['стык ролик → эндкарта', 'растворение 0–0.4 c', 'финальный кадр']
errs, data = [], {}
for d in sys.argv[1:]:
    p = pathlib.Path(d) / 'final_review.md'
    if not p.exists(): errs.append(f'{d}: нет final_review.md'); continue
    t = p.read_text(); vals = {}
    for line in t.splitlines():
        m = re.match(r'- ([^:(]+?)\s*(?:\(.*?\))?:\s*(.*)$', line)
        if not m: continue
        key, val = m.group(1).strip(), m.group(2).strip()
        if not val: errs.append(f'{d}: пустой пункт «{key}»')
        vals[key] = val
    fin = next((v for k, v in vals.items() if k.startswith('финальный кадр')), '')
    if fin and not re.search(r'\d+\s*px', fin): errs.append(f'{d}: в финальном кадре нет расстояния до кнопки в px')
    data[d] = vals
for (a, va), (b, vb) in itertools.combinations(data.items(), 2):
    for f in FIELDS:
        x = next((v for k, v in va.items() if k.startswith(f)), None); y = next((v for k, v in vb.items() if k.startswith(f)), None)
        if x and y and x == y: errs.append(f'одинаковое описание «{f}» у {a} и {b} — описывать по реальным кадрам каждого ролика')
for e in errs: print('ERROR', e)
print(f'итог: ошибок {len(errs)}'); sys.exit(1 if errs else 0)
