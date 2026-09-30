#!/usr/bin/env python3
"""Render the profile card (assets/card-light.svg, assets/card-dark.svg).

Usage: render.py NAME=DESCRIPTION [NAME=DESCRIPTION ...]
"""
import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
THEMES = {
    'light': {'fg': '#1f2328', 'muted': '#656d76'},
    'dark': {'fg': '#e6edf3', 'muted': '#7d8590'},
}
FONT = ("ui-monospace, 'JetBrains Mono', SFMono-Regular, Menlo, Consolas, "
        "'Liberation Mono', monospace")
SIZE, LINE, CHAR = 14, 24, 8.6  # font size, line height, approx. glyph width


def render(title, repos, theme):
    fg, muted = theme['fg'], theme['muted']
    pad = max((len(name) for name, _ in repos), default=0) + 3
    rows = [(name.ljust(pad), desc) for name, desc in repos]
    longest = max([len(title)] + [len(n) + len(d) for n, d in rows])
    width = round(longest * CHAR) + 24
    height = 30 + LINE * (len(rows) + 1) + 20
    y_cursor = 30 + LINE * (len(rows) + 1) - SIZE + 2

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">',
        f'<title>{escape(title)}</title>',
        '<style>'
        f'text{{font-family:{FONT};font-size:{SIZE}px;white-space:pre}}'
        '.cursor{animation:blink 1.1s steps(1) infinite}'
        '@keyframes blink{50%{opacity:0}}'
        '</style>',
        f'<text x="2" y="22" fill="{fg}" font-weight="600" font-size="18">{escape(title)}</text>',
    ]
    for i, (name, desc) in enumerate(rows):
        y = 30 + LINE * (i + 1)
        out.append(f'<text x="2" y="{y}" xml:space="preserve">'
                   f'<tspan fill="{fg}">{escape(name)}</tspan>'
                   f'<tspan fill="{muted}">{escape(desc)}</tspan></text>')
    out.append(f'<rect class="cursor" x="2" y="{y_cursor}" width="8" height="{SIZE + 2}" fill="{fg}"/>')
    out.append('</svg>')
    return '\n'.join(out) + '\n'


def main(args):
    repos = [tuple(arg.split('=', 1)) for arg in args]
    (ROOT / 'assets').mkdir(exist_ok=True)
    for name, theme in THEMES.items():
        (ROOT / 'assets' / f'card-{name}.svg').write_text(render('qokori', repos, theme))


if __name__ == '__main__':
    main(sys.argv[1:])
