# Road to Doomsday

A two-player Marvel watch tracker, built to get through everything before
*Avengers: Doomsday*. One self-contained HTML file, no build step, no backend.

**84 titles:** 64 films and 20 series across the MCU, Fox's X-Men, Sony's
Spider-Man, and Marvel on Netflix.

## Features

- **Two independent scores per title.** Tap a 1 to 10 pip for each person;
  tap the same pip again to clear it. Scoring a title marks it watched.
- **Three orders.** Release order, per-universe timeline order, and a mixed
  "story year" order that interleaves everything by the year it is set in
  (1943 to 2029).
- **Filters** for universe (MCU / X-Men / Sony / Netflix), format (films or
  series), and watch state.
- **Leaderboard** ranking every scored title by your combined average.
- **Stats:** hours logged, each person's average, an agreement percentage,
  average score by saga, biggest disagreements, and a universe head to head.
- **Countdown** to Doomsday with the viewing pace needed to finish in time.
- Editable names, and export/import of your scores as JSON.

## Running it

Open `index.html` in any browser. That is the whole thing.

## Shared boards

By default the app is local: scores live in `localStorage`, in one browser on
one device. **Share with someone** creates a shared board, seeds it with your
current scores, and gives you a link like:

```
https://your-site.vercel.app/#r=39XJ-X3AV
```

Anyone who opens that link scores into the same board from any device. Edits
apply locally straight away, then sync; the pill in the toolbar shows
`Shared`, or `Not synced` if the connection drops. Edits made while offline
queue up and send when you are back, and a poll will never overwrite work that
has not been sent yet.

There is no login. **Anyone with the link can read and change that board**, so
treat it like a shared document. Boards expire after 400 days untouched, and
every edit refreshes that.

### Setting up sharing on Vercel

Sharing needs a Redis instance. Without one the site still works fine in local
mode, and the share button explains that it is unconfigured.

1. In the Vercel dashboard open your project, then **Storage**.
2. Add a **Redis** database (the Upstash integration under the Marketplace tab).
3. Connect it to the project and redeploy.

The integration sets `KV_REST_API_URL` and `KV_REST_API_TOKEN` automatically.
`UPSTASH_REDIS_REST_URL` / `UPSTASH_REDIS_REST_TOKEN` are read as a fallback,
so a direct Upstash account works too. The free tier is far more than this
needs.

### API

| Route | Method | Purpose |
| --- | --- | --- |
| `/api/room` | `POST` | Create a board, seeded from the posted state |
| `/api/room?code=…` | `GET` | Load a board |
| `/api/op` | `POST` | Apply edits: `score`, `watch`, `name`, `reset` |

Each board is three Redis hashes, with one field per person per title. Every
edit is a single atomic `HSET`/`HDEL`, so two people scoring at the same moment
cannot clobber each other and no merge step is needed.

## Posters

`posters/` holds one WebP per title, pulled from English Wikipedia's
`pageimages` API and downscaled to fit 240x380. The widest slot in the UI is
112px, so that still covers a 2x display while keeping the whole set near
1.5 MB. Straight from Wikipedia they were 6.7 MB, several of them PNGs, at
about 83 KB each for a thumbnail.

Refetch (for example when an upcoming title's poster is finally published):

```bash
pip install Pillow
python3 fetch_posters.py          # skips what already exists
python3 fetch_posters.py --force  # refetch everything
```

Any title without a poster falls back to a styled tile, so a missing image
never breaks the layout.

Wikipedia only ever returns the one image in a title's infobox, which is not
always the poster you would pick. To swap in a specific one:

```bash
python3 set_poster.py --list                       # every id and title
python3 set_poster.py sp2 ~/Downloads/poster.jpg   # local file
python3 set_poster.py sp2 https://.../poster.jpg   # or a direct image URL
```

It resizes and encodes to match the rest. `fetch_posters.py` will not
overwrite it afterwards, since it skips files that already exist; use
`--force` to go back to the Wikipedia default.
