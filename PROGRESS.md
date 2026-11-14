# Progress report

As of 2026-11-14. Tests: 72 pass. The skeleton is live at https://davincicommit.tech; the other features are merged but not yet checked there.

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

Checked against the live Bluesky API: post text, author profile, 38 post times, "Post not found" for a deleted post.

## Not done

- **Nothing after Feature 0 is checked on the live URL.** Features 1-4 and the panel are merged or in review but the VPS still serves old code; see the deploy notes.
- **Phone check for 0.7.** The plan says "returns ok from a phone on mobile data"; only checked from a laptop.
- **1.1 needs a real AI Router call**: set `AI_ROUTER_BASE_URL`, `AI_ROUTER_API_KEY` and `AI_ROUTER_MODEL` on the VPS and check that one post returns techniques. Until then the panel says technique detection is not configured.
- **Features 5-8**: not started. Feature 5 uses the SemEval-2021 Task 6 test set (20 techniques), not the 2020 list.
- **`codex/oxylabs-live-context` is unmerged** and branched before Features 1 and 4. It rewrites `web/index.html` and `app/main.py`, fills `coverage` in a different shape from the plan's Feature 7, and adds an Oxylabs key. It needs rebasing onto the panel (`web/panel.js`) before it can merge.

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
