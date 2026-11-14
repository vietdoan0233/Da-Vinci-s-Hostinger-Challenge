# Progress report

As of 2026-11-14. Tests: 130 pass. `main` is live at https://davincicommit.tech. Checked there: pasted text, a Bluesky post with its replies, a web link with live sources, and a YouTube video's captions.

## Done

| Step | What |
|---|---|
| 0.1-0.7 | FastAPI skeleton, paste page, tests, deploy files, live on the VPS behind Traefik. `/api/health`, the page and `/api/analyze` answer over HTTPS. |
| 2.1-2.6, 2.8 | `app/bluesky.py` reads a post, an author and the author's post times from a bsky.app URL. 10 min cache, 10 s timeout, failures go into `errors`. A `url` input fills `post`. Tests run on saved responses in `tests/fixtures/`. |
| 4.1-4.3, 4.6 | Similar posts (teammate): Bluesky search, word-shingle ranking, `similar` filled for pasted text and, now that the two are merged, for post URLs too (the post's own author and URL are excluded). |
| 1.2-1.9 | Techniques: 20 SemEval-2021 Task 6 techniques, one AI Router call per post, quotes validated against the post, cache, rate limit. Tested with the AI faked. |
| 3.1-3.5, 4.4 | Bot-likeness: a post link fills `bot` from the author's profile, post times and the copies found. |
| 1.8, 2.7, 3.3, 3.4, 4.5 | Panel: `web/panel.js` + `web/panel.css` render the post with quotes highlighted, techniques, bot-likeness and copies. `?q=<post link>` opens a result directly. Checked locally with faked data, desktop and narrow widths. |
| 9.1-9.6 | Thread: a post link also loads its replies ten at a time as the reader scrolls. Each reply shows its own bot-likeness score; replies above 0.4 are also checked for techniques. Clicking a reply opens it as the main post. Checked against the live Bluesky API on a 182-reply post (2-3 s per page) and in the page with faked data. |
| Detector order | Techniques come from the 20-technique prompt through the Hostinger AI Router. The six-technique Anthropic detector (`app/anthropic_detect.py`) is the backup when the router is unset or fails. The router runs on the live site (the full technique run went through it); the backup has not been run there. |
| 5.1-5.7 | Measurement: `eval/` scripts, labelled data and an accuracy page (`/metrics.html`). Bot-likeness on a hold-out of 30 declared bots and 30 verified people: 20 of 30 bots flagged, 8 of 30 from behaviour alone (0 of 30 before the posting-schedule rule), 0 of 30 people flagged. Copy detection: survives hashtags, links, caps; one changed word drops 28% of copies below the 0.7 line. Techniques on 200 labelled memes: precision 57%, recall 46%, micro-F1 0.506; false alarms on 17 of 41 no-technique memes and 1 of 32 factual posts. |
| 7.1-7.7, 7.9 | Live sources (Oxylabs Web API): the post's main claim is searched from the US, Finland and Germany, up to four pages are read in full, and each point shown quotes a page that was read. Tested with Oxylabs and the AI faked, and checked on the live site: three quoted points from four pages read (7.8). |
| Media | A post's images and quoted post are sent to the AI with the text; techniques found there are marked as from the image or the quoted post. |
| 10.1-10.4 | YouTube: a video link is read through its captions, a minute at a time, and each flagged stretch is listed with its time. Checked against real YouTube from a laptop (transcript in 1.5 s) and in the page with faked AI answers. YouTube refuses the VPS, so there the captions come through the Oxylabs Web API (10.5); checked live. |
| 6.1-6.7 | Extension (`extension/`): a Chrome side panel that takes the tab's link and calls the API. Bluesky posts, YouTube videos, and right-click on selected text anywhere. Checked as a page with the browser APIs stubbed; not yet loaded in a real Chrome. |
| 11.1-11.6 | Any web link: a link that is not a Bluesky post or a YouTube video is read through the Oxylabs Web API (`/v1/scrape`, retried once with `run_js` when empty) and checked like a pasted text, with its own site kept out of the live sources. Tested with Oxylabs faked and looked at in the page with faked data. **Run against the real Oxylabs API on one page only** (a Wikipedia article on the live site; 11.7 lists what is left): the rule that picks the article text out of the page is untested on real sites. |

Checked against the live Bluesky API: post text, author profile, 38 post times, "Post not found" for a deleted post.

## Not done

- **Most "Done when" lines are still unticked.** The live site answers for every feature, but the exact checks have not been run: a loaded post and a weather report (1), a feed bot and a teammate's account (3), a copypasta post and an original (4), a long thread with a clicked reply (9), a clicked time in a video (10), a blog post and a JavaScript-heavy page (11.7), health from a phone on mobile data (0), and the extension loaded in a real Chrome (6).
- **Technique accuracy is low** (precision 57%, recall 46%). A prompt change tuned on the SemEval dev set is planned; the dev-set baseline for the current prompt is micro-F1 0.557.
- **Known gaps found in a read-through (2026-11-14), not fixed:** a reply whose author could not be timed shows a low score badge with "not enough data" only in the hover text; accounts that only reply are never timed (post times are read without replies); a Bluesky link with anything after the post ID is rejected; the rate limit is per IP address, so one shared network shares it; the extension's "Analyse this tab" button takes Bluesky posts and YouTube videos only.
- **Reddit and YouTube bot-likeness** is a draft formula in `ARCHITECTURE.md`, not built.
- **Feature 8** (sides): not started.
- **`aarush/detector-standin` is unmerged**: an older, separate app (TF-IDF classifier, its own `/analyze`, port 80). Nothing in `main` uses it. `codex/oxylabs-live-context` is superseded and can be deleted.

## Deploy notes

- **What runs on the VPS is not `compose.yml`.** A compose file that builds from the git URL started no containers on Hostinger's Docker Manager, so the project `decode-the-noise` runs a variant: `python:3.12-slim` downloads the GitHub tarball of `main` and starts uvicorn, with the same Traefik labels. It re-downloads `main` on every container restart, so the live app can be newer than the last deploy.
- `/api/health` shows `GIT_SHA` as set by hand in the project's environment; it does not follow `main`.
- A variable only reaches the app if the project's compose file lists it under `environment:`. `OXYLABS_WEB_API_KEY` turns on live sources, web links and YouTube captions together.
- Traefik (already on the VPS template) owns ports 80 and 443, so Caddy was dropped. An unrelated `noise` project on the VPS also binds port 80; leave it stopped.
- DNS: `davincicommit.tech` A record now points at the VPS (`179.67.199.150`); it pointed at `2.57.91.91` before.
- The AI Router key was printed once in a tool result during this work. Rotate it if this transcript is shared.

## Notes

- `bot_score.py` self-check passes (`python app/bot_score.py`). Its weights and thresholds are hand-set and unvalidated; Feature 5 measures them.
- Author timestamps cover the last 100 feed entries minus reposts, so fewer than 100.
- Search uses `api.bsky.app` (the public mirror refuses `searchPosts`); post and author reads use `public.api.bsky.app`.
