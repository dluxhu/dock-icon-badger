#!/usr/bin/env python3
"""
make_gallery.py - regenerate the README gallery and the web UI style thumbnails from samples/.

    python3 examples/make_gallery.py

Writes examples/styles-light.png and examples/styles-dark.png (every style: 4 sample apps x 2
sample badges) and web/thumbs/<style>.png (the Swirl sample with the Beta badge).
"""
import os, sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import dock_icon_badger as dib  # noqa: E402

SAMPLES = os.path.join(ROOT, "samples")
APPS = ["Mail", "Calendar", "Notes", "Swirl"]
BADGES = [("todo-dodo", "Todo-Dodo"), ("beta", "Beta")]


def badge_path(base):
    svg = os.path.join(SAMPLES, "badges", base + ".svg")
    return svg if dib.svg_backend() and os.path.exists(svg) else os.path.join(SAMPLES, "badges", base + ".png")


def main():
    apps = [dib.App(os.path.join(SAMPLES, "apps", n + ".png")) for n in APPS]
    logos = []
    for base, label in BADGES:
        lg = dib.Logo(badge_path(base)); lg.name = label; logos.append(lg)
    rows, thumbs = [], os.path.join(ROOT, "web", "thumbs"); os.makedirs(thumbs, exist_ok=True)
    for st in dib.STYLES:
        ims = []
        for lg in logos:
            for a in apps:
                img, _ = dib.render(a, lg, st); ims.append((a.name, img))
                if a.name == "Swirl" and lg.name == "Beta": img.resize((192, 192), Image.LANCZOS).save(os.path.join(thumbs, st + ".png"), optimize=True)
        rows.append((st, ims)); print(st)
    t, pad, lab, n = 200, 20, 280, len(rows[0][1])
    for th in ("light", "dark"):
        tmp = os.path.join(HERE, f".sheet-{th}.png"); dib.preview(rows, tmp, (th,))
        im = Image.open(tmp); W = lab + n*(t + pad) + 6; im = im.crop((0, 30, W, im.height))
        im = im.resize((1600, round(im.height*1600/W)), Image.LANCZOS); im.save(os.path.join(HERE, f"styles-{th}.png"), optimize=True)
        os.remove(tmp); print(f"examples/styles-{th}.png", im.size)


if __name__ == "__main__":
    main()
