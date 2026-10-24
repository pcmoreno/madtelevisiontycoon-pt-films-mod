# Pacote Português

A Mad Television Tycoon content mod: 80 Portuguese films (1981–2005) with their directors, cast and pictures.
Status on 5 October 2026: built, installed and working in game.

## Layout

| Folder | What's in it |
|---|---|
| `data/` | The source data. `films.json` (the 80 films), `people.json` (gender and death date per person), `genre_review.csv` (reviewed genres), `data_overrides.json` (owner changes to film values), `crop_overrides.json` (image crop fixes), `cast_ids.json` (generated: name+role → cast ID), `titles.csv` (approved parody titles: original language + English), `cast_names.csv` (approved parody names for the 194 cast entries), `image_prompts.csv` (lookalike-image pilot), `pacote-portugues.html` (handoff page) |
| `tools/` | The scripts, below. `tools/windows/` holds the player installer (Install.bat, install.ps1, ...) |
| `build/` | Generated mod files: `CastData.json`, `ItemsData.json`, `textures.json`, and `last_install.json` (the record of the last install) |
| `stills/stills/` | The downloaded TMDB stills and their manifest |
| `stills/png/` | The stills converted to the game's format: `<film ID>.png`, 640×480 |
| `stills/generated/` | Lookalike images from an image generator: `<film ID>-i2i.png` or `-t2i.png` |
| `.venv/` | Python environment with Pillow (only `convert_stills.py` needs it) |

## Rebuild and install

```bash
python3 tools/apply_genres.py              # after editing genre_review.csv or data_overrides.json
python3 tools/build_cast.py                # data/films.json + people.json -> build/CastData.json
python3 tools/build_items.py               # -> build/ItemsData.json
.venv/bin/python tools/convert_stills.py   # -> stills/png/ and stills/png/_contact.jpg
python3 tools/install_mod.py --dry-run     # preview
python3 tools/install_mod.py               # install into the game
python3 tools/install_mod.py --uninstall   # remove everything it added
```

For players (no Python needed): `python3 tools/package.py --version 1.0` builds `build/PacotePortugues-1.0.zip`
with the files from `tools/windows/` and our data only (no game data). Players extract it and double-click
`Install.bat`, which runs `install.ps1` (Windows PowerShell 5.1). It does the same merge, numbering and
safety checks as `install_mod.py`, uses the same install record, and either one can remove the other's install.

Re-run `install_mod.py` after every game update.

## Things to know

- The game reads `EXTERN/DATABASE/MOD/<file>` **instead of** `EXTERN/DATABASE/<file>`. So the installer writes the
  vanilla entries plus ours into `MOD/`. Installing only our entries froze a new game.
- Prefixed mod files (`MOD/<modname>_items.json` / `_cast.json`, what the MTT Mod Creator exports) are **not** loaded:
  tested 18 October 2026, none of our films appeared in two new games. So we can't run alongside other content mods.
- All our cast entries are `Disabled`, which keeps them out of the film studio's hiring pool; film credits still work.
- Images go into the game's own genre folders (`EXTERN/SCRN/<GENRE>/`), numbered straight after the vanilla ones.
  The game stops loading at the first missing number, so the numbering must have no gaps.
- The installer only deletes files it wrote and that are unchanged (checked by SHA-1).
- Pak tools used for research (repak, kismet-analyzer) are not part of the project. See the handoff page §2 for what
  was learned from the game's code.
