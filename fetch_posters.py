#!/usr/bin/env python3
"""
Downloads one poster per title into ./posters/<id>.webp

Source: English Wikipedia's pageimages API (no key, no signup).
Re-run it any time; files already on disk are skipped unless you pass --force.
Useful later for titles whose poster wasn't published yet.

Images are downscaled to fit MAX_BOX and saved as WebP. The widest slot in the
UI is 112px, so 240px still covers a 2x display while keeping the whole set
around 1.5 MB instead of 6.7 MB.

Requires Pillow:  pip install Pillow

    python3 fetch_posters.py
    python3 fetch_posters.py --force
"""

import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "posters")
UA = "mcu-watch-tracker/1.0 (personal use)"
WIDTH = 500              # ask Wikipedia for this, then downscale locally
MAX_BOX = (240, 380)     # what actually ships
QUALITY = 82

# app id -> Wikipedia article title
FILMS = [
    ("im1",   "Iron Man (2008 film)"),
    ("hulk",  "The Incredible Hulk (film)"),
    ("im2",   "Iron Man 2"),
    ("thor",  "Thor (film)"),
    ("cap1",  "Captain America: The First Avenger"),
    ("av1",   "The Avengers (2012 film)"),
    ("im3",   "Iron Man 3"),
    ("thor2", "Thor: The Dark World"),
    ("cap2",  "Captain America: The Winter Soldier"),
    ("gotg",  "Guardians of the Galaxy (film)"),
    ("av2",   "Avengers: Age of Ultron"),
    ("am1",   "Ant-Man (film)"),
    ("cap3",  "Captain America: Civil War"),
    ("ds1",   "Doctor Strange (2016 film)"),
    ("gotg2", "Guardians of the Galaxy Vol. 2"),
    ("sm1",   "Spider-Man: Homecoming"),
    ("thor3", "Thor: Ragnarok"),
    ("bp1",   "Black Panther (film)"),
    ("av3",   "Avengers: Infinity War"),
    ("am2",   "Ant-Man and the Wasp"),
    ("cm",    "Captain Marvel (film)"),
    ("av4",   "Avengers: Endgame"),
    ("sm2",   "Spider-Man: Far From Home"),
    ("bw",    "Black Widow (2021 film)"),
    ("sc",    "Shang-Chi and the Legend of the Ten Rings"),
    ("et",    "Eternals (film)"),
    ("sm3",   "Spider-Man: No Way Home"),
    ("ds2",   "Doctor Strange in the Multiverse of Madness"),
    ("thor4", "Thor: Love and Thunder"),
    ("bp2",   "Black Panther: Wakanda Forever"),
    ("am3",   "Ant-Man and the Wasp: Quantumania"),
    ("gotg3", "Guardians of the Galaxy Vol. 3"),
    ("marv",  "The Marvels"),
    ("dw",    "Deadpool & Wolverine"),
    ("cap4",  "Captain America: Brave New World"),
    ("tb",    "Thunderbolts*"),
    ("ff",    "The Fantastic Four: First Steps"),
    ("sm4",   "Spider-Man: Brand New Day"),

    # Fox X-Men
    ("xm1",   "X-Men (film)"),
    ("xm2",   "X2 (film)"),
    ("xm3",   "X-Men: The Last Stand"),
    ("xmo",   "X-Men Origins: Wolverine"),
    ("xmfc",  "X-Men: First Class"),
    ("wolv",  "The Wolverine (film)"),
    ("dofp",  "X-Men: Days of Future Past"),
    ("dp1",   "Deadpool (film)"),
    ("xmap",  "X-Men: Apocalypse"),
    ("logan", "Logan (film)"),
    ("dp2",   "Deadpool 2"),
    ("dkph",  "Dark Phoenix (film)"),
    ("nmut",  "The New Mutants (film)"),

    # Sony Spider-Man
    ("sp1",   "Spider-Man (2002 film)"),
    ("sp2",   "Spider-Man 2"),
    ("sp3",   "Spider-Man 3"),
    ("tas1",  "The Amazing Spider-Man (2012 film)"),
    ("tas2",  "The Amazing Spider-Man 2"),
    ("ven1",  "Venom (2018 film)"),
    ("itsv",  "Spider-Man: Into the Spider-Verse"),
    ("ven2",  "Venom: Let There Be Carnage"),
    ("morb",  "Morbius (film)"),
    ("atsv",  "Spider-Man: Across the Spider-Verse"),
    ("ven3",  "Venom: The Last Dance"),
    ("mweb",  "Madame Web (film)"),
    ("krav",  "Kraven the Hunter (film)"),

    # Disney+ MCU series
    ("dwv",    "WandaVision"),
    ("dfws",   "The Falcon and the Winter Soldier"),
    ("dloki1", "Loki (season 1)"),
    ("dwi1",   "What If...? (season 1)"),
    ("dmm",    "Ms. Marvel (TV series)"),
    ("dsi",    "Secret Invasion (miniseries)"),
    ("dloki2", "Loki (season 2)"),
    ("dwi2",   "What If...? (season 2)"),
    ("dagath", "Agatha All Along"),
    ("dwi3",   "What If...? (season 3)"),
    ("ddba1",  "Daredevil: Born Again"),
    ("dih",    "Ironheart (TV series)"),
    ("dvq",    "Vision Quest (TV series)"),
    ("ddba2",  "Daredevil: Born Again season 2"),

    # X-Men animated
    ("xm97",   "X-Men '97"),

    # Netflix
    ("nfdd1",  "Daredevil (season 1)"),
    ("nfdd2",  "Daredevil (season 2)"),
    ("nfdd3",  "Daredevil (season 3)"),
    ("nfpun1", "The Punisher (season 1)"),
    ("nfpun2", "The Punisher (season 2)"),
]


