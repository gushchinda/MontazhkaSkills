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
| Один герой на весь ролик (хук = скринкаст = все сцены) | `rules/character-continuity.md` | `scripts/character_check.py` |
| Финальная проверка пачки (одна, в конце) | этот файл → «Порядок работы», шаг 5 | `scripts/check_all.py` |
| Ложное срабатывание проверки: сигнал монтажёру и ответ «Всё окей» | `rules/check-override.md` | `check/for_editor.md`, `check_acks.txt` |
| Проверка на нейрослоп после генерации | `rules/ugc-video-from-photo.md`, шаг 10 | `scripts/slop_check.py` |
| Сценарий | `rules/ugc-script-format.md` (теги `[ENUM]`, `[BIG]`, `[DELTA]`, `[KEY]`) | — |

## Общие требования к любой графике (faceless, плашки, субтитры, эндкарта)
- Шрифты только несистемные: Inter Tight / Inter (по умолчанию), Manrope, Space Grotesk. SF, Arial и Helvetica запрещены.
- Антиалиасинг: рендер из HTML в 1440×2560 (×2), `crf ≤ 18`, проверка кропом ×2. Никаких stroke и белых обводок у текста.
- Иконка бренда — оригинал из App Store, скругление 22.37 %, без обводки (`rules/end-card.md`).
- Faceless-инфографика — `rules/faceless-graphics.md`: крупные цифры, появление по словам, один текстовый слой, зерно.
- Каждый новый шаблон графики проходит дизайн-шаг `rules/design-pass.md` (один раз на шаблон, не на ролик).
- Текст на видео только из HTML (`render_html.py`). ffmpeg drawtext, subtitles и PIL-текст запрещены (`scripts/text_guard.py`).

## Порядок работы (быстрый режим, по умолчанию)
Главное правило скорости: **сначала монтаж всей пачки, проверки — один раз в самом конце**, одной командой и
параллельно. Во время монтажа ничего не проверяем по каждому ролику и не пересобираем ради промежуточных проверок.

1. Сценарий в формате `ugc-script-format.md`, у каждого перечисления тег `[ENUM]`.
2. Озвучка → whisper word timestamps (`mlx_whisper --word-timestamps True -f json` или whisper.cpp) → тайминги слов.
   Вся графика садится на эти тайминги.
3. **Дизайн-шаг — один раз на шаблон, не на ролик** (`rules/design-pass.md`): бриф и 3 превью делаем, когда
   шаблон новый или меняется. Для пачки на одном шаблоне — одно превью на первом ролике, дальше без превью.
4. Монтаж всех роликов пачки подряд (можно 2–3 параллельно). Рендер графики из HTML: оверлей с альфой — сразу
   в размере таймлайна (`--size 1080x1920`, `ugc_build.py` не масштабирует оверлей), непрозрачные слои — с `--jpeg`.
   Эндкарта — по `rules/end-card.md`.
5. **Одна финальная проверка всей пачки:** `python3 scripts/check_all.py <final1.mp4> <final2.mp4> ...`
   и `python3 scripts/character_check.py <те же ролики> --out check/cast` (один герой на весь ролик,
   `rules/character-continuity.md`: человек на экране приложения = герой хука)
   (cut_check по всем роликам параллельно + лист кадров на пачку + листы стыков ролик→эндкарта). Смотрим
   2 листа глазами, правим только то, что упало, и проверяем только исправленные ролики.
6. Нейрослоп (`scripts/slop_check.py`) — только на новых сгенерированных клипах, один раз, до монтажа; уже
   проверенные исходники повторно не гоняем.
7. Тяжёлые ворота (`scripts/release_gate.py`, `endcard_check.py`, `endcard_review.py`, `final_endcard_sheet.py`,
   `final_review.md`) — **только когда ролики выкладываем заказчику на Drive** или по прямой просьбе. Если нужен
   просто результат — отдаём после шага 5.
8. Склейки — по номеру кадра, не по секундам (`trim=end_frame`), иначе мелькает кадр старой эндкарты.
   Скринкаст режем со спокойного экрана, без хвоста прошлой анимации UI (`cut_check` → `JUMPIN`).
9. Ролик с FAIL в шаге 5 на Drive не выкладываем, даже «на посмотреть»: сначала правка, потом повторная проверка.
   Исключение одно: монтажёр получил сигнал (`check/for_editor.md`: что, где, лист кадров) и явно ответил
   «Всё окей» на эту ошибку в `check_acks.txt` (`rules/check-override.md`). Тогда ошибка идёт как ACK и ролик проходит.

### Чего не делать (съедает время)
- Не гонять cut_check / endcard_check / design_lint после каждого ролика и после каждой мелкой правки.
- Не перерендеривать оверлей ради проверок: если менялся только монтаж, собирать с готовым `overlay.mov`.
- Не делать бриф и 3 превью на каждый ролик пачки с одинаковым шаблоном.
- Не ставить в очередь больше 3 параллельных рендеров HTML: браузеры падают, и всё равно приходится пересобирать.

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
