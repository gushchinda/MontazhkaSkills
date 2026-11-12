---
name: montazhka-creatives
description: Use when the editing team (Монтажка) generates ad videos — faceless-графика с цифрами и перечислениями, UGC с говорящей головой через Kling, сценарии для роликов. Triggers: «сделай faceless», «UGC ролик», «оживи лицо», «перечисление в ролике», «сценарий для креатива».
---

# Монтажка: правила генерации креативов

Скилл универсальный: правила (`rules/`), шаблоны (`templates/`), скрипты (`scripts/`) и промпты (`prompts/`)
не знают про конкретный продукт. Всё продуктовое (бренд, цвета, персона, предмет в кадре, экраны приложения,
сценарий, тайминги, монтаж) лежит в `projects/<проект>/`. Новый продукт = новая папка по образцу `projects/example-app/`.
Примеры роликов — в `bad_examples/` и `good_examples/`. Перед любой генерацией
прочитай нужное правило целиком. Правку правил вносим PR-ом в этот репозиторий, вместе с примером
«было/стало».

| Задача | Правило | Инструменты |
|---|---|---|
| Цифры, метрики, список шагов без лица | `rules/faceless-graphics.md` (опции A/B/C) | `templates/faceless_kinetic/` + `projects/<проект>/faceless.json`, `scripts/render_html.py` |
| Говорящая голова (UGC) из реального фото — основной способ | `rules/ugc-video-from-photo.md` + `rules/ugc-realistic-face.md` | `scripts/ugc_from_photo.py` + `projects/<проект>/ugc.json`, `prompts/` |
| Требования к лицу и свету | `rules/ugc-realistic-face.md` | `faces/`, `scripts/ugc_keyframe.py`, Kling на fal |
| Перечисления внутри UGC | `rules/faceless-graphics.md` → «Перечисления внутри UGC» | `templates/enum_overlay/` + `projects/<проект>/overlay.json` |
| Дизайн каждого экрана графики (бриф, превью, линтер) | `rules/design-pass.md` | `scripts/design_lint.py`, `scripts/text_guard.py` |
| Эндкарта (иконка из App Store, шрифты, без обводки) | `rules/end-card.md` | `templates/end_card/` + `projects/<проект>/brand/app_icon_1024.png` |
| Проверка эндкарты и ворота перед выгрузкой | `rules/end-card.md` → «Ворота перед выгрузкой» | `scripts/endcard_check.py`, `scripts/endcard_review.py`, `scripts/release_gate.py` |
| Финальная проверка склеек | `rules/ugc-video-from-photo.md` → «Финальная проверка склеек» | `scripts/cut_check.py` |
| Проверка на нейрослоп после генерации | `rules/ugc-video-from-photo.md`, шаг 10 | `scripts/slop_check.py` |
| Сценарий | `rules/ugc-script-format.md` (теги `[ENUM]`, `[BIG]`, `[DELTA]`, `[KEY]`) | — |

## Общие требования к любой графике (faceless, плашки, субтитры, эндкарта)
- Шрифты только несистемные: Inter Tight / Inter (по умолчанию), Manrope, Space Grotesk. SF, Arial и Helvetica запрещены.
- Антиалиасинг: рендер из HTML в 1440×2560 (×2), `crf ≤ 18`, проверка кропом ×2. Никаких stroke и белых обводок у текста.
- Иконка бренда — оригинал из App Store, скругление 22.37 %, без обводки (`rules/end-card.md`).
- Faceless-инфографика — `rules/faceless-graphics.md`: крупные цифры, появление по словам, один текстовый слой, зерно.
- Каждый экран графики проходит дизайн-шаг `rules/design-pass.md`: бриф, 3 превью, `scripts/design_lint.py`, рубрика.
- Текст на видео только из HTML (`render_html.py`). ffmpeg drawtext, subtitles и PIL-текст запрещены (`scripts/text_guard.py`).

## Порядок работы
1. Сценарий в формате `ugc-script-format.md`, у каждого перечисления тег `[ENUM]`.
2. Озвучка → `mlx_whisper --word-timestamps True -f json` → тайминги слов. Вся графика садится на эти тайминги.
3. На каждый экран графики — дизайн-шаг `rules/design-pass.md` (бриф → 3 превью → `design_lint.py` → рубрика), затем
   рендер из HTML (`window.render(t)`) в 1440×2560/30 fps, поверх видео — с альфой.
4. Каждый сгенерированный клип — `scripts/slop_check.py` и просмотр листов глазами (нейрослоп), до сборки.
5. Эндкарта — по `rules/end-card.md` (оригинальная иконка из стора, Inter Tight/Inter, без обводок).
6. Выгрузка ролика — только через `scripts/release_gate.py` (ворота: cut_check, endcard_check, design_lint и глазная
   оценка эндкарты ≥ 4 по рубрике из `scripts/endcard_review.py`), отдельно для каждого ролика.
7. Перед сдачей — `scripts/cut_check.py` (склейки, вспышки, стоп-кадры, щелчки), лист кадров (`ffmpeg -vf fps=1,tile=6x5`)
   и проверка по чек-листам правил. Склейки — по номеру кадра, не по секундам.

## Ключи
`FAL_KEY` в окружении (fal.ai: nano-banana-pro для кейфреймов, Kling для видео). В репозиторий ключи не коммитим.

## Новый проект
```
projects/<проект>/
  faceless.json     # бренд, accent/good, тексты и цифры сцен, тайминги (templates/faceless_kinetic)
  ugc.json          # persona, prop, gesture_a/b, screens, talk, edit_template (scripts/ugc_from_photo.py)
  overlay.json      # плашки ENUM/BIG/DELTA и keys субтитров (templates/enum_overlay)
  ugc_edit.json     # порядок клипов, блюр, эндкарта (scripts/ugc_build.py)
  script.md         # сценарий в формате rules/ugc-script-format.md
  screens/          # скрины приложения для кадров с телефоном
  brand/app_icon_1024.png  # иконка из App Store (rules/end-card.md)
```
