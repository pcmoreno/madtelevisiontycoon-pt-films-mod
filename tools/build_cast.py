"""Build the mod's cast file from data/films.json and data/people.json.

Writes:
  build/CastData.json  -> copy to EXTERN/DATABASE/MOD/CastData.json
  data/cast_ids.json   -> "<name>|<job>" -> ID, used by the items build for Credits

In-game names are the parodies in data/cast_names.csv (column suggested), like vanilla's "Stanley Kuprick";
the real name stays in _comment and in cast_ids.json.

Conventions copied from the vanilla CastData.json:
  - one entry per person per role: Job 0 director, Job 1 actor (a person who does both gets two IDs)
  - Gender 1 = female, omitted = male
  - Disabled true on everyone: keeps our people out of the studio hiring pool (owner's choice,
    2026-10-18). Vanilla disables 279 people, mostly dead (Hitchcock, Kubrick), and 277 of them are
    still credited on films, so credits keep working.
  - Rating follows the ratings of their films, using the vanilla fit
      director = 4.5 + 0.92 x mean film rating, actor = 18.6 + 0.63 x mean film rating
  - Genre = most common main genre among their films (ties: their highest-rated film)

Usage: python3 tools/build_cast.py
"""
import collections
import csv
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIRST_ID = 9_000_001
DIRECTOR, ACTOR = 0, 1
FIT = {DIRECTOR: (4.5, 0.92), ACTOR: (18.6, 0.63)}


def main():
    films = json.load(open(os.path.join(ROOT, "data", "films.json"), encoding="utf-8"))
    people = json.load(open(os.path.join(ROOT, "data", "people.json"), encoding="utf-8"))
    parody = {int(r["id"]): r for r in
              csv.DictReader(open(os.path.join(ROOT, "data", "cast_names.csv"), encoding="utf-8-sig"))}

    roles = collections.defaultdict(list)  # (name, job) -> films
    for f in films:
        for pos, name in enumerate(f["credits"]):
            roles[(name, DIRECTOR if pos == 0 else ACTOR)].append(f)

    missing = sorted({n for n, _ in roles} - set(people))
    if missing:
        raise SystemExit("No entry in data/people.json for: " + ", ".join(missing))

    # directors first, then actors, each alphabetical: stable IDs between runs
    keys = sorted(roles, key=lambda k: (k[1], k[0]))
    entries, ids = [], {}
    for n, (name, job) in enumerate(keys):
        fs = roles[(name, job)]
        person = people[name]
        a, b = FIT[job]
        rating = round(a + b * sum(f["rating"] for f in fs) / len(fs))
        counts = collections.Counter(f["gcode"] for f in fs)
        top = max(counts.values())
        genre = max((f for f in fs if counts[f["gcode"]] == top), key=lambda f: f["rating"])["gcode"]

        entry = {"ID": FIRST_ID + n, "_comment": name}
        if person["gender"] == "female":
            entry["Gender"] = 1
        row = parody[entry["ID"]]
        assert row["name"] == name, "cast_names.csv row %d is %r, the build has %r" % (entry["ID"], row["name"], name)
        entry.update(Job=job, Genre=genre, Rating=max(1, min(99, rating)), Name=row["suggested"])
        entry["Disabled"] = True
        entries.append(entry)
        ids["%s|%d" % (name, job)] = entry["ID"]

    os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
    with open(os.path.join(ROOT, "build", "CastData.json"), "w", encoding="utf-8") as fh:
        json.dump({"data": entries}, fh, ensure_ascii=False, indent="\t")
    with open(os.path.join(ROOT, "data", "cast_ids.json"), "w", encoding="utf-8") as fh:
        json.dump(ids, fh, ensure_ascii=False, indent=1)

    jobs = collections.Counter(e["Job"] for e in entries)
    print("%d entries (%d directors, %d actors), IDs %d-%d, %d disabled, %d female"
          % (len(entries), jobs[DIRECTOR], jobs[ACTOR], entries[0]["ID"], entries[-1]["ID"],
             sum(1 for e in entries if e.get("Disabled")), sum(1 for e in entries if e.get("Gender") == 1)))


if __name__ == "__main__":
    main()
