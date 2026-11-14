# Progress report

As of 2026-11-14. Tests: 39 pass. The skeleton is live at https://davincicommit.tech; the other features are merged but not yet checked there.

## Done

| Step | What |
|---|---|
| 0.1-0.7 | FastAPI skeleton, paste page, tests, deploy files, live on the VPS behind Traefik. `/api/health`, the page and `/api/analyze` answer over HTTPS. |
| 2.1-2.6, 2.8 | `app/bluesky.py` reads a post, an author and the author's post times from a bsky.app URL. 10 min cache, 10 s timeout, failures go into `errors`. A `url` input fills `post`. Tests run on saved responses in `tests/fixtures/`. |
| 4.1-4.3, 4.6 | Similar posts (teammate): Bluesky search, word-shingle ranking, `similar` filled for pasted text and, now that the two are merged, for post URLs too (the post's own author and URL are excluded). |

Checked against the live Bluesky API: post text, author profile, 38 post times, "Post not found" for a deleted post.

## Not done

- **Phone check for 0.7.** The plan says "returns ok from a phone on mobile data"; I only checked from this machine. The box stays unticked until someone tries it.
- **2.7** Author and time in the panel waits for `panel.js` (step 1.8).
- **4.4** `similar` is filled, but the copies are not yet passed into `bot_score.score` (`similar.as_others`). That comes with Feature 3.
- **4.5** The similar-posts panel waits for `panel.js`.
- **Feature 1** (techniques): 1.2-1.7 and 1.9 merged; the code paths are tested with the AI faked. **1.1 still needs a real call**: set `AI_ROUTER_BASE_URL`, `AI_ROUTER_API_KEY` and `AI_ROUTER_MODEL` on the VPS and check that one post returns techniques. 1.8 waits for `panel.js`. Technique list is now SemEval-2021 Task 6 (20 techniques), not the 2020 list.
- **Feature 3** (bot-likeness wiring), Features 5-8: not started. Feature 3 is unblocked: `get_author`, `get_author_timestamps` and `similar.as_others` all exist.

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
