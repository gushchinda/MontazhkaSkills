"""Сборка UGC-ролика: склейка клипов + графика с альфой поверх + общая дорожка озвучки.

python3 scripts/ugc_build.py edit.json out.mp4

edit.json:
{
  "audio": "voice.wav",                  # озвучка на весь ролик (тайминги графики считаны с неё)
  "overlay": "overlay.mov",              # ProRes 4444 из render_html.py --alpha (может быть короче ролика)
  "clips": [{"src": "talk1.mp4", "in": 0, "dur": 10.85}, ...]   # подряд, без зазоров
}
Клипы приводятся к 1080×1920 / 30 fps (cover-кроп), звук клипов отбрасывается.
У клипа можно задать "blur": 1.0 — лёгкий gblur (правило: лёгкий блюр на сгенерированных кадрах).
"""
import json, subprocess, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from text_guard import guard  # текст на видео только из HTML (rules/design-pass.md)

e = json.load(open(sys.argv[1])); out = sys.argv[2]
args, parts = [], []
for i, c in enumerate(e["clips"]):
    args += ["-ss", str(c.get("in", 0)), "-t", str(c["dur"]), "-i", c["src"]]
    parts.append(f"[{i}:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
                 f"fps=30,setsar=1,trim=duration={c['dur']},setpts=PTS-STARTPTS"
                 + (f",gblur=sigma={c['blur']}" if c.get('blur') else "") + f"[v{i}]")
n = len(e["clips"])
args += ["-i", e["overlay"], "-i", e["audio"]]
fc = ";".join(parts) + ";" + "".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1[base];" \
     f"[{n}:v]fps=30,setpts=PTS-STARTPTS[ov];[base][ov]overlay=eof_action=pass:format=auto[v]"
guard([*args, fc])
subprocess.run(["ffmpeg", "-v", "error", "-y", *args, "-filter_complex", fc, "-map", "[v]", "-map", f"{n + 1}:a",
                "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                "-shortest", "-movflags", "+faststart", out], check=True)
print(out)
