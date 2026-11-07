#!/usr/bin/env python3
"""
make_samples.py - regenerate the original, publishable sample app icons and badges.

    python3 samples/make_samples.py

Writes samples/apps/*.png (1024 px) and samples/badges/*.svg + *.png (1024 px). Everything is
drawn here from scratch (no third-party artwork, no fonts), so the samples can be shared freely.
The set is bright and contemporary: luminous gradients with a soft inner glow, crisp white
geometric glyphs, translucent "glass" layers for depth and one thin shadow. It avoids the look
of any vendor's own app icons. The apps deliberately use different presentations, to exercise
dock_icon_badger's input classifier:

    Mail      full-bleed hot pink to orange, white envelope over a glass letter -> "full-bleed"
    Calendar  electric blue squircle, white card with a dot grid, pink day      -> "macOS-shaped"
    Notes     bare mint page over a glass page, pink pen stroke                 -> "glyph on white"
    Swirl     violet-to-pink squircle, white spiral with a soft glow            -> "macOS-shaped"
    Weather   sunny yellow squircle, sun behind a glass cloud, blue droplet     -> "macOS-shaped"
    Terminal  full-bleed lime-to-aqua, glass window, white prompt and cursor    -> "full-bleed"
    Music     bare sound-wave capsules (pink to violet) over a glass disc       -> "glyph on white"
    Chat      soft white squircle, glassy blue bubble behind a pink one         -> "macOS-shaped"

Badges: todo-dodo (copy of the Todo-Dodo SVG, not drawn here), beta (red scalloped seal with
heavy BETA lettering drawn from the block-letter paths in LETTERS) and dev (green seal with a
</> glyph). No text is rendered with a font anywhere, so the output is the same on every machine.
Needs Pillow, numpy and cairosvg (with the cairo library).
"""
import io, math, os, sys
import cairosvg
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import dock_icon_badger as dib  # noqa: E402

APPS, BADGES = os.path.join(HERE, "apps"), os.path.join(HERE, "badges")
SQ = dib.SQUIRCLE_D   # Apple's squircle, in 100..924 coordinates of the 1024 canvas


def svg_png(svg, size=1024):
    return Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode(), output_width=size, output_height=size))).convert("RGBA")


def with_apple_shadow(im):
    """Add Apple's template drop shadow under a squircle icon (black 30 %, sigma 12, 10 px down)."""
    out = dib.shadow(im.getchannel("A"), *dib.APPLE_SHADOW); out.alpha_composite(im); return out


def svg(body, defs=""):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024"><defs>{defs}</defs>{body}</svg>'


# ------------------------------------------------------------------ apps

# Modern, luminous set: bright gradients with a soft inner glow, crisp white geometric glyphs,
# translucent "glass" layers (white at low opacity with a light rim) for depth, one thin shadow.
WHITE = "#ffffff"
THIN = ('<filter id="sh" x="-30%" y="-30%" width="160%" height="170%">'
        '<feDropShadow dx="0" dy="6" stdDeviation="10" flood-color="#1a1244" flood-opacity="0.16"/></filter>')


def grad(gid, c1, c2, vertical=False):
    x2, y2 = ("0", "1") if vertical else ("1", "1")
    return f'<linearGradient id="{gid}" x1="0" y1="0" x2="{x2}" y2="{y2}"><stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/></linearGradient>'


GLOW = ('<radialGradient id="glow" cx="0.28" cy="0.18" r="0.75"><stop offset="0" stop-color="#fff" stop-opacity="0.09"/>'
        '<stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>')


def glass(shape, fill="#fff", opacity=0.22, rim="#fff", rim_opacity=0.55):
    """A translucent layer with a light rim. `shape` is an SVG element without fill/stroke."""
    return shape.replace("/>", f' fill="{fill}" fill-opacity="{opacity}" stroke="{rim}" stroke-opacity="{rim_opacity}" stroke-width="4"/>')


def full_bg(c1, c2):
    return grad("bg", c1, c2) + GLOW, '<rect width="1024" height="1024" fill="url(#bg)"/><rect width="1024" height="1024" fill="url(#glow)"/>'


