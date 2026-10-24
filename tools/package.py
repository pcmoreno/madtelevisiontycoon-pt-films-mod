"""Build the player zip ("Option B"): scripts + our data only, no game data.

Layout inside the zip (one top folder, so "Extract All" makes a clean folder):
  PacotePortugues-<version>/Install.bat, Uninstall.bat, install.ps1, uninstall.ps1, README.txt
  PacotePortugues-<version>/data/PacotePortugues_items.json, PacotePortugues_cast.json
  PacotePortugues-<version>/data/images/<film ID>.png

Checks what install.ps1 relies on: every film has an "ID" key before its "Texture" key, a known genre and
a 640x480 PNG; IDs are unique; the .ps1 files are ASCII (PowerShell 5.1 reads BOM-less scripts as ANSI);
.bat files get CRLF line endings.

Usage: python3 tools/package.py --version 1.0 [--scripts tools/windows] [--out build/]
"""
import argparse
import json
import os
import struct
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FOLDER = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 15, 16, 27, 28, 29}   # genre codes with a SCRN folder
SCRIPTS = ("Install.bat", "Uninstall.bat", "install.ps1", "uninstall.ps1", "README.txt")


def png_size(path):
    with open(path, "rb") as fh:
        head = fh.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        sys.exit("Not a PNG: " + path)
    return struct.unpack(">II", head[16:24])


def dump(data):
    # Same style as the build scripts; ensure_ascii=False keeps accents as UTF-8 (no \u escapes),
    # the form the game has been seen to load.
    return (json.dumps(data, ensure_ascii=False, indent="\t") + "\n").encode("utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", required=True)
    ap.add_argument("--scripts", default=os.path.join(ROOT, "tools", "windows"), help="folder with the 5 files")
    ap.add_argument("--build", default=os.path.join(ROOT, "build"))
    ap.add_argument("--png", default=os.path.join(ROOT, "stills", "png"))
    ap.add_argument("--out", default=os.path.join(ROOT, "build"))
    args = ap.parse_args()

    items = json.load(open(os.path.join(args.build, "ItemsData.json"), encoding="utf-8"))
    cast = json.load(open(os.path.join(args.build, "CastData.json"), encoding="utf-8"))
    for name, data in (("items", items), ("cast", cast)):
        ids = [e["ID"] for e in data["data"]]
        if len(ids) != len(set(ids)):
            sys.exit("Duplicate IDs in " + name)
    cast_ids = {e["ID"] for e in cast["data"]}
    for e in items["data"]:
        keys = list(e)
        if "Texture" not in keys or keys.index("ID") > keys.index("Texture"):
            sys.exit("Film %s: needs an ID key before a Texture key (install.ps1 sets Texture by text)" % e["ID"])
        if e["Genre"] not in FOLDER:
            sys.exit("Film %s: genre %s has no SCRN folder" % (e["ID"], e["Genre"]))
        missing = [c for c in (int(x) for x in e.get("Credits", "").split(",") if x.strip()) if c not in cast_ids
                   and c >= 9000000]
        if missing:
            sys.exit("Film %s credits unknown cast IDs %s" % (e["ID"], missing))
        e["Texture"] = 0  # set by install.ps1 on the player's PC

    top = "PacotePortugues-" + args.version
    os.makedirs(args.out, exist_ok=True)
    zpath = os.path.join(args.out, top + ".zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for name in SCRIPTS:
            raw = open(os.path.join(args.scripts, name), "rb").read()
            if name.endswith(".ps1"):
                try:
                    raw.decode("ascii")
                except UnicodeDecodeError:
                    sys.exit(name + " must be ASCII-only (Windows PowerShell 5.1 would misread it)")
            if name.endswith((".bat", ".txt", ".ps1")):
                raw = raw.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
            if name == "README.txt":
                raw = b"\xef\xbb\xbf" + raw.lstrip(b"\xef\xbb\xbf")   # BOM so Notepad shows the accents for sure
            z.writestr(top + "/" + name, raw)
        z.writestr(top + "/data/PacotePortugues_items.json", dump(items))
        z.writestr(top + "/data/PacotePortugues_cast.json", dump(cast))
        for e in items["data"]:
            src = os.path.join(args.png, "%d.png" % e["ID"])
            if not os.path.exists(src):
                sys.exit("Missing image " + src)
            if png_size(src) != (640, 480):
                sys.exit("%s is %dx%d, not 640x480" % ((src,) + png_size(src)))
            z.write(src, "%s/data/images/%d.png" % (top, e["ID"]), compress_type=zipfile.ZIP_STORED)
    print("wrote %s (%d films, %d cast, %.1f MB)" % (zpath, len(items["data"]), len(cast["data"]),
                                                    os.path.getsize(zpath) / 1e6))


if __name__ == "__main__":
    main()
