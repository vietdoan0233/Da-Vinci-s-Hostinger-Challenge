# Architecture and build plan

Challenge: Hostinger "Decode the Noise" at Junction. A panel that opens next to a
social media post and shows which manipulation techniques it uses, how bot-like
the author is, and who else posted the same thing.

Hard requirement from the brief: a public URL on Hostinger infrastructure that
judges can open. Judges weigh honest detection logic and false-positive handling
above front-end polish.

## Decisions

| Decision | Choice | Why |
|---|---|---|
| Data source | Bluesky public API | Post history, account age, follower counts and search without scraping or paid keys. X and Instagram would cost the whole weekend in scraping. |
| Fallback input | Pasted text, any platform | Techniques still work; bot and similar sections show "not enough data". |
| Backend | Python, FastAPI, one process | `bot_score.py` is already Python. |
| LLM | Hostinger AI Router through the OpenAI SDK | Free credits, required-ish by the sponsor. Model set by env var. |
| Technique list | The 20 text techniques of SemEval-2021 Task 6 | Fixed, published list with a labelled corpus of short meme texts, closer to posts than the 2020 news-article corpus. Public on GitHub without registration, labelled test set of 200. |
| Similar posts | Bluesky search + word-shingle overlap (`bot_score.similarity`) | No embeddings, no vector database. |
| Storage | One SQLite file as a cache | Saves LLM credits on repeat views. Nothing else needs persisting. |
| Front end | One static page + one shared `panel.js`, no framework, no build step | The same panel renders on the web page and inside the extension. |
| Extension | Chrome MV3 content script on `bsky.app` | The "window next to the post". Loaded unpacked for the demo. |
| Deploy | Docker Compose on the Hostinger VPS, Traefik (already on the VPS) for HTTPS | The extension runs on an https page, so the API must be https. |

Not verified yet, check in the step that needs it:
- The AI Router base URL and model names (step 1.1).
- Whether Bluesky `app.bsky.feed.searchPosts` works without login from the VPS (step 4.1). It works on `api.bsky.app` from a home connection (checked 2026-11-14); `public.api.bsky.app` returns 403 for search. Recheck from the VPS; if refused, log in with an app password.
- ~~Whether the SemEval corpus can be downloaded without registration (step 5.1).~~ Yes: the 2021 Task 6 corpus is public at github.com/di-dimitrov/SEMEVAL-2021-task6-corpus.

## Components

```
 bsky.app page                     Hostinger VPS (Docker Compose)
┌──────────────────┐              ┌──────────────────────────────────────────┐
│ extension/       │   HTTPS      │ Traefik ─► FastAPI (app/main.py)          │
│  content.js      ├─────────────►│            ├─ techniques.py ─► AI Router │
│  panel.js        │              │            ├─ bluesky.py   ─► Bluesky API│
└──────────────────┘              │            ├─ bot_score.py               │
 Judge's browser                  │            ├─ similar.py                 │
┌──────────────────┐              │            └─ cache.py     ─► SQLite     │
│ web/index.html   ├─────────────►│  also serves web/ and eval/results.json  │
│  panel.js        │              └──────────────────────────────────────────┘
└──────────────────┘
```

## Folder layout

```
app/main.py         routes, rate limit, static files
app/llm.py          AI Router client
app/techniques.py   prompt, technique list, output validation
app/bluesky.py      URL -> post, author, author's recent posts, search
app/bot_score.py    moved from the repo root in step 0.1
app/similar.py      candidate search + overlap ranking
app/coverage.py     claim -> Oxylabs search + scrape -> quoted points from live pages
app/cache.py        SQLite get/set
web/index.html      paste box + panel
web/panel.js        renders an analysis into a DOM node (shared with extension)
web/panel.css       styles for the panel (shared with extension)
web/metrics.html    precision and false-positive numbers
extension/          manifest.json, content.js, copy of panel.js
eval/               labelled data, run scripts, results.json
tests/
Dockerfile, compose.yml, .env.example
```

## API contract

One endpoint. Every feature fills in one section of the same response, so the
front end never changes shape and unfinished sections are simply `null`.