def squircle_bg(c1, c2):
    return (f'<clipPath id="sq"><path d="{SQ}"/></clipPath>' + grad("bg", c1, c2) + GLOW,
            '<g clip-path="url(#sq)"><rect x="100" y="100" width="824" height="824" fill="url(#bg)"/>'
            '<rect x="100" y="100" width="824" height="824" fill="url(#glow)"/></g>')


def mail():
    """Full-bleed hot pink to sunny orange; white envelope over a glass second letter, yellow seal dot."""
    d, bg = full_bg("#f2047f", "#ff7a04")
    body = f'''{bg}
      {glass('<rect x="306" y="262" width="500" height="350" rx="64"/>')}
      <g filter="url(#sh)"><rect x="222" y="340" width="560" height="390" rx="70" fill="{WHITE}"/></g>
      <path d="M290 420 L502 580 L714 420" fill="none" stroke="#f2047f" stroke-width="30" stroke-linecap="round" stroke-linejoin="round"/>
      <circle cx="502" cy="586" r="44" fill="#ffd602"/>'''
    return svg_png(svg(body, d + THIN))


def calendar():
    """Electric blue squircle; glass card behind a white card with a 3x3 dot grid, one hot-pink checked day."""
    d, bg = squircle_bg("#0a8cff", "#3825ff")
    dots = []
    for r in range(3):
        for c in range(3):
            cx, cy = 402 + c*110, 470 + r*104
            if (r, c) == (1, 0):   # left of center, so the corner badge never hides it
                dots.append(f'<circle cx="{cx}" cy="{cy}" r="44" fill="url(#hot)"/>'
                            f'<path d="M{cx-20} {cy+2} L{cx-5} {cy+17} L{cx+21} {cy-14}" fill="none" stroke="#fff" stroke-width="13" stroke-linecap="round" stroke-linejoin="round"/>')
            else:
                dots.append(f'<circle cx="{cx}" cy="{cy}" r="30" fill="#bad0fe"/>')
    body = f'''{bg}
      {glass('<rect x="322" y="236" width="470" height="470" rx="96"/>')}
      <g filter="url(#sh)"><rect x="252" y="300" width="500" height="500" rx="100" fill="{WHITE}"/></g>
      <rect x="342" y="362" width="200" height="26" rx="13" fill="#2348ff"/>
      {"".join(dots)}'''
    return with_apple_shadow(svg_png(svg(body, d + THIN + grad("hot", "#ff088b", "#e0045f"))))


def notes():
    """Bare glyph: mint page over a glass page, white lines, one bold hot-pink pen stroke."""
    body = f'''<g transform="rotate(8 560 512)">{glass('<rect x="330" y="190" width="420" height="580" rx="84"/>', '#04c99a', 0.55, '#01b488', 0.8)}</g>
      <g filter="url(#sh)"><rect x="262" y="230" width="440" height="600" rx="88" fill="url(#pg)"/></g>
      <rect x="340" y="330" width="230" height="30" rx="15" fill="#fff" fill-opacity="0.9"/>
      <rect x="340" y="400" width="170" height="30" rx="15" fill="#fff" fill-opacity="0.9"/>
      <path d="M332 640 C392 560 444 700 504 620 S600 560 640 600" fill="none" stroke="url(#pen)" stroke-width="40" stroke-linecap="round"/>'''
    return svg_png(svg(body, grad("pg", "#01daa3", "#00a37f", True) + grad("pen", "#f2047f", "#ff6a04") + THIN))


def swirl():
    """Violet-to-pink squircle with a crisp white spiral over a soft wide glow of itself."""
    pts = []
    for i in range(0, 361):
        th = i/360*3.4*math.pi; r = 20 + 26*th
        pts.append((530 + r*math.cos(th - math.pi/2), 500 + r*math.sin(th - math.pi/2)))
    p = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    d, bg = squircle_bg("#6404ff", "#f30298")
    body = f'''{bg}
      <path d="{p}" fill="none" stroke="#fff" stroke-opacity="0.18" stroke-width="96" stroke-linecap="round" stroke-linejoin="round"/>
      <g filter="url(#sh)"><path d="{p}" fill="none" stroke="#fff" stroke-width="44" stroke-linecap="round" stroke-linejoin="round"/></g>'''
    return with_apple_shadow(svg_png(svg(body, d + THIN)))


