#!/usr/bin/env python3
"""
Replace one title's poster with an image you picked yourself.

fetch_posters.py takes whatever image sits in a title's Wikipedia infobox,
which is not always the poster you want. This swaps in a specific one and
matches the size and format the app expects.

    python3 set_poster.py sp2 ~/Downloads/spiderman2.jpg
    python3 set_poster.py sp2 https://example.com/poster.jpg
    python3 set_poster.py --list          # show every id and title

Save the image you want (right click, Save Image As) and point this at it.
Re-running fetch_posters.py will not overwrite it, since that skips files
that already exist. Use fetch_posters.py --force to go back to the default.

Requires Pillow:  pip install Pillow
"""

import io
import os
import re
import sys
import urllib.request

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "posters")
INDEX = os.path.join(HERE, "index.html")
MAX_BOX = (240, 380)
QUALITY = 82
UA = "mcu-watch-tracker/1.0 (personal use)"


def known_titles():
    """Read the id -> title map straight out of the app, so it cannot drift."""
    html = io.open(INDEX, encoding="utf-8").read()
    return dict(re.findall(r'\{id:"([a-z0-9]+)",\s*t:"([^"]+)"', html))


def load(source):
    if re.match(r"^https?://", source):
        req = urllib.request.Request(source, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            return Image.open(io.BytesIO(r.read()))
    return Image.open(os.path.expanduser(source))


def main():
    titles = known_titles()

    if "--list" in sys.argv or len(sys.argv) < 3:
        if "--list" in sys.argv:
            for fid, title in sorted(titles.items(), key=lambda kv: kv[1]):
                print("  %-8s %s" % (fid, title))
            return 0
        print(__doc__.strip())
        return 1

    fid, source = sys.argv[1], sys.argv[2]
    if fid not in titles:
        print("Unknown id %r. Run with --list to see them all." % fid)
        return 1

    try:
        im = load(source).convert("RGB")
    except Exception as e:
        print("Could not read that image: %s" % e)
        return 1

    original = im.size
    im.thumbnail(MAX_BOX, Image.LANCZOS)
    dest = os.path.join(OUT, fid + ".webp")
    im.save(dest, "WEBP", quality=QUALITY, method=6)

    print("%s (%s)" % (titles[fid], fid))
    print("  from   %dx%d" % original)
    print("  saved  %dx%d, %d KB -> %s"
          % (im.size[0], im.size[1], os.path.getsize(dest) // 1024, dest))
    if im.size[0] >= im.size[1]:
        print("  note   this is landscape, so the app will letterbox it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
