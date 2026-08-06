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

Scores are saved to `localStorage`, which means they live in **one browser on
one device**. Use the Export button to back them up or move them.

## Posters

`posters/` holds one image per title, pulled from English Wikipedia's
`pageimages` API. To refetch (for example when an upcoming title's poster is
finally published):

```bash
python3 fetch_posters.py          # skips what already exists
python3 fetch_posters.py --force  # refetch everything
```

Any title without a poster falls back to a styled tile, so a missing image
never breaks the layout.
