"""Build the mod's film entries from data/films.json and data/cast_ids.json.

Writes build/ItemsData.json -> copy to EXTERN/DATABASE/MOD/ItemsData.json
Titles come from data/titles.csv: the English parody goes in Name and Name_DE, the parody in the
original language (Portuguese for all but two) in Name_PTBR. The real title stays in _comment.
Run tools/build_cast.py first: Credits are cast IDs from data/cast_ids.json.

Conventions copied from the vanilla ItemsData.json:
  - Credits is a string of 4 IDs, director first: "9000021,  9000129, 9000054, 9000111"
  - Country 7 = Portugal; IP = the film's own ID
  - Chance is a rarity: the higher the Potential, the lower the Chance
      Potential <50 -> 15, 50s -> 8, 60s -> 5, 70s -> 3, 80+ -> 1
  - Approval is left out, as on 608 of 694 vanilla films
  - Name_DE repeats the English title and Desc_DE the English synopsis (every vanilla film fills DE)
  - Texture = image number inside SCRN/<genre folder>/, continuing after the files already there.
    Counted from the game install given by --scrn (default: the Steam path below). The install
    script recounts at install time, so these numbers are a preview.

Usage: python3 tools/build_items.py [--scrn PATH_TO_EXTERN/SCRN]
"""
import argparse
import csv
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SCRN = "/mnt/c/Program Files (x86)/Steam/steamapps/common/Mad Television Tycoon/MadTelevisionTycoon/EXTERN/SCRN"
FIRST_ID = 9_000_001
PORTUGAL = 7
FOLDER = {0: "ACTION", 1: "DRAMA", 2: "SCIFI", 3: "ROMANTIC", 4: "FANTASY", 5: "CRIME", 6: "THRILLER",
          7: "HORROR", 8: "MYSTERY", 9: "ADVENTURE", 10: "FAMILY", 11: "DOCU", 14: "ANTIWAR",
          15: "WESTERN", 16: "COMEDY", 27: "CARTOON", 28: "EROTIC", 29: "HISTORICAL"}
FLAGS = ("Cult", "Timeless", "Evergreen")  # no Premium: the owner wants none in the mod


def chance(potential):
    for floor, value in ((80, 1.0), (70, 3.0), (60, 5.0), (50, 8.0)):
        if potential >= floor:
            return value
    return 15.0


def vanilla_count(scrn, folder):
    path = os.path.join(scrn, folder)
    if not os.path.isdir(path):
        return None
    return sum(1 for f in os.listdir(path) if f.lower().endswith(".png") and f[:-4].isdigit())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scrn", default=DEFAULT_SCRN)
    args = ap.parse_args()

    films = json.load(open(os.path.join(ROOT, "data", "films.json"), encoding="utf-8"))
    cast_ids = json.load(open(os.path.join(ROOT, "data", "cast_ids.json"), encoding="utf-8"))
    titles = {int(r["id"]): r for r in
              csv.DictReader(open(os.path.join(ROOT, "data", "titles.csv"), encoding="utf-8-sig"))}

    next_tex, textures = {}, {}
    entries = []
    for n, f in enumerate(films):
        folder = FOLDER[f["gcode"]]
        if folder not in next_tex:
            count = vanilla_count(args.scrn, folder)
            next_tex[folder] = (count or 0) + 1 if count is not None else None
        tex = next_tex[folder]
        if tex is not None:
            next_tex[folder] += 1
        textures[f["pt"]] = {"folder": folder, "texture": tex, "file": "%04d.png" % tex if tex else None}

        ids = [cast_ids["%s|%d" % (name, 0 if pos == 0 else 1)] for pos, name in enumerate(f["credits"])]
        desc = f["desc"]
        item_id = FIRST_ID + n
        title = titles[item_id]
        assert title["original"] == f["pt"], "titles.csv row %d is %r, films.json has %r" % (
            item_id, title["original"], f["pt"])

        entry = {
            "_comment": "%s (%d)" % (f["pt"], f["year"]),
            "ID": item_id,
            "ItemTyp": 1,
            "Name": title["en"],
            "Desc": desc,
            "Name_DE": title["en"],
            "Desc_DE": desc,
            "Name_PTBR": title["suggested"],
            "Genre": f["gcode"],
        }
        if f.get("sgcode") is not None:
            entry["Subgenre"] = f["sgcode"]
        entry.update({
            "Credits": "%d,  %s" % (ids[0], ", ".join(str(i) for i in ids[1:])),
            "Country": PORTUGAL,
            "Date": f["year"],
            "Rating": f["rating"],
            "Blocks": f["blocks"],
            "AgeRate": f["age"],
            "Texture": tex or 0,
            "Potential": f["pot"],
        })
        for flag in FLAGS:
            if flag in f["flags"]:
                entry[flag] = True
        entry.update({"Chance": chance(f["pot"]), "IP": item_id})
        entries.append(entry)

    os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
    with open(os.path.join(ROOT, "build", "ItemsData.json"), "w", encoding="utf-8") as fh:
        json.dump({"data": entries}, fh, ensure_ascii=False, indent="\t")
    with open(os.path.join(ROOT, "build", "textures.json"), "w", encoding="utf-8") as fh:
        json.dump(textures, fh, ensure_ascii=False, indent=1)

    missing = sorted({t["folder"] for t in textures.values() if t["texture"] is None})
    print("%d films, IDs %d-%d" % (len(entries), entries[0]["ID"], entries[-1]["ID"]))
    print("texture numbers start after: " + ", ".join(
        "%s %d" % (k, v - 1 - sum(1 for t in textures.values() if t["folder"] == k))
        for k, v in sorted(next_tex.items()) if v is not None))
    if missing:
        print("WARNING: no SCRN folder found for %s; Texture left at 0" % ", ".join(missing))


if __name__ == "__main__":
    main()
