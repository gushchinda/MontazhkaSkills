---
name: montazhka-creatives
description: Use when the editing team (Монтажка) generates ad videos — faceless-графика с цифрами и перечислениями, UGC с говорящей головой через Kling, сценарии для роликов. Triggers: «сделай faceless», «UGC ролик», «оживи лицо», «перечисление в ролике», «сценарий для креатива».
---

# Монтажка: правила генерации креативов

Скилл универсальный: правила (`rules/`), шаблоны (`templates/`), скрипты (`scripts/`) и промпты (`prompts/`)
не знают про конкретный продукт. Всё продуктовое (бренд, цвета, персона, предмет в кадре, экраны приложения,
сценарий, тайминги, монтаж) лежит в `projects/<проект>/`. Новый продукт = новая папка по образцу `projects/longy/`.
Примеры роликов — в `bad_examples/` и `good_examples/`. Перед любой генерацией
прочитай нужное правило целиком. Правку правил вносим PR-ом в этот репозиторий, вместе с примером
«было/стало».

| Задача | Правило | Инструменты |
|---|---|---|
| Цифры, метрики, список шагов без лица | `rules/faceless-graphics.md` (опции A/B/C) | `templates/faceless_kinetic/` + `projects/<проект>/faceless.json`, `scripts/render_html.py` |
| Говорящая голова (UGC) из реального фото — основной способ | `rules/ugc-video-from-photo.md` + `rules/ugc-realistic-face.md` | `scripts/ugc_from_photo.py` + `projects/<проект>/ugc.json`, `prompts/` |
| Требования к лицу и свету | `rules/ugc-realistic-face.md` | `faces/`, `scripts/ugc_keyframe.py`, Kling на fal |
| Перечисления внутри UGC | `rules/faceless-graphics.md` → «Перечисления внутри UGC» | `templates/enum_overlay/` + `projects/<проект>/overlay.json` |
| Сценарий | `rules/ugc-script-format.md` (теги `[ENUM]`, `[BIG]`, `[DELTA]`, `[KEY]`) | — |

## Порядок работы
1. Сценарий в формате `ugc-script-format.md`, у каждого перечисления тег `[ENUM]`.
2. Озвучка → `mlx_whisper --word-timestamps True -f json` → тайминги слов. Вся графика садится на эти тайминги.
3. Графика рендерится из HTML (`window.render(t)`) в 1440×2560/30 fps, поверх видео — с альфой.
4. Перед сдачей — лист кадров (`ffmpeg -vf fps=1,tile=6x5`) и проверка по чек-листам правил.

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
```