def weather():
    """Sunny yellow-to-orange squircle; white sun behind a glass cloud, one electric-blue droplet."""
    d, bg = squircle_bg("#ffc007", "#ff7304")
    cloud = "M352 680 a110 110 0 0 1 12 -219 a160 160 0 0 1 304 -44 a125 125 0 0 1 32 263 Z"
    body = f'''{bg}
      <circle cx="650" cy="372" r="150" fill="url(#sun)"/>
      <g filter="url(#sh)">{glass(f'<path d="{cloud}"/>', opacity=0.9, rim_opacity=0.95)}</g>
      <g filter="url(#sh)"><path d="M512 712 q-62 94 0 132 q62 -38 0 -132 Z" fill="url(#drop)"/></g>'''
    sun = '<radialGradient id="sun" cx="0.4" cy="0.35" r="0.7"><stop offset="0" stop-color="#feef91"/><stop offset="1" stop-color="#ffd617"/></radialGradient>'
    return with_apple_shadow(svg_png(svg(body, d + THIN + sun + grad("drop", "#109dff", "#1932ff", True))))


def terminal():
    """Full-bleed lime-to-aqua; glass window card, crisp white prompt and cursor."""
    d, bg = full_bg("#22cd00", "#0094c4")
    body = f'''{bg}
      {glass('<rect x="170" y="230" width="684" height="564" rx="96"/>')}
      <g filter="url(#sh)">
        <path d="M290 400 L440 512 L290 624" fill="none" stroke="#fff" stroke-width="64" stroke-linecap="round" stroke-linejoin="round"/>
        <rect x="500" y="580" width="230" height="64" rx="32" fill="#fff"/></g>'''
    return svg_png(svg(body, d + THIN))


def music():
    """Bare glyph: sound-wave capsules in a hot-pink to violet gradient over a glass disc."""
    hs = (180, 340, 480, 300, 420, 220)
    bars = "".join(f'<rect x="{252 + i*96}" y="{512 - h/2}" width="56" height="{h}" rx="28"/>' for i, h in enumerate(hs))
    body = f'''{glass('<circle cx="512" cy="512" r="330"/>', '#ff0791', 0.26, '#ff0791', 0.5)}
      <g filter="url(#sh)" fill="url(#wave)">{bars}</g>'''
    return svg_png(svg(body, grad("wave", "#eb007c", "#580fff") + THIN))


def chat():
    """Soft white squircle; translucent electric-blue bubble behind a hot-pink bubble with white dots."""
    d, bg = squircle_bg("#f2f5fd", "#d4e0ff")
    back = "M430 230 H720 a100 100 0 0 1 100 100 V470 a100 100 0 0 1 -100 100 H710 L760 650 L640 570 H430 a100 100 0 0 1 -100 -100 V330 a100 100 0 0 1 100 -100 Z"
    front = "M310 420 H600 a100 100 0 0 1 100 100 V660 a100 100 0 0 1 -100 100 H400 L300 830 L320 760 H310 a100 100 0 0 1 -100 -100 V520 a100 100 0 0 1 100 -100 Z"
    body = f'''{bg}
      <path d="{back}" fill="url(#b1)" fill-opacity="0.85"/>
      <g filter="url(#sh)"><path d="{front}" fill="url(#b2)"/>
        <circle cx="352" cy="590" r="34" fill="#fff"/><circle cx="455" cy="590" r="34" fill="#fff"/><circle cx="558" cy="590" r="34" fill="#fff"/></g>'''
    return with_apple_shadow(svg_png(svg(body, d + THIN + grad("b1", "#109dff", "#1f43ff") + grad("b2", "#f9038a", "#db0357"))))


