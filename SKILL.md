---
name: montazhka-creatives
description: Use when the editing team (Монтажка) generates ad videos — faceless-графика с цифрами и перечислениями, UGC с говорящей головой через Kling, сценарии для роликов. Triggers: «сделай faceless», «UGC ролик», «оживи лицо», «перечисление в ролике», «сценарий для креатива».
---

# Монтажка: правила генерации креативов

Правила живут в `rules/`, примеры в `bad_examples/` и `good_examples/`. Перед любой генерацией
прочитай нужное правило целиком. Правку правил вносим PR-ом в этот репозиторий, вместе с примером
«было/стало».

| Задача | Правило | Инструменты |
|---|---|---|
| Цифры, метрики, список шагов без лица | `rules/faceless-graphics.md` (опции A/B/C) | `templates/faceless_kinetic/`, `scripts/render_html.py` |
| Говорящая голова (UGC) из реального фото — основной способ | `rules/ugc-video-from-photo.md` + `rules/ugc-realistic-face.md` | `scripts/ugc_from_photo.py`, `prompts/`, `refs/` |
| Требования к лицу и свету | `rules/ugc-realistic-face.md` | `faces/`, `scripts/ugc_keyframe.py`, Kling на fal |
| Перечисления внутри UGC | `rules/faceless-graphics.md` → «Перечисления внутри UGC» | `templates/enum_overlay/` |
| Сценарий | `rules/ugc-script-format.md` (теги `[ENUM]`, `[BIG]`, `[DELTA]`, `[KEY]`) | — |

## Порядок работы
1. Сценарий в формате `ugc-script-format.md`, у каждого перечисления тег `[ENUM]`.
2. Озвучка → `mlx_whisper --word-timestamps True -f json` → тайминги слов. Вся графика садится на эти тайминги.
3. Графика рендерится из HTML (`window.render(t)`) в 1440×2560/30 fps, поверх видео — с альфой.
4. Перед сдачей — лист кадров (`ffmpeg -vf fps=1,tile=6x5`) и проверка по чек-листам правил.

## Ключи
`FAL_KEY` в окружении (fal.ai: nano-banana-pro для кейфреймов, Kling для видео). В репозиторий ключи не коммитим.
