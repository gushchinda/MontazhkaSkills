"""Кейфрейм для UGC (nano-banana-pro/edit на fal).

Основной режим — restage: берём кадр-образец (референс сцены) и пересобираем его
с другим человеком из базы лиц. Свет, сеттинг, локация и композиция — как в образце.
  python3 scripts/ugc_keyframe.py restage <scene_ref.png> <face.jpg|-> <out.png> ["уточнение"] [кадр_с_персонажем.png ...]
  (face = "-" для кадров без лица: руки, телефон)

Старый режим — scene: лицо + текстовое описание сцены (хуже по реализму света).
  python3 scripts/ugc_keyframe.py scene <face.jpg> <out.png> "<описание сцены>"

FAL_KEY — из окружения. ~$0.15 за кадр.
"""
import sys, httpx, fal_client


def _dl(url, out):
    # httpx (certifi), а не urllib: у python.org-Python на маке нет системных сертификатов
    open(out, 'wb').write(httpx.get(url, timeout=300, follow_redirects=True).content)
    return out


# Правило Дмитрия 12.11.2026: «не улучшай видео, сохрани максимально реалистичное освещение и
# несовершенный свет, снято на телефон; максимально похожее изображение, но с другим лицом и
# другим персонажем; сохраняем свет, сеттинг, локацию и композицию».
RESTAGE = ("Recreate the FIRST image as closely as possible, but with a different person: use the face and identity "
           "of the man in the SECOND image (same face shape, eyes, nose, jaw, hairline, skin tone; age him to match "
           "the first image if needed), and change the character's clothing details slightly so it is a different "
           "person, not a copy. Keep EXACTLY the same lighting, imperfect natural light, exposure, white balance, "
           "setting, location, background, camera angle, framing, composition, pose and props. "
           "Do NOT enhance or beautify the image: keep it looking shot on a phone, with phone-camera softness, "
           "noise, slight motion blur and uneven light. Remove any caption or subtitle text burned into the frame "
           "(text on a phone screen stays exactly as it is). ")
RESTAGE_NOFACE = ("Recreate this image as closely as possible with a different person's hands and arms (different skin, "
                  "different hair on the arm, slightly different accessories). Keep EXACTLY the same lighting, imperfect "
                  "natural light, setting, location, background, framing and composition, and keep the phone screen "
                  "content exactly as it is and legible. Do NOT enhance or beautify: keep it looking shot on a phone. "
                  "Remove any caption or subtitle text burned into the frame that is not on the phone screen. ")

FACE_LOCK = ("Keep the EXACT same person from the first reference photo: same face shape, eyes, nose, jaw, "
             "ears, hairline and skin tone. Do not beautify him, do not make him look like a model. ")
REALISM = (" Shot on an iPhone front camera, vertical 9:16, handheld selfie framing at arm's length, natural "
           "daylight, real skin texture with visible pores, wrinkles, slight sweat shine and small imperfections, "
           "mild sensor noise, slight lens distortion, no beauty filter, no makeup, no CGI or 3D render look, "
           "no text overlays.")


def _gen(prompt, images, out):
    r = fal_client.subscribe("fal-ai/nano-banana-pro/edit", arguments={
        "prompt": prompt, "image_urls": [fal_client.upload_file(p) for p in images],
        "aspect_ratio": "9:16", "num_images": 1, "resolution": "2K"})
    return _dl(r["images"][0]["url"], out)


def restage(scene_ref, face, out, extra="", *more_refs):
    """more_refs — доп. кадры с уже сгенерированным персонажем, чтобы лицо совпадало между сценами."""
    if face == "-":
        return _gen(RESTAGE_NOFACE + extra, [scene_ref, *more_refs], out)
    return _gen(RESTAGE + extra, [scene_ref, face, *more_refs], out)


def scene(face, out, text, *refs):
    return _gen(FACE_LOCK + text + REALISM, [face, *refs], out)


if __name__ == "__main__":
    mode, *args = sys.argv[1:]
    print({"restage": restage, "scene": scene}[mode](*args))
