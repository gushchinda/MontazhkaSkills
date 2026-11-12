"""Кейфрейм для UGC: реальное фото лица -> кадр сцены с тем же человеком (nano-banana-pro/edit на fal).

python3 scripts/ugc_keyframe.py <face.jpg> <out.png> "<описание сцены>" [доп. референс.jpg ...]
FAL_KEY — из окружения. ~$0.15 за кадр.
"""
import sys, urllib.request, fal_client

FACE_LOCK = ("Keep the EXACT same person from the first reference photo: same face shape, eyes, nose, jaw, "
             "ears, hairline and skin tone. Do not beautify him, do not make him look like a model. ")
REALISM = (" Shot on an iPhone front camera, vertical 9:16, handheld selfie framing at arm's length, natural "
           "daylight, real skin texture with visible pores, wrinkles, slight sweat shine and small imperfections, "
           "mild sensor noise, slight lens distortion, no beauty filter, no makeup, no CGI or 3D render look, "
           "no text overlays.")


def keyframe(face, out, scene, *refs):
    urls = [fal_client.upload_file(p) for p in (face, *refs)]
    r = fal_client.subscribe("fal-ai/nano-banana-pro/edit", arguments={
        "prompt": FACE_LOCK + scene + REALISM, "image_urls": urls,
        "aspect_ratio": "9:16", "num_images": 1, "resolution": "2K"})
    urllib.request.urlretrieve(r["images"][0]["url"], out)
    return out


if __name__ == "__main__":
    print(keyframe(*sys.argv[1:]))