`POST /api/analyze` with `{"url": "..."}` or `{"text": "..."}`

```json
{
  "post":       {"text": "", "author": "", "url": "", "ts": 0},
  "techniques": [{"name": "", "quote": "", "why": ""}],
  "bot":        {"score": 0.0, "verdict": "", "checked": [], "reasons": []},
  "similar":    [{"author": "", "text": "", "url": "", "ts": 0, "overlap": 0.0}],
  "coverage":   {"claim": {"quote": "", "statement": "", "query": ""},
                 "points": [{"source": "S1", "stance": "supports | challenges | adds context", "quote": "", "text": ""}],
                 "sources": [{"id": "S1", "title": "", "url": "", "domain": "", "read": true}],
                 "by_country": [{"country": "FI", "name": "Finland", "sources": [{"title": "", "url": "", "domain": ""}]}],
                 "checked_at": 0},
  "sides":      null,
  "errors":     {"bot": "author history unavailable"}
}
```

A section that fails goes into `errors` and the rest still returns.

`GET /api/health` returns `{"ok": true, "version": "<git sha>"}`.

`GET /api/replies?url=<post link>&offset=0` returns one page of ten direct replies, most liked first:

```json
{
  "replies": [{"post": {"text": "", "author": "", "name": "", "avatar": "", "url": "", "ts": 0, "likes": 0, "replies": 0},
               "bot": {"score": 0.0, "verdict": "", "checked": [], "reasons": []},
               "techniques": null,
               "errors": {}}],
  "total": 0, "next": 10, "errors": {}
}
```

`techniques` is `null` when the reply was not scanned and a list when it was. `next` is `null` on the last page.

## Rules that hold across features

- Every verdict carries a reason a non-expert can read. No bare numbers.
- No evidence is "not enough data", never a clean result.
- The bot number is called the "bot-likeness score". It is uncalibrated, so never "bot probability".
- The panel says "techniques found in this post", never "this post is propaganda".
- Post text is untrusted input to the LLM: it goes in a delimited data block, and the output is validated before display.

## Bot-likeness score

Implemented in `bot_score.py`. Each signal is a detection with a score, a
confidence and a reason.

```
category = 1 - PRODUCT(1 - score_i * confidence_i)      over detections in it
score    = 0.30*cadence + 0.30*text_reuse + 0.20*profile + 0.10*rate + 0.10*declared
floor 0.9 if the bio self-declares a bot
floor 0.6 if two of (cadence, text_reuse, rate) are each >= 0.4
>= 0.6 likely automated or coordinated, >= 0.3 some bot-like signals
```

Cadence, rate, text reuse, the aggregation and the floors are ported from FCaptcha.

The profile category is one logistic formula, emitted as a single detection when
it reaches 0.2. With `age` = account age in days (at least 1) and each sub-score
clipped to 0..1:

```
s_freq     = log10((total_posts/age) / 10) / log10(15)     0 at 10 posts/day, 1 at 150
s_friend   = log10((following/age) / 5) / log10(20)        0 at 5 follows/day, 1 at 100
s_ratio    = 1 - (followers/following) / 0.5               only if following >= 50
s_digits   = (digits in handle - 2) / 4
s_new      = 1 - age/90
s_nobio, s_noavatar, verified = 0 or 1

z = -3.0 + 2.0*s_freq + 1.5*s_friend + 1.2*s_ratio + 1.2*s_new
         + 1.0*s_digits + 0.6*s_nobio + 0.6*s_noavatar - 2.0*verified
profile_score = 1 / (1 + e^-z)
confidence    = (weights of features that had data) / 8.1
```

A clean account gives about 0.05, any single feature at maximum stays under 0.3,
all at maximum gives about 0.99. A missing field contributes 0.

Honesty notes for the pitch and the metrics page:
- The feature list comes from the BotometerLite paper (Yang, Varol, Hui, Menczer, AAAI 2020). Their model is closed; the weights above are hand-set by us.
- Not validated on labelled data. The upgrade path is fitting these weights on TwiBot-20/22.
- Skipped on purpose: BotometerLite's handle-likelihood (needs a bigram table of real handles) and likes growth rate (most platforms hide it).

