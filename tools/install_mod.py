"""Install (or remove) the Portuguese films mod in a Mad Television Tycoon install.

What it does:
  1. Removes the images of a previous install, using the record it left in DATABASE/MOD/.
     An image is only deleted if it is still byte-identical to ours, so a vanilla image that a
     game update put at the same number is never touched.
  2. Counts the vanilla images in each SCRN/<GENRE>/ folder and numbers ours straight after them.
     The game loads 0001.png, 0002.png, ... so the numbering must have no gaps.
  3. Copies the images in and writes DATABASE/MOD/ItemsData.json and CastData.json, then saves
     the install record.

The game reads DATABASE/MOD/<file> INSTEAD of DATABASE/<file> when it exists (BP_LoadData only
falls back to the vanilla file when the mod file fails to load). So the mod files must hold the
full vanilla data plus ours: this script merges the install's current vanilla ItemsData.json /
CastData.json with build/, and refuses if an ID would clash.
Tested 18 October 2026: the game does NOT load prefixed mod files (MOD/<modname>_items.json and
_cast.json, the format the MTT Mod Creator exports): none of our films appeared in two new games.
So several content mods cannot be installed side by side; whichever writes these two files wins.

The install record (every file written, with its SHA-1) is saved twice: in DATABASE/MOD/ and in
build/last_install.json in the project. If the game-side copy is lost, the project copy is used,
as long as it was made for the same EXTERN folder.

Re-run it after every game update: the update may add images, reset the folders, or change the
vanilla database that the merged files carry.
It refuses to overwrite DATABASE/MOD/ItemsData.json or CastData.json that another mod wrote.

Needs only the Python standard library, so it runs from WSL or from Windows Python.
Build first: tools/build_cast.py, tools/build_items.py, tools/convert_stills.py.

Usage:
  python3 tools/install_mod.py [--extern PATH] [--dry-run]
  python3 tools/install_mod.py --uninstall [--extern PATH] [--dry-run]
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_EXTERN = "/mnt/c/Program Files (x86)/Steam/steamapps/common/Mad Television Tycoon/MadTelevisionTycoon/EXTERN"
if os.name == "nt":
    DEFAULT_EXTERN = r"C:\Program Files (x86)\Steam\steamapps\common\Mad Television Tycoon\MadTelevisionTycoon\EXTERN"
RECORD = "pt_films_install.json"
OTHER_RECORDS = ("PacotePortugues_install.txt",)  # left by the prefixed-files trial install
PROJECT_RECORD = os.path.join(ROOT, "build", "last_install.json")
MOD_FILES = ("ItemsData.json", "CastData.json")
FOLDER = {0: "ACTION", 1: "DRAMA", 2: "SCIFI", 3: "ROMANTIC", 4: "FANTASY", 5: "CRIME", 6: "THRILLER",
          7: "HORROR", 8: "MYSTERY", 9: "ADVENTURE", 10: "FAMILY", 11: "DOCU", 14: "ANTIWAR",
          15: "WESTERN", 16: "COMEDY", 27: "CARTOON", 28: "EROTIC", 29: "HISTORICAL"}


def sha1(path):
    h = hashlib.sha1()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_lenient(path):
    """Vanilla database files contain trailing commas, which the game tolerates and json does not."""
    text = open(path, encoding="utf-8-sig").read()
    return json.loads(re.sub(r",(\s*[\]}])", r"\1", text))


def merge(vanilla_path, ours, what):
    vanilla = load_lenient(vanilla_path)["data"]
    clash = {e.get("ID") for e in vanilla} & {e["ID"] for e in ours}
    if clash:
        sys.exit("%s: our IDs clash with vanilla IDs %s. Change FIRST_ID in the build scripts."
                 % (what, sorted(clash)[:10]))
    return {"data": vanilla + ours}, len(vanilla)


def numbered_pngs(folder):
    """Numbers of the NNNN.png files in a folder."""
    out = set()
    for f in os.listdir(folder):
        stem, ext = os.path.splitext(f)
        if ext.lower() == ".png" and stem.isdigit():
            out.add(int(stem))
    return out


class Installer:
    def __init__(self, extern, dry_run):
        self.extern = extern
        self.dry = dry_run
        self.mod_dir = os.path.join(extern, "DATABASE", "MOD")
        self.scrn = os.path.join(extern, "SCRN")
        self.record_path = os.path.join(self.mod_dir, RECORD)

    def act(self, msg, fn, *args):
        print(("[dry-run] " if self.dry else "") + msg)
        if not self.dry:
            fn(*args)

    def load_record(self):
        for name in (RECORD,) + OTHER_RECORDS:
            path = os.path.join(self.mod_dir, name)
            if os.path.exists(path):
                return json.load(open(path, encoding="utf-8"))
        if os.path.exists(PROJECT_RECORD):
            record = json.load(open(PROJECT_RECORD, encoding="utf-8"))
            if os.path.normcase(os.path.abspath(record.get("extern", ""))) == os.path.normcase(os.path.abspath(self.extern)):
                print("No install record in DATABASE/MOD/: using the project copy, build/last_install.json")
                return record
        return None

    def is_ours(self, name, record):
        """True if DATABASE/MOD/<name> is the file our last install wrote."""
        path = os.path.join(self.mod_dir, name)
        known = (record or {}).get("mod_files", {}).get(name)
        return known is not None and sha1(path) == known

    def remove_previous(self, record):
        """Delete our images and mod files from a previous install. Returns {folder: set of freed numbers}."""
        freed = {}
        kept = 0
        for img in record.get("images", []):
            path = os.path.join(self.scrn, img["folder"], img["file"])
            if os.path.exists(path) and sha1(path) == img["sha1"]:
                freed.setdefault(img["folder"], set()).add(int(img["file"][:-4]))
                if not self.dry:
                    os.remove(path)
            elif os.path.exists(path):
                kept += 1  # a game update replaced it with a vanilla image: leave it alone
        print("%sremoved %d images from the previous install%s" % (
            "[dry-run] " if self.dry else "", sum(len(v) for v in freed.values()),
            ", left %d that a game update replaced" % kept if kept else ""))
        # mod_files lists what that install wrote (it may be other file names than MOD_FILES)
        records = (RECORD,) + OTHER_RECORDS
        for name in list(record.get("mod_files", {})) + list(records):
            path = os.path.join(self.mod_dir, name)
            if not os.path.exists(path):
                continue
            if name not in records and not self.is_ours(name, record):
                print("left DATABASE/MOD/%s: it is not the file this mod installed" % name)
                continue
            self.act("remove DATABASE/MOD/" + name, os.remove, path)
        return freed

    def check_foreign_mod(self, record):
        foreign = [n for n in MOD_FILES
                   if os.path.exists(os.path.join(self.mod_dir, n)) and not self.is_ours(n, record)]
        if foreign:
            sys.exit("DATABASE/MOD/ already holds %s from another mod. This installer will not overwrite it.\n"
                     "Move those files aside (or merge them by hand), then run again." % ", ".join(foreign))

    def install(self):
        if not os.path.isdir(self.scrn) or not os.path.isdir(self.mod_dir):
            sys.exit("Not a game EXTERN folder (no SCRN/ or DATABASE/MOD/): " + self.extern)
        items_path = os.path.join(ROOT, "build", "ItemsData.json")
        cast_path = os.path.join(ROOT, "build", "CastData.json")
        png_dir = os.path.join(ROOT, "stills", "png")
        for p in (items_path, cast_path):
            if not os.path.exists(p):
                sys.exit("Missing %s. Run the build scripts first." % p)
        items = json.load(open(items_path, encoding="utf-8"))

        record = self.load_record()
        self.check_foreign_mod(record)
        freed = self.remove_previous(record) if record else {}

        # vanilla images = what is in the folder minus what we just removed
        next_num = {}
        images = []
        for item in items["data"]:
            folder = FOLDER[item["Genre"]]
            src = os.path.join(png_dir, "%d.png" % item["ID"])
            if not os.path.exists(src):
                sys.exit("Missing image for %s: %s. Run tools/convert_stills.py." % (item["_comment"], src))
            if folder not in next_num:
                path = os.path.join(self.scrn, folder)
                if not os.path.isdir(path):
                    sys.exit("The game has no SCRN/%s folder." % folder)
                vanilla = numbered_pngs(path) - freed.get(folder, set())
                expected = set(range(1, len(vanilla) + 1))
                if vanilla != expected:
                    sys.exit("SCRN/%s has gaps or extra files in its numbering (%d files, highest %s). "
                             "Check the folder before installing." % (folder, len(vanilla), max(vanilla, default=0)))
                next_num[folder] = len(vanilla) + 1
            num = next_num[folder]
            next_num[folder] += 1
            item["Texture"] = num
            images.append({"id": item["ID"], "folder": folder, "file": "%04d.png" % num, "src": src})

        for img in images:
            dest = os.path.join(self.scrn, img["folder"], img["file"])
            if not self.dry:
                shutil.copyfile(img["src"], dest)
            img["sha1"] = sha1(img["src"])
            del img["src"]
        print("%s%d images: %s" % ("[dry-run] would copy " if self.dry else "copied ", len(images), ", ".join(
            "%s %04d-%04d" % (f, min(int(i["file"][:-4]) for i in images if i["folder"] == f), n - 1)
            for f, n in sorted(next_num.items()))))

        def write_json(path, data):
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent="\t")

        db = os.path.join(self.extern, "DATABASE")
        merged_items, n_items = merge(os.path.join(db, "ItemsData.json"), items["data"], "ItemsData")
        cast = json.load(open(cast_path, encoding="utf-8"))
        merged_cast, n_cast = merge(os.path.join(db, "CastData.json"), cast["data"], "CastData")
        self.act("write DATABASE/MOD/ItemsData.json (%d vanilla entries + %d films)" % (n_items, len(items["data"])),
                 write_json, os.path.join(self.mod_dir, "ItemsData.json"), merged_items)
        self.act("write DATABASE/MOD/CastData.json (%d vanilla entries + %d cast)" % (n_cast, len(cast["data"])),
                 write_json, os.path.join(self.mod_dir, "CastData.json"), merged_cast)
        record = {"mod": "Pacote Português", "extern": os.path.abspath(self.extern), "images": images,
                  "mod_files": {}}
        if not self.dry:  # hash what was actually written
            for name in MOD_FILES:
                record["mod_files"][name] = sha1(os.path.join(self.mod_dir, name))
        self.act("write DATABASE/MOD/" + RECORD, write_json, self.record_path, record)
        self.act("write build/last_install.json (project copy of the record)", write_json, PROJECT_RECORD, record)
        print("Done." if not self.dry else "Dry run only: nothing was written.")

    def uninstall(self):
        record = self.load_record()
        if record is None:
            sys.exit("No install record in DATABASE/MOD/: nothing to remove.")
        self.remove_previous(record)
        if os.path.exists(PROJECT_RECORD):
            self.act("remove build/last_install.json", os.remove, PROJECT_RECORD)
        print("Done." if not self.dry else "Dry run only: nothing was removed.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--extern", default=DEFAULT_EXTERN, help="the game's EXTERN folder")
    ap.add_argument("--dry-run", action="store_true", help="show what would happen, change nothing")
    ap.add_argument("--uninstall", action="store_true", help="remove the mod")
    args = ap.parse_args()
    inst = Installer(args.extern, args.dry_run)
    inst.uninstall() if args.uninstall else inst.install()


if __name__ == "__main__":
    main()