def get(url, tries=6):
    """Wikimedia throttles bursts, so back off and retry on 429/5xx."""
    delay = 2.0
    for attempt in range(tries):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or attempt == tries - 1:
                raise
            wait = float(e.headers.get("Retry-After") or delay)
            time.sleep(min(wait, 30))
            delay *= 2


def poster_urls(titles):
    """One batched lookup for up to 50 titles. Posters are non-free files, so
    pilicense=any is required; the default (free) returns nothing for them."""
    out = {}
    for i in range(0, len(titles), 40):
        chunk = titles[i:i + 40]
        q = urllib.parse.urlencode({
            "action": "query",
            "titles": "|".join(chunk),
            "prop": "pageimages",
            "piprop": "thumbnail",
            "pilicense": "any",
            "pilimit": len(chunk),
            "pithumbsize": WIDTH,
            "format": "json",
            "formatversion": "2",
            "redirects": "1",
        })
        data = json.loads(get("https://en.wikipedia.org/w/api.php?" + q))
        query = data.get("query", {})

        # follow redirects/normalisation so we can map back to requested titles
        alias = {}
        for key in ("normalized", "redirects"):
            for r in query.get(key, []):
                alias[r["from"]] = r["to"]

        by_title = {}
        for p in query.get("pages", []):
            src = (p.get("thumbnail") or {}).get("source")
            if src:
                by_title[p.get("title")] = src

        for t in chunk:
            resolved = t
            for _ in range(3):
                resolved = alias.get(resolved, resolved)
            if resolved in by_title:
                out[t] = by_title[resolved]
        time.sleep(1)
    return out


def main():
    force = "--force" in sys.argv
    os.makedirs(OUT, exist_ok=True)
    got = skipped = 0
    missing = []

    todo = [(fid, title) for fid, title in FILMS
            if force or not os.path.exists(os.path.join(OUT, fid + ".webp"))]
    skipped = len(FILMS) - len(todo)
    if not todo:
        print("All %d posters already present. Use --force to refetch." % len(FILMS))
        return

    urls = poster_urls([t for _, t in todo])

    for fid, title in todo:
        dest = os.path.join(OUT, fid + ".webp")
        url = urls.get(title)
        if not url:
            missing.append((fid, title, "no poster on the article yet"))
            print("  miss  %-6s %s" % (fid, title))
            continue
        try:
            im = Image.open(io.BytesIO(get(url))).convert("RGB")
            im.thumbnail(MAX_BOX, Image.LANCZOS)
            im.save(dest, "WEBP", quality=QUALITY, method=6)
            got += 1
            print("  ok    %-6s %-46s %dx%d %dKB"
                  % (fid, title, im.size[0], im.size[1], os.path.getsize(dest) // 1024))
        except Exception as e:
            if os.path.exists(dest):
                os.remove(dest)
            missing.append((fid, title, str(e)))
            print("  fail  %-6s %s  (%s)" % (fid, title, e))
        time.sleep(0.4)

    print("\n%d downloaded, %d already present, %d missing" % (got, skipped, len(missing)))
    if missing:
        print("The app shows a styled fallback tile for these:")
        for fid, title, why in missing:
            print("  %-6s %s  (%s)" % (fid, title, why))


if __name__ == "__main__":
    main()