## Build order

Each feature is its own branch and its own deploy. "Shipped" means it is live on
the public URL and checked there by hand. Features 5 and 6 can run in parallel
with two people. Hour figures are guesses.

### Feature 0: skeleton live on Hostinger (about 1.5 h)

- [x] 0.1 Repo already initialised here. Move `bot_score.py` to `app/`. Add `.gitignore` with `.env`, `*.db`, `__pycache__`.
- [x] 0.2 `requirements.txt`: fastapi, uvicorn, httpx, openai, pytest. Nothing else.
- [x] 0.3 `app/main.py`: `GET /api/health`, and `POST /api/analyze` returning the contract above with every section `null`. Validate input: exactly one of `url` or `text`, text at most 5000 characters.
- [x] 0.4 `web/index.html`: text box, Analyze button, raw JSON printed below. Served by FastAPI.
- [x] 0.5 `tests/test_api.py`: health returns ok; analyze rejects empty and oversized input.
- [x] 0.6 `Dockerfile`, `compose.yml` (app, Traefik labels), `.env.example`.
- [x] 0.7 Point the free domain at the VPS, `docker compose up -d` on the VPS.
- [ ] Done when: `https://<domain>/api/health` returns ok from a phone on mobile data.

### Feature 1: name the technique (about 2 h)

- [ ] 1.1 `app/llm.py`: one function `ask_json(system, user) -> dict` using the OpenAI SDK against `AI_ROUTER_BASE_URL`. 30 s timeout, one retry. Code done and checked against a local fake server; **still to do: confirm the base URL and a working model name with a one-line call using the team key.**
- [x] 1.2 `app/techniques.py`: the 20 SemEval-2021 Task 6 text technique names, verbatim from the corpus, with a one-sentence definition each.
- [x] 1.3 Prompt: definitions, then the post inside a delimited block marked as data. Ask for JSON `[{name, quote, why}]`, where `quote` is copied exactly from the post and `why` is one plain sentence. Allow an empty list and say so explicitly. Few-shot: three labelled training memes plus two ordinary posts with no technique.
- [x] 1.4 Validation: drop any item whose `name` is not in the list or whose `quote` is not a substring of the post. This is the false-positive guard and the prompt-injection guard. The substring check ignores case, curly quotes and spacing.
- [x] 1.5 `app/cache.py`: SQLite table `(key, json, created)`. Key is a hash of the text plus the prompt version.
- [x] 1.6 Rate limit `POST /api/analyze` per IP (10 per minute, in memory). The endpoint is public and spends credits. IP is the last `X-Forwarded-For` entry, which Traefik sets.
- [x] 1.7 Wire into `/api/analyze` so `techniques` is filled for both `text` and `url` input.
- [x] 1.8 `web/panel.js`: `renderPanel(node, analysis)`. Techniques section: name, the quote highlighted, the reason. Empty list shows "No manipulation techniques found".
- [x] 1.9 Tests with the LLM stubbed: invalid name dropped, invented quote dropped, empty list passes through, cache hit skips the LLM.
- [ ] Done when: a loaded post on the live site shows techniques with quotes, and a weather report shows none.

### Feature 2: read a Bluesky post from its URL (about 1 h)

- [x] 2.1 `app/bluesky.py`: `parse_url(url) -> (handle, post_id)`. Reject anything that is not a `bsky.app` post URL.
- [x] 2.2 `get_post(url) -> {text, author, ts, url}` through the public API.
- [x] 2.3 `get_author(handle) -> {handle, bio, created_at, followers, following, default_avatar, total_posts, verified}`.
- [x] 2.4 `get_author_timestamps(handle) -> [epoch seconds]` for the last 100 posts.
- [x] 2.5 Cache each call for 10 minutes. 10 s timeout. A failure becomes an entry in `errors`.
- [x] 2.6 Wire in: `url` input fills `post`, and techniques run on the fetched text.
- [x] 2.7 Web page: accept a URL as well as text. Panel shows author and time above the techniques.
- [x] 2.8 Tests on saved API responses in `tests/fixtures/`: URL parsing, field mapping, deleted post.
- [ ] Done when: pasting a real Bluesky post URL on the live site shows its text and techniques.

