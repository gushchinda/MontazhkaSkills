# Проект Example App (пример конфигурации)

Приложение биологического возраста по данным Garmin. Первый проект, на котором отлажен скилл (12.11.2026).

- `faceless.json` — пример конфига faceless-вставки (кадр результата: `good_examples/05_bioage_faceless_after.jpg`)
- `ugc.json` — UGC из реального фото: мужчина 55–58, Garmin на руке, экраны `+5`/`+2`
- `overlay.json`, `voice_words.json` — плашки и субтитры под озвучку из `bad_examples/02`
- `ugc_edit.json` — монтаж: talk1 → phone1 → talk2 → phone2 → эндкарта, блюр 1.0
- `script.md` — сценарий; `prompt_examples/` — промпты ручных экспериментов (машина 01.jpg)
- `keyframes/` — проверенные кейфреймы

Озвучка и оверлей генерируются в `work/` (не в git): `work/ugc/T1.wav`, `T2.wav`, `voice.wav`, `overlay.mov`
(`render_html.py templates/enum_overlay/overlay.html projects/example-app/voice_words.json 0 26.3 work/ugc/overlay.mov --alpha --cfg projects/example-app/overlay.json --size 1080x1920`).


`brand/app_icon_placeholder.png` и `screens/plus5.png`, `screens/plus2.png` — нейтральные заглушки для примеров.
В реальном проекте иконку берём из App Store (rules/end-card.md), экраны — настоящие скриншоты приложения.
