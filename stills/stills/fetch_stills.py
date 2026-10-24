#!/usr/bin/env python3
"""
Fetch one representative image per film from TMDB.

Preference order per title:
  1. Highest-rated backdrop (scene still)
  2. Highest-rated poster (fallback)
  3. Nothing -> logged in report.csv for manual sourcing

Usage:
    set TMDB_API_KEY=your_key_here      (Windows cmd)
    $env:TMDB_API_KEY="your_key_here"   (PowerShell)
    python fetch_stills.py

Get a free key at https://www.themoviedb.org/settings/api (v3 auth, "API Key").
Stdlib only - no pip install required.
"""

import csv
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

API = "https://api.themoviedb.org/3"
IMG = "https://image.tmdb.org/t/p/original"
KEY = os.environ.get("TMDB_API_KEY", "").strip()
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")
REPORT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "report.csv")

FILMS = [
    ("Conversa Acabada", 1981), ("Francisca", 1981), ("Kilas, o Mau da Fita", 1981),
    ("A Ilha dos Amores", 1982), ("A Vida É Bela?!", 1982), ("Silvestre", 1982),
    ("Crónica dos Bons Malandros", 1984), ("O Lugar do Morto", 1984),
    ("Le Soulier de Satin", 1985), ("Um Adeus Português", 1986),
    ("Uma Rapariga no Verão", 1986), ("Balada da Praia dos Cães", 1987),
    ("O Bobo", 1987), ("O Querido Lilás", 1987), ("Os Canibais", 1988),
    ("Tempos Difíceis", 1988), ("O Sangue", 1989), ("Recordações da Casa Amarela", 1989),
    ("Non, ou a Vã Glória de Mandar", 1990), ("A Divina Comédia", 1991),
    ("A Idade Maior", 1991), ("O Último Mergulho", 1992),
    ("Amor e Dedinhos de Pé", 1993), ("Vale Abraão", 1993), ("Casa de Lava", 1994),
    ("Três Irmãos", 1994), ("A Comédia de Deus", 1995), ("Adão e Eva", 1995),
    ("Corte de Cabelo", 1995), ("O Convento", 1995), ("Sinais de Fogo", 1995),
    ("Ossos", 1997), ("Tentação", 1997), ("Viagem ao Princípio do Mundo", 1997),
    ("Fintar o Destino", 1998), ("Os Mutantes", 1998), ("Pesadelo Cor de Rosa", 1998),
    ("Sapatos Pretos", 1998), ("Zona J", 1998), ("A Carta", 1999),
    ("As Bodas de Deus", 1999), ("Inferno", 1999), ("Jaime", 1999),
    ("Branca de Neve", 2000), ("Capitães de Abril", 2000), ("No Quarto da Vanda", 2000),
    ("O Fantasma", 2000), ("Palavra e Utopia", 2000), ("Peixe-Lua", 2000),
    ("A Raiz do Coração", 2001), ("Camarate", 2001), ("Ganhar a Vida", 2001),
    ("Rasganço", 2001), ("Vou Para Casa", 2001), ("Água e Sal", 2001),
    ("A Jangada de Pedra", 2002), ("A Selva", 2002), ("O Delfim", 2002),
    ("O Princípio da Incerteza", 2002), ("A Mulher Polícia", 2003),
    ("Os Imortais", 2003), ("Quaresma", 2003), ("Um Filme Falado", 2003),
    ("Vai~e~Vem", 2003), ("A Cara que Mereces", 2004), ("A Costa dos Murmúrios", 2004),
    ("André Valente", 2004), ("Kiss Me", 2004), ("Lá Fora", 2004),
    ("Noite Escura", 2004), ("O Milagre Segundo Salomé", 2004),
    ("O Quinto Império", 2004), ("Portugal S.A.", 2004), ("Sorte Nula", 2004),
    ("Adriana", 2005), ("Alice", 2005), ("O Crime do Padre Amaro", 2005),
    ("O Fatalista", 2005), ("Odete", 2005), ("Um Tiro no Escuro", 2005),
]


def get(path, **params):
    params["api_key"] = KEY
    url = "%s%s?%s" % (API, path, urllib.parse.urlencode(params))
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(2 ** attempt)
                continue
            if e.code == 404:
                return None
            raise
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)
    return None


def pick_movie(title, year):
    """Search TMDB, prefer Portuguese-origin release matching the year."""
    for lang in ("pt-PT", "en-US"):
        res = get("/search/movie", query=title, year=year, language=lang)
        if not res or not res.get("results"):
            continue
        cands = res["results"]
        scored = []
        for c in cands:
            rd = (c.get("release_date") or "")[:4]
            score = 0
            if rd.isdigit() and abs(int(rd) - year) <= 1:
                score += 10
            if c.get("original_language") == "pt":
                score += 5
            score += min(c.get("popularity", 0), 5)
            scored.append((score, c))
        scored.sort(key=lambda x: -x[0])
        if scored and scored[0][0] >= 10:
            return scored[0][1]
    # last resort: drop anything after a comma and retry once
    if "," in title:
        return pick_movie(title.split(",")[0].strip(), year)
    return None


def pick_image(movie_id):
    """Return (kind, file_path) - backdrop preferred, poster as fallback."""
    imgs = get("/movie/%d/images" % movie_id, include_image_language="null,pt,en")
    if not imgs:
        return None, None
    for kind in ("backdrops", "posters"):
        pool = imgs.get(kind) or []
        if pool:
            pool.sort(key=lambda i: (i.get("vote_average", 0), i.get("width", 0)), reverse=True)
            return kind[:-1], pool[0]["file_path"]
    return None, None


def safe(name):
    return re.sub(r'[<>:"/\\|?*]', "-", name).strip().rstrip(".")


def main():
    if not KEY:
        sys.exit("TMDB_API_KEY is not set. See the docstring at the top of this file.")
    os.makedirs(OUT, exist_ok=True)
    rows = []
    for idx, (title, year) in enumerate(FILMS, 1):
        print("[%2d/%d] %s (%d)" % (idx, len(FILMS), title, year), flush=True)
        kind = url = fname = ""
        tmdb_id = ""
        try:
            m = pick_movie(title, year)
            if m:
                tmdb_id = m["id"]
                kind, path = pick_image(m["id"])
                if path:
                    url = IMG + path
                    ext = os.path.splitext(path)[1] or ".jpg"
                    fname = "%d - %s%s" % (year, safe(title), ext)
                    dest = os.path.join(OUT, fname)
                    if not os.path.exists(dest):
                        urllib.request.urlretrieve(url, dest)
                    print("        -> %s (%s)" % (fname, kind))
                else:
                    print("        -> matched, but no images on TMDB")
            else:
                print("        -> NO MATCH")
        except Exception as e:
            print("        -> ERROR: %s" % e)
            kind = "error"
        rows.append({
            "title": title, "year": year, "tmdb_id": tmdb_id,
            "image_type": kind or "none", "file": fname, "source_url": url,
        })
        time.sleep(0.3)

    with open(REPORT, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    stills = sum(1 for r in rows if r["image_type"] == "backdrop")
    posters = sum(1 for r in rows if r["image_type"] == "poster")
    none = len(rows) - stills - posters
    print("\nDone. %d scene stills, %d posters, %d unresolved." % (stills, posters, none))
    print("Images: %s\nReport: %s" % (OUT, REPORT))


if __name__ == "__main__":
    main()
