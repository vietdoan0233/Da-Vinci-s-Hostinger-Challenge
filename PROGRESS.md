# Progress report

As of 2026-11-14. Nothing is shipped: no feature is live on a public URL yet.

## Done (local, tests pass: 9)

| Step | What | Branch |
|---|---|---|
| 0.1-0.5 | FastAPI skeleton: `/api/health`, `/api/analyze` with input validation, paste page, tests | `feature-0-skeleton` |
| 0.6 | `Dockerfile`, `compose.yml`, `Caddyfile`, `.env.example` | `feature-0-skeleton` |
| 2.1-2.6 | `app/bluesky.py` (parse URL, get post, get author, author timestamps), 10 min cache, 10 s timeout, errors in `errors`; `url` input fills `post` | `feature-2-bluesky` (includes feature 0) |

Checked against the live Bluesky API: post text, author profile, 38 timestamps, and "Post not found" for a deleted post.

## Not done

- **0.7 deploy.** Needs the domain and VPS access; I have neither. Until it is done, Feature 0 is not shipped.
- **Docker files untested.** Docker is not installed on this machine, so they were never built or run.
- **2.7, 2.8 partly.** 2.8 tests are written; 2.7 (author and time in the panel) waits for `panel.js` in step 1.8.
- **Feature 2 "done when"** (a real URL on the live site shows text and techniques) needs 0.7 and Feature 1.
- **Features 1, 3-8** not started. Feature 3 (bot-likeness) is next: its inputs (`get_author`, `get_author_timestamps`) now exist but are not yet passed to `bot_score.score()`.

## Notes

- `bot_score.py` self-check still passes (`python app/bot_score.py`). Its weights and thresholds are hand-set and unvalidated; Feature 5 is what measures them.
- Step 2.6 says techniques run on the fetched text; techniques do not exist yet, so only `post` is filled.
- Author timestamps cover the last 100 feed entries minus reposts, so under 100 posts.
