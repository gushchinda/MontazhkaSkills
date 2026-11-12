# Формат сценария UGC

Каждая сцена — строка с таймкодом, типом кадра, репликой и тегами графики.

Типы кадра: `TALK` (говорящая голова), `PHONE` (экран приложения в руке), `GFX` (faceless-графика), `END` (эндкарта).

Теги графики:
- `[ENUM: a | b | c]` — перечисление: плашки по слову поверх кадра (опция A/B из `faceless-graphics.md`), субтитры в эти секунды скрыть;
- `[BIG: +5]` — крупная цифра «вылетает» из экрана телефона (опция C);
- `[DELTA: +5 → +2]` — цифра тикает от старого значения к новому, цвет меняется с акцента на зелёный;
- `[KEY: слово]` — слово в субтитрах акцентным цветом.

## Пример (Example App × Garmin, мужчина 58)

```
0–4    TALK   «I've worn this for six years. Love it.»                          [KEY: Garmin]
4–10   TALK   «Body Battery, VO2 max, every number you want.                    [ENUM: Body Battery | VO2 max | every number]
              But I'm 58 and I still couldn't tell you why I'm wiped out by 4 pm.» [KEY: 4 pm]
10–15  PHONE  «It took my Garmin data and showed me: plus five years on my biological age.» [BIG: +5]
15–16  TALK   «That hit.»
16–20  TALK   «Then it told me what was doing it: not enough protein,           [ENUM: ✕ Not enough protein | ✕ No strength work | ✕ Late dinners]
              no strength work, late dinners.»
20–26  PHONE  «Same Garmin. Eight weeks later I'm down to plus two.»            [DELTA: +5 → +2]
26–28  END    «Example App.»
```