# ------------------------------------------------------------------ badges
# Heavy block letters as paths on a 100-unit cap height (fill-rule evenodd for the counters).
LETTERS = {
    "B": (76, "M0 0 H42 C62 0 71 10 71 25 C71 36 64 44 55 47 C67 50 76 59 76 72 C76 89 64 100 44 100 H0 Z "
              "M24 20 H39 C45 20 48 23 48 28 C48 33 45 36 39 36 H24 Z M24 56 H42 C49 56 52 60 52 67 C52 74 49 79 42 79 H24 Z"),
    "E": (60, "M0 0 H60 V21 H24 V39 H54 V60 H24 V79 H60 V100 H0 Z"),
    "T": (66, "M0 0 H66 V22 H45 V100 H21 V22 H0 Z"),
    "A": (82, "M0 100 L27 0 H55 L82 100 H57 L52 82 H30 L25 100 Z M35 63 H47 L41 37 Z"),
}


def word_paths(word, gap=9):
    x, parts = 0, []
    for ch in word:
        w, d = LETTERS[ch]; parts.append(f'<path transform="translate({x} 0)" d="{d}"/>'); x += w + gap
    return "".join(parts), x - gap


def beta_svg():
    n, R, amp = 18, 456, 14          # scalloped rim: n bumps around radius R
    pts = []
    for i in range(720):
        t = i/720*2*math.pi; r = R - amp + amp*math.cos(n*t)
        pts.append((512 + r*math.cos(t), 512 + r*math.sin(t)))
    rim = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + " Z"
    letters, w = word_paths("BETA"); sc = 560/w
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024">
  <defs>
    <radialGradient id="red" cx="0.42" cy="0.35" r="0.75"><stop offset="0" stop-color="#ff0329"/><stop offset="0.7" stop-color="#db031a"/><stop offset="1" stop-color="#b50013"/></radialGradient>
    <filter id="tx" x="-10%" y="-10%" width="120%" height="130%"><feDropShadow dx="0" dy="10" stdDeviation="8" flood-color="#5a0006" flood-opacity="0.45"/></filter>
  </defs>
  <path d="{rim}" fill="url(#red)"/>
  <circle cx="512" cy="512" r="372" fill="none" stroke="#fff" stroke-width="16"/>
  <circle cx="512" cy="512" r="340" fill="none" stroke="#fff" stroke-opacity="0.35" stroke-width="5"/>
  <g transform="translate(512 512) rotate(-8) skewX(-10) scale({sc:.4f}) translate({-w/2:.1f} -50)" fill="#fff" fill-rule="evenodd" filter="url(#tx)">{letters}</g>
</svg>'''


def dev_svg():
    """Green rounded seal with a white </> code glyph."""
    return '''<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024">
  <defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#06c976"/><stop offset="1" stop-color="#028b4e"/></linearGradient></defs>
  <rect x="112" y="112" width="800" height="800" rx="220" fill="url(#g)" stroke="#fff" stroke-width="40"/>
  <g fill="none" stroke="#fff" stroke-width="78" stroke-linecap="round" stroke-linejoin="round">
    <path d="M380 340 L230 512 L380 684"/><path d="M644 340 L794 512 L644 684"/><path d="M568 300 L456 724"/></g>
</svg>'''


def main():
    os.makedirs(APPS, exist_ok=True); os.makedirs(BADGES, exist_ok=True)
    for name, fn in (("Mail", mail), ("Calendar", calendar), ("Notes", notes), ("Swirl", swirl),
                     ("Weather", weather), ("Terminal", terminal), ("Music", music), ("Chat", chat)):
        fn().save(os.path.join(APPS, name + ".png"), optimize=True); print("apps/" + name + ".png")
    b = beta_svg(); open(os.path.join(BADGES, "beta.svg"), "w").write(b)
    svg_png(b).save(os.path.join(BADGES, "beta.png"), optimize=True); print("badges/beta.svg, badges/beta.png")
    d = dev_svg(); open(os.path.join(BADGES, "dev.svg"), "w").write(d)
    svg_png(d).save(os.path.join(BADGES, "dev.png"), optimize=True); print("badges/dev.svg, badges/dev.png")
    src = os.path.join(BADGES, "todo-dodo.svg")   # the Todo-Dodo logo is kept as a file, not drawn here
    if os.path.exists(src):
        im = Image.open(io.BytesIO(cairosvg.svg2png(url=src, output_width=1024, output_height=1024))).convert("RGBA")
        im.save(os.path.join(BADGES, "todo-dodo.png"), optimize=True); print("badges/todo-dodo.png")


if __name__ == "__main__":
    main()
