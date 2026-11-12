"""UGC-ролик из одного реального фото (правило rules/ugc-video-from-photo.md). Универсальный:
всё, что относится к продукту (персона, предмет в кадре, жест, экраны приложения, монтажный шаблон),
лежит в конфиге проекта projects/<проект>/ugc.json. Пример: projects/example-app/ugc.json.

python3 scripts/ugc_from_photo.py frames <project/ugc.json> <photo.jpg> <outdir>
python3 scripts/ugc_from_photo.py video  <project/ugc.json> <outdir>

frames (nano-banana-pro/edit), всё в локации и свете исходного фото:
  kf_a0  — проход 1: тот же человек, кадр фронталки, жест gesture_a (показывает prop), говорит
  kf_a   — проход 2: неузнаваемо другое лицо по persona
  kf_b   — тот же новый человек, жест gesture_b, другой угол
  проход 3 (A3, relight): kf_a и kf_b отдельно переосвещаются «лицо на ступень темнее фона»
           (в проходе 2 модель суффикс недосвета игнорирует, проверено 12.11.2026); до прохода — *_lit.png
  kf_ph1..N — рука держит телефон с экраном из screens[i], prop на руке, лица нет
video: Kling AI Avatar (kf_a+talk[0], kf_b+talk[1]) и Kling i2v (телефоны) параллельно,
  затем ugc_build.py по шаблону edit_template (src talk1/talk2/phoneN подставляются из outdir).
Пути в конфиге — относительно корня репозитория. FAL_KEY — из окружения.
"""
import sys, json, pathlib, subprocess, concurrent.futures as cf
import fal_client
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from ugc_keyframe import _dl
import ugc_kling

ROOT = pathlib.Path(__file__).resolve().parent.parent
P = {k: (ROOT / 'prompts' / f).read_text().strip() for k, f in {
    'persona': 'persona_default.txt', 'lofi': 'lofi_suffix.txt', 'dim': 'face_underlit_suffix.txt',
    'relight': 'relight_underlit.txt'}.items()}

DEFAULTS = {
    "gesture_a": "mouth slightly open as if talking, natural friendly expression",
    "gesture_b": "arms lowered out of the frame, a serious, slightly frustrated expression, mouth slightly open as if talking",
    "prop": "",
    "avatar_prompts": ["Selfie video, the person talks to the camera like to a friend.", "Selfie video."],
    "phone_motion": ("Handheld phone footage, the person holds the phone steady and slightly tilts it toward the camera, "
                     "subtle natural hand tremor, the phone screen content stays exactly the same and sharp, "
                     "no new text appears."),
    "screens": [],
}

# Два прохода: A1 — жест и кадр (человек тот же), A2 — замена лица. В один проход модель
# оставляет исходное лицо (проверено 12.11.2026 на 4 фото).
A = ("Edit this exact phone photo with the smallest possible change. Keep the same person, "
     "the same location, background, clothing, framing and camera angle as the photo. "
     "It must be a front-camera selfie VIDEO frame held at arm's length (if the photo is a mirror selfie, turn it "
     "into a front-camera selfie in the same place, no phone visible). {gesture_a}. {lofi}")
A2 = ("Edit this exact phone photo. Replace the person with a completely different person so that they are NOT "
      "recognizable as the original: a different face shape, different eyes and eye color, different nose, different "
      "mouth and jaw, different ears, a different hairstyle and hair. {persona} Keep everything else the same: the "
      "same location, clothing, pose and gesture{prop_keep}, mouth slightly open as if talking, the same framing and "
      "camera angle. {dim} {lofi}")
B = ("The person from the second image, same face and identity, same clothes, in the same place and the same light "
     "as the second image: {gesture_b}. Slightly different head angle than in the second image. "
     "Location reference: the first image. {dim} {lofi}")
PH = ("Phone footage in the same place and the same light as the first image, from the point of view of the person "
      "from the second image: their hand holds a smartphone showing EXACTLY the app screen from the third image "
      "(same layout, numbers, colors and text, legible){prop_hand}. No face in frame, no subtitles. {lofi}")


def load(cfg):
    c = dict(DEFAULTS, **json.load(open(cfg)))
    persona = c.get('persona') or P['persona']
    fmt = dict(P, persona=persona, gesture_a=c['gesture_a'], gesture_b=c['gesture_b'],
               prop_keep=f", {c['prop']}" if c['prop'] else "",
               prop_hand=f"; {c['prop']} is visible on the hand/wrist like in the second image" if c['prop'] else "")
    return c, fmt


