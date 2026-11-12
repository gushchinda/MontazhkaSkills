# Проект Longy (пример конфигурации)

Приложение биологического возраста по данным Garmin. Первый проект, на котором отлажен скилл (12.11.2026).

- `faceless.json` — faceless-вставка для `bad_examples/01` → `good_examples/01_faceless_kinetic.mp4`
- `ugc.json` — UGC из реального фото: мужчина 55–58, Garmin на руке, экраны `+5`/`+2`
- `overlay.json`, `voice_words.json` — плашки и субтитры под озвучку из `bad_examples/02`
- `ugc_edit.json` — монтаж: talk1 → phone1 → talk2 → phone2 → эндкарта, блюр 1.0
- `script.md` — сценарий; `prompt_examples/` — промпты ручных экспериментов (машина 01.jpg)
- `keyframes/` — проверенные кейфреймы; ролики — `good_examples/ugc_from_photo/longy_face01–04.mp4`

Озвучка и оверлей генерируются в `work/` (не в git): `work/ugc/T1.wav`, `T2.wav`, `voice.wav`, `overlay.mov`
(`render_html.py templates/enum_overlay/overlay.html projects/longy/voice_words.json 0 26.3 work/ugc/overlay.mov --alpha --cfg projects/longy/overlay.json --size 1080x1920`).
