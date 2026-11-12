"""Запрет короткого пути для текста на видео (rules/design-pass.md): любой текст — только HTML-шаблон + render_html.py.

guard(args)               — вызывается сборщиками перед ffmpeg: падает, если в команде есть drawtext / subtitles / ass.
python3 scripts/text_guard.py <папка> — ищет в .py/.sh запрещённое: ffmpeg drawtext, subtitles=/ass=, PIL ImageDraw.text.
"""
import re, sys, pathlib
BAD = re.compile(r"drawtext|(?<![\w-])subtitles=|(?<![\w-])ass=|ImageDraw\.Draw\([^)]*\)\.text|\.text\(\s*\(\s*\d")


def guard(args):
    s = ' '.join(map(str, args))
    if re.search(r"drawtext|(?<![\w-])subtitles=|(?<![\w-])ass=", s):
        raise SystemExit('ЗАПРЕЩЕНО: текст на видео через ffmpeg drawtext/subtitles/ass. '
                         'Текст — только HTML-шаблон + render_html.py (rules/design-pass.md).')


if __name__ == '__main__':
    hits = []
    for p in pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else '.').rglob('*'):
        if p.suffix in ('.py', '.sh') and p.name != 'text_guard.py':
            for i, line in enumerate(p.read_text(errors='ignore').splitlines(), 1):
                if BAD.search(line): hits.append(f'{p}:{i}: {line.strip()[:120]}')
    print('\n'.join(hits) or 'чисто'); sys.exit(1 if hits else 0)