def gen(prompt, imgs, out):
    r = fal_client.subscribe("fal-ai/nano-banana-pro/edit", arguments={
        "prompt": prompt, "image_urls": [fal_client.upload_file(str(p)) for p in imgs],
        "aspect_ratio": "9:16", "num_images": 1, "resolution": "1K"})
    return _dl(r["images"][0]["url"], str(out))


def relight(img):
    """Проход A3: отдельный проход «только свет» (лицо темнее фона). Исходник сохраняется как *_lit.png."""
    img = pathlib.Path(img); lit = img.with_name(img.stem + '_lit.png')
    if not lit.exists(): img.rename(lit)
    return gen(P['relight'], [lit], img)


def frames(cfg, photo, outdir):
    c, f = load(cfg)
    a2, b = A2.format(**f), B.format(**f)
    # правило «лицо недосвечено» нельзя потерять: суффикс обязан быть в промптах лица, а свет — отдельным проходом
    assert P['dim'] in a2 and P['dim'] in b, 'face_underlit_suffix не попал в промпт A2/B'
    assert 'darker than the background' in P['relight'], 'prompts/relight_underlit.txt пустой или изменён'
    o = pathlib.Path(outdir); o.mkdir(parents=True, exist_ok=True)
    gen(A.format(**f), [photo], o / 'kf_a0.png')
    gen(a2, [o / 'kf_a0.png'], o / 'kf_a.png')
    jobs = [(b, [photo, o / 'kf_a.png'], o / 'kf_b.png')]
    jobs += [(PH.format(**f), [photo, o / 'kf_a.png', ROOT / s], o / f'kf_ph{i + 1}.png')
             for i, s in enumerate(c['screens'])]
    with cf.ThreadPoolExecutor() as ex:
        print(list(ex.map(lambda j: gen(*j), jobs)))
    with cf.ThreadPoolExecutor() as ex:  # A3: свет отдельным проходом
        print(list(ex.map(relight, [o / 'kf_a.png', o / 'kf_b.png'])))


def video(cfg, outdir):
    c, _ = load(cfg)
    o = pathlib.Path(outdir)
    assert (o / 'kf_a_lit.png').exists() and (o / 'kf_b_lit.png').exists(), 'нет прохода A3 (relight): запусти frames заново'
    t1, t2 = (str(ROOT / t) for t in c['talk'])
    jobs = [lambda: ugc_kling.avatar(str(o / 'kf_a.png'), t1, str(o / 'talk1.mp4'), c['avatar_prompts'][0]),
            lambda: ugc_kling.avatar(str(o / 'kf_b.png'), t2, str(o / 'talk2.mp4'), c['avatar_prompts'][1])]
    jobs += [(lambda i=i: ugc_kling.i2v(str(o / f'kf_ph{i}.png'), str(o / f'phone{i}.mp4'), c['phone_motion'], "5"))
             for i in range(1, len(c['screens']) + 1)]
    with cf.ThreadPoolExecutor() as ex:
        print([fu.result() for fu in [ex.submit(j) for j in jobs]])
    e = json.load(open(ROOT / c['edit_template']))
    for cl in e['clips']:
        name = pathlib.Path(cl['src']).name
        cl['src'] = str(o / name) if (o / name).exists() else str(ROOT / cl['src'])
    for k in ('audio', 'overlay'):
        e[k] = str(ROOT / e[k])
    json.dump(e, open(o / 'edit.json', 'w'), indent=1)
    clips = [str(p) for p in sorted(o.glob('talk*.mp4')) + sorted(o.glob('phone*.mp4'))]
    subprocess.run([sys.executable, str(ROOT / 'scripts/slop_check.py'), *clips, '--out', str(o / 'slop')], check=True)
    print('СМОТРИ листы', o / 'slop', '— нейрослоп проверяется глазами до сборки (rules/ugc-video-from-photo.md, шаг 10)')
    subprocess.run([sys.executable, str(ROOT / 'scripts/ugc_build.py'), str(o / 'edit.json'), str(o / 'final.mp4')],
                   check=True, cwd=ROOT)


if __name__ == '__main__':
    mode, *args = sys.argv[1:]
    {'frames': frames, 'video': video}[mode](*args)
