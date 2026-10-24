"""Convert the film images into the game's image format.

For each film, uses the lookalike image in stills/generated/<item ID>-i2i.png or -t2i.png when there is
one (forced to pure greyscale, centre-cropped to 4:3), and otherwise falls back to the downloaded TMDB
still in stills/stills/images/ (via stills_manifest.csv). Writes stills/png/<item ID>.png: 640x480 RGBA
PNG at 72 dpi, like the vanilla files in EXTERN/SCRN.

TMDB stills are cropped to 4:3 around a focus point: the centre for scene stills and 40% down for
portrait posters. data/crop_overrides.json can move it per film: {"<title>": {"x": 0.3, "y": 0.5}}
(0 = left/top, 1 = right/bottom). The overrides apply to TMDB stills only, not to generated images.

Also writes stills/png/_contact.jpg (all 80 results) and stills/png/_compare.jpg (TMDB still next to
the result, for every film with a generated image).

Usage: .venv/bin/python tools/convert_stills.py
"""
import csv
import json
import os

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "stills", "stills")
GEN = os.path.join(ROOT, "stills", "generated")
OUT = os.path.join(ROOT, "stills", "png")
W, H = 640, 480
FIRST_ID = 9_000_001


def crop_43(im, fx, fy):
    w, h = im.size
    if w * 3 > h * 4:  # wider than 4:3: cut the sides
        cw, ch = h * 4 // 3, h
    else:  # taller: cut top and bottom
        cw, ch = w, w * 3 // 4
    left = round((w - cw) * fx)
    top = round((h - ch) * fy)
    return im.crop((left, top, left + cw, top + ch))


def generated_image(item_id):
    for kind in ("i2i", "t2i"):
        path = os.path.join(GEN, "%d-%s.png" % (item_id, kind))
        if os.path.exists(path):
            return path, kind
    return None, None


def contact_sheet(thumbs, path, cols, tw=200, th=150, cap=18):
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * (th + cap)), "white")
    draw = ImageDraw.Draw(sheet)
    for i, (im, label) in enumerate(thumbs):
        x, y = (i % cols) * tw, (i // cols) * (th + cap)
        sheet.paste(im.convert("RGB").resize((tw, th), Image.LANCZOS), (x, y))
        draw.text((x + 3, y + th + 3), label[:34], fill="black")
    sheet.save(path, quality=85)


def main():
    films = json.load(open(os.path.join(ROOT, "data", "films.json"), encoding="utf-8"))
    overrides_path = os.path.join(ROOT, "data", "crop_overrides.json")
    overrides = json.load(open(overrides_path, encoding="utf-8")) if os.path.exists(overrides_path) else {}
    manifest = {(int(r["year"]), r["title"]): r for r in
                csv.DictReader(open(os.path.join(SRC, "stills_manifest.csv"), encoding="utf-8-sig"))}

    os.makedirs(OUT, exist_ok=True)
    thumbs, compare = [], []
    counts = {"i2i": 0, "t2i": 0, "tmdb": 0}
    for n, f in enumerate(films):
        item_id = FIRST_ID + n
        row = manifest[(f["year"], f["pt"])]
        im = Image.open(os.path.join(SRC, "images", row["filename"])).convert("RGBA")
        portrait = im.size[1] > im.size[0]
        o = overrides.get(f["pt"], {})
        fx, fy = o.get("x", 0.5), o.get("y", 0.4 if portrait else 0.5)
        tmdb = crop_43(im, fx, fy).resize((W, H), Image.LANCZOS)

        gen_path, kind = generated_image(item_id)
        if gen_path:
            gen = Image.open(gen_path).convert("L")  # pure greyscale: drops Gemini's sepia/blue tints
            out = crop_43(gen, 0.5, 0.5).resize((W, H), Image.LANCZOS).convert("RGBA")
            label = "%s (%d) %s" % (f["pt"], f["year"], kind)
            compare += [(tmdb, "TMDB: %s" % f["pt"]), (out, "new: %s" % kind)]
        else:
            out, kind = tmdb, "tmdb"
            label = "%s (%d) TMDB%s" % (f["pt"], f["year"], " poster" if portrait else "")
        counts[kind] += 1
        out.save(os.path.join(OUT, "%d.png" % item_id), dpi=(72, 72), optimize=True)
        thumbs.append((out, label))

    contact_sheet(thumbs, os.path.join(OUT, "_contact.jpg"), cols=8)
    if compare:
        contact_sheet(compare, os.path.join(OUT, "_compare.jpg"), cols=8)
    print("%d images -> %s (generated: %d i2i, %d t2i; TMDB stills: %d)" % (
        len(thumbs), OUT, counts["i2i"], counts["t2i"], counts["tmdb"]))


if __name__ == "__main__":
    main()
