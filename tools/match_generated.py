"""Find which film a generated image belongs to, and save it under stills/generated/.

Compares the image's light-and-dark layout with every converted still in stills/png/ (colour is
ignored, so a black-and-white restyle still matches its colour original). Saves the image as
stills/generated/<id>-<kind>.png when the best match is clear; otherwise lists the candidates.

Usage:
  .venv/bin/python tools/match_generated.py IMAGE [--kind i2i|t2i] [--id 9000042] [--dry-run]
  --id skips the matching and saves under that film ID.
"""
import argparse
import json
import os
import shutil

from PIL import Image, ImageChops, ImageOps, ImageStat

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIRST_ID = 9_000_001
CLEAR_MATCH = 35   # mean difference (0-255) below which the best match is accepted
CLEAR_GAP = 20     # ...and how far ahead of the runner-up it must be


def signature(path):
    return ImageOps.equalize(Image.open(path).convert("L").resize((64, 48)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--kind", default="i2i", choices=("i2i", "t2i"))
    ap.add_argument("--id", type=int)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    films = json.load(open(os.path.join(ROOT, "data", "films.json"), encoding="utf-8"))
    title = lambda i: films[i - FIRST_ID]["pt"]

    if args.id:
        item_id = args.id
    else:
        png_dir = os.path.join(ROOT, "stills", "png")
        ref = signature(args.image)
        scores = sorted(
            (ImageStat.Stat(ImageChops.difference(ref, signature(os.path.join(png_dir, f)))).mean[0], int(f[:-4]))
            for f in os.listdir(png_dir) if f[:-4].isdigit())
        for score, i in scores[:3]:
            print("%5.1f  %d  %s" % (score, i, title(i)))
        (best, item_id), (second, _) = scores[0], scores[1]
        if best > CLEAR_MATCH or second - best < CLEAR_GAP:
            raise SystemExit("No clear match. Re-run with --id <film ID> to save it.")

    dest = os.path.join(ROOT, "stills", "generated", "%d-%s.png" % (item_id, args.kind))
    size = Image.open(args.image).size
    if args.dry_run:
        print("would save %s (%dx%d) for %s" % (dest, size[0], size[1], title(item_id)))
        return
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copyfile(args.image, dest)
    os.chmod(dest, 0o644)
    print("saved %s (%dx%d) for %s" % (os.path.relpath(dest, ROOT), size[0], size[1], title(item_id)))


if __name__ == "__main__":
    main()