### Feature 3: bot-likeness score (about 1 h)

- [x] 3.1 Call `bot_score.score(account, timestamps)` with the data from feature 2. No similar posts yet.
- [x] 3.2 Fill `bot` with `score`, `verdict`, `checked`, `reasons`.
- [x] 3.3 Panel: a labelled bar, the verdict, the list of reasons, and a line listing what could be checked. Text input shows "Paste a post link to check the author".
- [x] 3.4 Wording on the panel: "bot-likeness score", with a tooltip that it is not a probability.
- [x] 3.5 Test: fixture author and timestamps map into the response; author fetch failure gives `bot: null` plus an error.
- [ ] Done when: a known feed bot scores high and a teammate's own account scores low on the live site.

### Feature 4: similar posts and coordination (about 1.5 h)

- [x] 4.1 `bluesky.search(query) -> [{author, text, url, ts}]` on `api.bsky.app`, limited to 3 days either side of the post. Works without login locally; recheck from the VPS, otherwise add app-password login from `.env`.
- [x] 4.2 `app/similar.py`: up to 3 queries of 3 rare words each, 50 results per query, merged. Bluesky search requires every word, so one 5 to 8 word query missed copies that changed a single word. Drop the post itself and the post's own author.
- [x] 4.3 Rank by `bot_score.similarity`, keep overlap of 0.3 or more, one item per account, top 10.
- [x] 4.4 Fill `similar`. Pass `similar.as_others(items)` (not the raw list: the contract says `author`, `bot_score` reads `account`) as `others` into `bot_score.score` so the text-reuse category goes live.
- [x] 4.5 Panel: list with author, overlap percent, time, link. Header line built in `panel.js` with the same rule as `similar.summary()` (the contract has no field for it), such as "7 accounts posted near-identical text, 5 within 10 minutes". Label it coordination, not automation: people share copypasta too.
- [x] 4.6 Tests: query builder on a fixture, ranking order, self-match removed (`tests/test_similar.py`). Known weaknesses for the metrics page are in the `app/similar.py` header.
- [ ] Done when: a known copypasta post shows its copies on the live site and an original post shows none.

### Feature 5: measured precision and false positives (about 2 h)

- [ ] 5.1 Techniques data: the SemEval-2021 Task 6 test set (200 labelled meme texts; dev set of 63 for prompt tuning, training set only for few-shot examples) plus about 30 neutral Bluesky posts collected by hand, since memes are not posts. Report per-technique numbers only where there are at least 10 examples. Stored in `eval/`.
- [ ] 5.2 `eval/run_techniques.py`: per-technique precision and recall, and the share of neutral posts that got any technique at all (the false-positive rate).
- [ ] 5.3 Bot data: 30 accounts that are openly bots and 30 accounts known to be people, handles and labels in `eval/bots.csv`.
- [ ] 5.4 `eval/run_bots.py`: precision, recall and false-positive rate at the 0.3 and 0.6 thresholds. State on the page that openly declared bots are the easy case, the sample is 60, and the profile weights are hand-set.
- [ ] 5.5 Both scripts write `eval/results.json` with the sample sizes and the date.
- [ ] 5.6 `web/metrics.html` reads that file and shows the tables plus a "known weaknesses" list. Linked from the main page.
- [ ] 5.7 If the numbers are poor, adjust the prompt or the thresholds, rerun, and keep the earlier numbers on the page as "before".
- [ ] Done when: the metrics page is live and its numbers match a fresh run of both scripts.

### Feature 6: the panel next to the post (about 2 h)

