# Progress report

As of 2026-11-14. Tests: 103 pass. The skeleton is live at https://davincicommit.tech; the other features are merged but not yet checked there.

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
| Detector order | Techniques come from the 20-technique prompt through the Hostinger AI Router. The six-technique Anthropic detector (`app/anthropic_detect.py`) is the backup when the router is unset or fails. Neither has been run on the live URL. |
| 5.1-5.7 | Measurement: `eval/` scripts, labelled data and an accuracy page (`/metrics.html`). Bot-likeness on a hold-out of 30 declared bots and 30 verified people: 20 of 30 bots flagged, 8 of 30 from behaviour alone (0 of 30 before the posting-schedule rule), 0 of 30 people flagged. Copy detection: survives hashtags, links, caps; one changed word drops 28% of copies below the 0.7 line. Technique numbers: full run on the live site in progress. |
| 7.1-7.7, 7.9 | Live sources (Oxylabs Web API): the post's main claim is searched from the US, Finland and Germany, up to four pages are read in full, and each point shown quotes a page that was read. Tested with Oxylabs and the AI faked; no real Oxylabs call has been checked yet (7.8). |
| Media | A post's images and quoted post are sent to the AI with the text; techniques found there are marked as from the image or the quoted post. |
| 10.1-10.4 | YouTube: a video link is read through its captions, a minute at a time, and each flagged stretch is listed with its time. Checked against real YouTube from a laptop (transcript in 1.5 s) and in the page with faked AI answers. Not checked from the VPS. |
| 6.1-6.7 | Extension (`extension/`): a Chrome side panel that takes the tab's link and calls the API. Bluesky posts, YouTube videos, and right-click on selected text anywhere. Checked as a page with the browser APIs stubbed; not yet loaded in a real Chrome. |

Checked against the live Bluesky API: post text, author profile, 38 post times, "Post not found" for a deleted post.

## Not done

- **1.1 needs a real AI Router call.** Checked 2026-11-14: a pasted post on the live site returns `"technique detection is not configured on this server"`. Set `AI_ROUTER_BASE_URL`, `AI_ROUTER_API_KEY` and `AI_ROUTER_MODEL` in the VPS project's environment, restart, and check that one post returns techniques. This blocks the "Done when" of Features 1, 2 and 9.
- **The "Done when" line of Features 0, 1, 2, 3, 4 and 9 is unticked.** The live site has the code (panel, `/api/replies`, `similar` all answer), but nobody has run the checks there: a loaded post and a weather report (1), a real post URL (2), a feed bot and a teammate's account (3), a copypasta post and an original (4), a long thread (9), and health from a phone on mobile data (0).
- **Feature 6** (Chrome extension): not started, no `extension/` folder.
- **Feature 7 is not checked live.** Step 7.8: run one real post on the live site with `OXYLABS_WEB_API_KEY` set and confirm the card shows quoted points. `codex/oxylabs-live-context` is superseded by it and can be deleted.
- **Feature 8** (sides): not started.
- **`aarush/detector-standin` is unmerged**: an older, separate app (TF-IDF classifier, its own `/analyze`, port 80). Nothing in `main` uses it.

## Deploy notes

- **What runs on the VPS is not `compose.yml`.** A compose file that builds from the git URL started no containers on Hostinger's Docker Manager, so the project `decode-the-noise` runs a variant: `python:3.12-slim` downloads the GitHub tarball of `main` and starts uvicorn, with the same Traefik labels. It re-downloads `main` on every container restart, so the live app can be newer than the last deploy.
- `/api/health` shows `GIT_SHA` as set by hand in the project's environment (`186ba5f`); it does not follow `main`.
- Traefik (already on the VPS template) owns ports 80 and 443, so Caddy was dropped. An unrelated `noise` project on the VPS also binds port 80; leave it stopped.
- DNS: `davincicommit.tech` A record now points at the VPS (`179.67.199.150`); it pointed at `2.57.91.91` before.
- The AI Router key was printed once in a tool result during this work. Rotate it if this transcript is shared.

## Notes

- `bot_score.py` self-check passes (`python app/bot_score.py`). Its weights and thresholds are hand-set and unvalidated; Feature 5 measures them.
- Author timestamps cover the last 100 feed entries minus reposts, so fewer than 100.
- Search uses `api.bsky.app` (the public mirror refuses `searchPosts`); post and author reads use `public.api.bsky.app`.
