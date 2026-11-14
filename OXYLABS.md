# Oxylabs Web API in Decode the Noise

Each analysed post gets a "What live sources say" card. The code is in `app/coverage.py`.

| Endpoint | When | Why |
|---|---|---|
| `POST /v1/search` | Once per post, with a neutral query for the post's main factual claim | Find pages about the claim on the web as it is now. Up to four results are kept, one per site. |
| `POST /v1/scrape` (`output: ["markdown"]`) | Once per kept result, in parallel | Read the whole page. The model sees page text only, never search snippets, so each point comes from what the page says. |

What the user sees:

- The claim that was checked, quoted from the post.
- Up to one point per page: supports, challenges or adds context. Each has a sentence quoted from the page and a link to it. A point whose quote is not in the scraped page is dropped.
- Every source URL, marked "read in full" or "found, could not be read", and the time of the check.
- No true/false verdict. With no checkable claim, no results or no readable page the card says "not enough data".

The key is read from `OXYLABS_WEB_API_KEY` on the server and never reaches the browser. Results are cached for one hour.
