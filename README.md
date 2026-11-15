# Europe, four seasons

A trip-planning app with four seasonal guides to Europe (4,036 ideas across 44 countries).
Mark each idea Keep, Maybe or Skip in the card view, a swipe deck or on a map. Everything saves on the device as you go,
and the whole thing works offline once installed.

- `src/` holds the app template, the idea data and the offline map outline.
- `tools/fetch_photos.py` downloads one photo per idea from Wikipedia (runs on GitHub Actions).
- `tools/build.py` assembles `site/`, which GitHub Pages publishes.

Photos come from Wikipedia and Wikimedia Commons; each card links to its Wikipedia article.
