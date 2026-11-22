# Week 3 · Day 5 — Top 5 News Headlines Scraper

A small Python script that fetches [BBC News](https://www.bbc.com/news) and prints the top 5 headlines in the terminal.

**Tools:** Python, requests, BeautifulSoup

## How the headlines were found

Right-click a headline on bbc.com/news → **Inspect**. Each headline is:

```html
<h2 data-testid="card-headline" class="IndexCardHeading-styles__CardHeadlineStyled-...">...</h2>
```

The class names are auto-generated and change, so the script selects on the stable attribute:

```python
soup.select('h2[data-testid="card-headline"]')
```

Tested in the browser console first:

```js
[...document.querySelectorAll('h2[data-testid="card-headline"]')].slice(0, 5).map(h => h.innerText)
```

Section titles ("Most read", "Sport") use a different `data-testid`, so only real headlines are matched.

## What the script handles

- Sends a normal browser User-Agent header
- Checks the HTTP status code before parsing
- Strips whitespace, skips empty and duplicate headlines (the same story appears in "Top stories" and "Most read")
- Prints exactly 5, numbered 1–5; if fewer are found it prints what it has instead of crashing
- Network errors exit with a clear message

## Run it (macOS)

```bash
cd week-3-day-5-news-headlines
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python headlines.py
```

## Sample output

```
$ python headlines.py
1. COP31 climate talks end with no deal after fossil fuels row derails hopes of agreement
2. Explosion on Russian ship at Libya port caused by suspected drone attack, officials say
3. Premier League: Ngumoha adds Liverpool's third against 10-man Man Utd
4. Russia-bound ship towed away after it was attacked in Gulf of Finland
5. US Army to detonate tonnes of unstable explosives in Iowa despite court order
```

(Headlines change through the day.)

## If a site loads headlines with JavaScript

`requests` only gets the initial HTML, so JS-rendered headlines come back empty. Options: look in DevTools → Network for the JSON API the page calls and request that directly, use the site's RSS feed (e.g. `https://feeds.bbci.co.uk/news/rss.xml`), or render the page with a headless browser such as Playwright or Selenium.
