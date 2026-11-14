# Oxylabs Web API in Unmasked

Each analysed post gets a "What live sources say" card. The code is in `app/coverage.py`.

| Endpoint | When | Why |
|---|---|---|
| `POST /v1/search` with `location` | Three times per post (US, FI, DE), with a neutral query for the post's main factual claim | Find pages about the claim on the web as it is now, and show how the results differ by country. Up to four results per country are kept, one per site. |
| `POST /v1/scrape` (`output: ["markdown"]`) | Once per kept result from the first country with results, in parallel | Read the whole page. The model sees page text only, never search snippets, so each point comes from what the page says. |
| `POST /v1/scrape/media/youtube/subtitles` | Once per YouTube video, only when YouTube refuses the server's own caption request (it refuses the VPS) | Read the video's captions so the transcript can be checked. The code is in `app/youtube.py`. |

What the user sees:

- The claim that was checked, quoted from the post.
- Up to one point per page: supports, challenges or adds context. Each has a sentence quoted from the page and a link to it. A point whose quote is not in the scraped page is dropped.
- "Same search, three countries": each country's results, with sites that only one country sees marked.
- Every source URL, marked "read in full" or "found, could not be read", and the time of the check.
- No true/false verdict. With no checkable claim, no results or no readable page the card says "not enough data".

The key is read from `OXYLABS_WEB_API_KEY` on the server and never reaches the browser. Results are cached for one hour.
