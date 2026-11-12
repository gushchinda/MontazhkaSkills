"""Оживление кейфрейма через Kling на fal.

Говорящая голова (липсинк по аудио):
  python3 scripts/ugc_kling.py avatar <keyframe.png> <line.wav> <out.mp4> ["доп. промпт"]
B-roll без речи (5 или 10 c):
  python3 scripts/ugc_kling.py i2v <keyframe.png> <out.mp4> "<что происходит в кадре>" [5|10]

FAL_KEY — из окружения. Оплата посекундная, актуальные цены на fal.ai/pricing.
"""
import sys, httpx, fal_client


def _dl(url, out):
    # httpx (certifi), а не urllib: у python.org-Python на маке нет системных сертификатов
    open(out, 'wb').write(httpx.get(url, timeout=300, follow_redirects=True).content)
    return out

AVATAR_PROMPT = ("Natural UGC selfie video, he talks to the camera like to a friend, small natural head movements, "
                 "blinks, slight handheld camera shake, realistic skin, no exaggerated mouth movement.")
I2V_NEG = "cgi, 3d render, plastic skin, morphing hands, extra fingers, text, watermark, blur"


def _get(res, out):
    return _dl(res["video"]["url"], out)


def avatar(img, audio, out, extra=""):
    r = fal_client.subscribe("fal-ai/kling-video/ai-avatar/v2/pro", arguments={
        "image_url": fal_client.upload_file(img), "audio_url": fal_client.upload_file(audio),
        "prompt": AVATAR_PROMPT + " " + extra})
    return _get(r, out)


def i2v(img, out, prompt, dur="5"):
    r = fal_client.subscribe("fal-ai/kling-video/v2.5-turbo/pro/image-to-video", arguments={
        "image_url": fal_client.upload_file(img), "prompt": prompt, "duration": str(dur),
        "negative_prompt": I2V_NEG, "cfg_scale": 0.5})
    return _get(r, out)


if __name__ == "__main__":
    mode, *args = sys.argv[1:]
    print({"avatar": avatar, "i2v": i2v}[mode](*args))
