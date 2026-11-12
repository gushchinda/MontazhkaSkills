"""UGC-ролик из одного реального фото (правило rules/ugc-video-from-photo.md).

python3 scripts/ugc_from_photo.py frames <photo.jpg> <outdir> ["подсказка по локации/кадру"]
python3 scripts/ugc_from_photo.py video  <outdir> <talk1.wav> <talk2.wav> <edit_template.json>

frames: 4 кейфрейма на базе фото (nano-banana-pro/edit), всё в той же локации и том же свете:
  kf_a   — новый человек (неузнаваемо другое лицо), поднимает руку с Garmin, говорит; лицо чуть недосвечено
  kf_b   — тот же новый человек, рука опущена, серьёзный, говорит
  kf_ph1 — рука держит телефон с экраном «+5» (refs/screen_plus5.png)
  kf_ph2 — рука держит телефон с экраном «+2» (refs/screen_plus2.png)
video: Kling AI Avatar (kf_a+talk1, kf_b+talk2) и Kling i2v (телефоны) параллельно, затем сборка
  ugc_build.py по шаблону edit (src подставляются из outdir), блюр клипам из шаблона.
FAL_KEY — из окружения.
"""
import sys, json, pathlib, subprocess, concurrent.futures as cf
import fal_client
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from ugc_keyframe import _dl
import ugc_kling

ROOT = pathlib.Path(__file__).resolve().parent.parent
P = {k: (ROOT / 'prompts' / f).read_text().strip() for k, f in {
    'persona': 'persona_default.txt', 'lofi': 'lofi_suffix.txt', 'dim': 'face_underlit_suffix.txt'}.items()}

# Два прохода: A1 — жест и кадр (человек тот же), A2 — замена лица. В один проход модель
# оставляет исходное лицо (проверено 12.11 на всех 4 фото).
A = ("Edit this exact phone photo with the smallest possible change. Keep the same man, "
     "the same location, background, clothing, framing and camera angle as the photo. "
     "It must be a front-camera selfie VIDEO frame held at arm's length (if the photo is a mirror selfie, turn it "
     "into a front-camera selfie in the same place, no phone visible). He raises his left forearm into the lower "
     "part of the frame, showing a black Garmin sports watch toward the camera, mouth slightly open as if talking. "
     "{lofi} {hint}")
A2 = ("Edit this exact phone photo. Replace the man with a completely different man so that he is NOT recognizable "
      "as the original person: a different face shape, different eyes and eye color, different nose, different mouth "
      "and jaw, different ears, a different hairstyle and hair. {persona} Keep everything else the same: the same "
      "location, clothing, the raised forearm with the Garmin watch, mouth slightly open as if talking, the same "
      "framing and camera angle. {dim} {lofi}")
B = ("The man from the second image, same face and identity, same clothes, in the same place and the same light as "
     "the second image. His arms are lowered out of the frame; he looks into the camera with a serious, slightly "
     "frustrated expression, mouth slightly open as if talking. Slightly different head angle than in the second "
     "image. Location reference: the first image. {dim} {lofi}")
PH = ("Phone footage in the same place and the same light as the first image, from the point of view of the man "
      "from the second image: his left hand holds a smartphone showing EXACTLY the app screen from the third image "
      "(same layout, numbers, colors and text, legible); the black Garmin watch from the second image is on his "
      "wrist. No face in frame, no subtitles. {lofi}")


def gen(prompt, imgs, out):
    r = fal_client.subscribe("fal-ai/nano-banana-pro/edit", arguments={
        "prompt": prompt, "image_urls": [fal_client.upload_file(str(p)) for p in imgs],
        "aspect_ratio": "9:16", "num_images": 1, "resolution": "1K"})
    return _dl(r["images"][0]["url"], str(out))


def frames(photo, outdir, hint="", only=""):
    o = pathlib.Path(outdir); o.mkdir(parents=True, exist_ok=True)
    gen(A.format(hint=hint, **P), [photo], o / 'kf_a0.png')
    gen(A2.format(**P), [o / 'kf_a0.png'], o / 'kf_a.png')
    jobs = [(B.format(**P), [photo, o / 'kf_a.png'], o / 'kf_b.png'),
            (PH.format(**P), [photo, o / 'kf_a.png', ROOT / 'refs/screen_plus5.png'], o / 'kf_ph1.png'),
            (PH.format(**P), [photo, o / 'kf_a.png', ROOT / 'refs/screen_plus2.png'], o / 'kf_ph2.png')]
    with cf.ThreadPoolExecutor() as ex:
        print(list(ex.map(lambda j: gen(*j), jobs)))


PH_MOTION = ("Handheld phone footage, the man holds the phone steady and slightly tilts it toward the camera, subtle "
             "natural hand tremor, the phone screen content stays exactly the same and sharp, no new text appears.")


def video(outdir, t1, t2, template):
    o = pathlib.Path(outdir)
    jobs = [lambda: ugc_kling.avatar(str(o / 'kf_a.png'), t1, str(o / 'talk1.mp4'),
                                     "Selfie video, he shows his Garmin watch to the camera, then keeps talking."),
            lambda: ugc_kling.avatar(str(o / 'kf_b.png'), t2, str(o / 'talk2.mp4')),
            lambda: ugc_kling.i2v(str(o / 'kf_ph1.png'), str(o / 'phone1.mp4'), PH_MOTION, "5"),
            lambda: ugc_kling.i2v(str(o / 'kf_ph2.png'), str(o / 'phone2.mp4'), PH_MOTION, "5")]
    with cf.ThreadPoolExecutor() as ex:
        print([f.result() for f in [ex.submit(j) for j in jobs]])
    e = json.load(open(template))
    for c in e['clips']:
        name = pathlib.Path(c['src']).name
        if name in ('talk1.mp4', 'talk2.mp4', 'phone1.mp4', 'phone2.mp4'):
            c['src'] = str(o / name)
    json.dump(e, open(o / 'edit.json', 'w'), indent=1)
    subprocess.run([sys.executable, str(ROOT / 'scripts/ugc_build.py'), str(o / 'edit.json'), str(o / 'final.mp4')],
                   check=True, cwd=ROOT)


if __name__ == '__main__':
    mode, *args = sys.argv[1:]
    {'frames': frames, 'video': video}[mode](*args)
