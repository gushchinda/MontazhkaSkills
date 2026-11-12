"""Кейфрейм B-roll «экран приложения в руке» по референсу (кадр-образец/скрин приложения).
python3 scripts/ugc_broll_frame.py <ref.png> <out.png> "<сцена>"
Текст на экране переносится с референса; субтитры/надписи с референса убираются."""
import sys, fal_client
from ugc_keyframe import _dl
BASE = ("Use the phone screen from the reference image EXACTLY: same layout, numbers, colors and text, sharp and legible. "
        "Remove any caption or subtitle text that is not on the phone screen. ")
REAL = (" Shot on iPhone rear camera, vertical 9:16, natural light, shallow depth of field, real skin on the hand with "
        "veins and hair, realistic watch, no CGI look.")
def frame(ref, out, scene):
    r = fal_client.subscribe("fal-ai/nano-banana-pro/edit", arguments={"prompt": BASE + scene + REAL,
        "image_urls": [fal_client.upload_file(ref)], "aspect_ratio": "9:16", "num_images": 1, "resolution": "2K"})
    return _dl(r["images"][0]["url"], out)
if __name__ == "__main__":
    print(frame(*sys.argv[1:4]))
