# Hybrid detector plan: LLM primary, labelled data as examples + yardstick

Decisions (from the team): Anthropic API directly; prior data = few-shot examples + eval set; demo text = English news sentences.

## Why the current baseline fails
TF-IDF+LR trained on SemEval memes predicts LOADED LANGUAGE for everything: that class dominates the labels, the data is memes not news, and the default threshold 0.5 flags it freely. The fix is not a better classifier; it is a model that reads meaning. The classifier stays only as a fallback and a measured comparison row.

## Design
`/analyze(text)` -> split sentences -> **one** LLM call per text (all sentences, numbered) -> validated result -> UI.

1. **Prompt (fixed, versioned in git):** definitions of 6 techniques, each with one short definition and 2 labelled example sentences, plus 6 plain-reporting negatives, so "none" is an explicit, common answer. Techniques are chosen from what the data actually contains (>= 30 positives), e.g. loaded language, name calling/labelling, appeal to fear, exaggeration/minimisation, flag-waving, doubt/casting suspicion.
2. **Output:** forced structured output (tool/JSON schema), temperature 0. Per sentence: `techniques[]` (enum), `quote` (exact phrase), `reason` (<= 20 words), `strength` (low/med/high). No true/false field exists in the schema.
3. **Validation (code, not LLM):** reject unknown techniques; `quote` must be a substring of the sentence, else drop the flag; cap flags per text; malformed JSON -> one retry -> "Analysis failed. Nothing was judged."
4. **Injection safety:** pasted text goes inside delimiters, labelled as data; the schema leaves no room to follow instructions in it.
5. **Abstain (code):** < 15 words, non-English (lingua), or mostly quotes -> "Cannot determine", no API call spent.
6. **Fallback:** API error/timeout/limit -> run the classifier with per-technique thresholds and a visible badge "backup model (weaker)". Techniques with no usable threshold are disabled, never defaulted to "loaded language".
7. **Cost/abuse:** batch per text, cache by text hash, 5000-char cap, per-IP rate limit, global daily call cap, log token counts only (never text or keys). Use the smaller model (Haiku-class) by default; the larger one only if the eval shows it is worth it.
8. **Secrets:** `ANTHROPIC_API_KEY` in local `.env` (git- and docker-ignored), read by `os.environ`, never printed or logged.

## Prior data, used three ways
- **Few-shot pool:** from the train split only, picked by hand-reading ~10 per technique.
- **Eval set (the yardstick):** held-out dev split + benign set (100 items, plan T9, news-style) + a small hand-labelled English news set (~60 sentences, labelled by us, never used in the prompt). Disclose that hand labels are ours.
- **Classifier training:** unchanged, now purely baseline/fallback.

## What we measure and show on the Metrics page
Same held-out sentences scored by (a) classifier, (b) LLM, (c) agreement-only. Per technique precision/recall, benign false-positive rate, Wilson 95% intervals, n printed, "too few examples" rule, and a self-test that swaps country names (side-swap). Report the LLM's run-to-run flips (run twice). Ship whichever is better as default; the page says which one and why.

## Build order (hours are my estimates)
| # | Task | h |
|---|---|---|
| H1 | `.env` + one-call smoke test with the real key (prints status and token counts only) | 0.25 |
| H2 | Technique list from data counts; pick few-shot examples; write prompt v1 | 0.75 |
| H3 | `detect_llm()` with schema, validation, retry, cache; unit tests with a fake client | 1.0 |
| H4 | Eval harness: run LLM + classifier on held-out and benign sets, Wilson CIs, `metrics.json` | 1.0 |
| H5 | Fix classifier fallback: per-technique thresholds, disable unreliable ones | 0.5 |
| H6 | Prompt iteration on **validation only** (max 3 rounds), then one scored run on test | 0.75 |
| H7 | `/analyze` + paste page + states from the plan + abstain + rate limit | 1.5 |
| H8 | Metrics page, side-swap, known-failures list | 1.0 |
| H9 | Deploy (after VPS port fix), env file on VPS, health check | 0.75 |

## Rules for honesty
Flags say "wording matches this technique", never a verdict on truth or intent. Prompt tuning touches validation data only; the test number is scored once. If the LLM does not beat the classifier, the page says so.

## Needs from you (one line each)
1. **Approve spend:** an Anthropic API key and a spending cap. This costs money, so I won't call the API until you approve it.
2. **Put the key in `C:\Users\aarus\Pictures\decode-noise\.env`** as `ANTHROPIC_API_KEY=...` yourself; don't paste it in chat.
3. **Data sharing:** sending SemEval/PTC sentences to the API for evaluation may fall under their licence terms (PTC is academic-only, no redistribution). Until a mentor clears it, I'll evaluate the LLM only on our own news set and the benign set.