- [ ] 6.1 `extension/manifest.json`: MV3, content script on `https://bsky.app/*`, host permission for the API domain only.
- [ ] 6.2 `content.js`: add an "Analyse" button to each post, including ones loaded while scrolling (one `MutationObserver`).
- [ ] 6.3 On click, work out the post URL, call `/api/analyze`, show a loading state.
- [ ] 6.4 Open a panel beside the post in a shadow root so site styles do not leak, and render with the same `panel.js`.
- [ ] 6.5 Enable CORS on the API for the extension. Close on Escape and on a close button; the button and panel are reachable by keyboard.
- [ ] 6.6 Error and rate-limit states shown in the panel, not the console.
- [ ] 6.7 `extension/README.md`: three lines on loading it unpacked.
- [ ] Done when: clicking Analyse on a post at bsky.app shows the same result as the live web page.

### Feature 9: the whole thread

A post link also loads the post's replies, so a reader can see who is in the thread.

- [x] 9.1 `bluesky.get_replies(url)`: direct replies from one `getPostThread` call, most liked first. Cached with the other reads.
- [x] 9.2 `GET /api/replies`: ten replies per page. Every reply gets a bot-likeness score from its author's profile and post times. A reply scoring above 0.4 is also checked for techniques. No copy search for replies.
- [x] 9.3 Own rate limit (30 per minute per IP), separate from `/api/analyze`. At most ten AI calls per page, and the cache covers repeats.
- [x] 9.4 Panel: replies under the techniques, each with its score badge and, when scanned, its techniques with quotes highlighted. Ten more load as the reader scrolls.
- [x] 9.5 Clicking a reply makes it the main post with its own replies. Back and forward move between opened posts.
- [x] 9.6 Tests: field mapping and order, paging, the 0.4 threshold, author failure, thread failure, rate limit.
- [ ] Done when: a long thread on the live site loads ten replies, loads more on scroll, and a clicked reply opens with its own replies.

### Feature 7: what live sources say (Oxylabs Web API)

Changed from the first plan (GDELT plus outlet leanings): the Oxylabs challenge needs live search and full-page reads, and a count of outlets per leaning says nothing about what the pages report.

- [x] 7.1 LLM picks the post's one checkable factual claim, with an exact quote from the post and a neutral search query. No claim is "not enough data".
- [x] 7.2 `POST /v1/search` on the Oxylabs Web API for the query; keep up to four https results, one per site.
- [x] 7.3 `POST /v1/scrape` reads each page as Markdown, in parallel. A page that cannot be read is listed as found but unread.
- [x] 7.4 LLM reports at most one point per read page: supports, challenges or adds context. A point is dropped unless it names a read page and its quote is found in that page. No true/false verdict.
- [x] 7.5 Fill `coverage`; runs beside the other checks so it does not add to the wait. Cached for one hour. Key in `OXYLABS_WEB_API_KEY`, server side only.
- [x] 7.6 Panel card "What live sources say": the claim, each point with its quote and link, every source with read or unread, and the time it was checked.
- [x] 7.7 Tests with Oxylabs and the LLM stubbed (`tests/test_coverage.py`). `OXYLABS.md` is the note for the challenge submission.
- [x] 7.9 Same claim, three countries: the search runs with `location` US, FI and DE in parallel and fills `coverage.by_country`. The panel lists each country's results and marks sites only one country sees. A failed country search shows as "not enough data" (`sources: null`), not as no results. Pages are read from the first country with results.
- [ ] 7.8 One real call with the team key to confirm the response fields (`results[].url`, `results[0].markdown`), then set the key on the VPS.
- [ ] Done when: a post about a current news story on the live site shows quoted points with working source links.

### Feature 8, later: sides of the argument

- [ ] 8.1 LLM lists the strongest two to three positions on the post's topic, each grounded in a coverage source from feature 7. Positions without a link are dropped.
- [ ] 8.2 Fill `sides`; panel tab shows them side by side, same length, neutral wording.
- [ ] Done when: the tab shows linked positions and never one that has no source.

## Demo script for judges

1. Open the public URL, paste a manipulative post link: techniques with quotes, bot-likeness with reasons, copies found.
2. Paste an ordinary post: nothing flagged, or "not enough data".
3. Open the metrics page: precision, false-positive rate, sample sizes, weaknesses.
4. Switch to bsky.app with the extension: the same panel next to a live post.
