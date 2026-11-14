# Ship a sourced, measured claim checker by 07:00

**Build the measured technique detector first (PTC news sentences, TF-IDF + logistic regression, benign-text false-positive set, abstain state, Wilson-interval metrics page, side-swap test), put a placeholder on the Hostinger VPS by IP before 16:00, have the minimum version live by 20:30, and then add the evidence layer in four cut-able stages: sourcing signals, Exa corroboration, wire-copy merging with an "other side" view, and a re-sharing flag.** The whole plan is **24.25 person-hours (A 12.375, B 11.875), inside the 25-hour cap**, including the 07:00-10:00 deployment checks and rehearsal; budget is EUR 0 and nothing is purchased. The evidence layer is what the three mentors said they care about most (how well a claim is backed, and whether many accounts re-share one story without sources), so it is cut last, not first: the cut order removes the re-sharing panel and the LLM explanation before any sourcing or corroboration work. The layer never returns "true" or "false"; it shows "backing found / not found / unavailable", links, and which country or ownership type each outlet belongs to. Two risks dominate: PTC data is academic-only and its spans are unvalidated until 14:45 (SemEval-2021 memes are the fallback), and Exa may return only topical, not same-claim, pages, so the plan measures that on a 26-item hand-checked set and states the limits. Every number below that looks like a result is either arithmetic on sample sizes or a target; no accuracy figure has been measured. The plan assumes the same two people as before (A speaks Finnish and owns data, evaluation and NLP modules; B owns deployment and the app), because the team line was left blank. Domain and HTTPS are skipped; the public URL is `http://<VPS-IP>`.

Tag legend: VERIFIED = a source page was opened by the research notes behind this plan; PARTIAL = search snippet, abstract, or incomplete page; INFERENCE = reasoning or general knowledge, untested. I did not re-open sources myself; tags come from the notes, which also warn that their fetch tool returned page summaries, so quotes are not character-exact.

**What changed from the earlier plan.** (1) PTC news articles replace SemEval-2021 memes as the primary data, with a validation gate at 14:45 (VERIFIED access terms, [PTC page](https://propaganda.math.unipd.it/ptc/)). (2) Domain, Let's Encrypt and Caddy HTTPS move to an optional stretch; the live URL is IP-only HTTP. (3) The evidence layer is added (sourcing signals, Exa corroboration, near-duplicate merging, re-sharing flag, "other side" view). (4) The cross-viewpoint smoke check is dropped and replaced by the outlet-side view and the 26-item evidence set. (5) The LLM explanation is no longer scheduled; it is a swap-in only if hours are freed. (6) Spend is zero: the EUR 50 line is removed. The judging weights are 40/25/20/15 per the brief; my notes only tie the 40% bucket to detection quality and explainability, and do not name the other three, so the plan does not assume them.

---

## 1. Schedule, checkpoints, cut list

### 1.1 Task list and hours (sum shown)

| ID | Task | Owner | Hours |
|---|---|---|---|
| T1 | VPS: SSH in, check or install Docker, hPanel firewall accepts 22 and 80 | B | 0.50 |
| T2 | Placeholder FastAPI container on the VPS, reachable at `http://<IP>/health` | B | 1.00 |
| T3 | PTC login with passcode, download train and dev, span-offset validation, SemEval-2021 clone as fallback | A | 0.75 |
| T4 | Load labels, technique frequency table, choose six techniques, span-to-sentence labels, article-level split | A | 1.25 |
| T5 | Key smoke tests: AI Router, Exa, Context.dev (one small request each, keys from env vars); Exa niche gate | B | 0.50 |
| T6 | Baseline TF-IDF + LR, validation macro-F1, per-technique thresholds | A | 1.25 |
| T7 | App core: `/analyze`, sentence split, model load, paste view, highlights, abstain display | B | 2.00 |
| T8 | Metrics library: P/R/FPR, Wilson CIs, threshold picker, `metrics.json` | A | 0.75 |
| T9 | Benign set, 100 items plus 10 Finnish abstain items (A 0.50, B 0.75) | A+B | 1.25 |
| T10 | Abstain rules, language ID, unit tests | A | 0.75 |
| T11 | Final evaluation on PTC dev (scored once) and benign set; error analysis (A 0.50); second annotator (B 0.25) | A+B | 0.75 |
| T12 | Metrics page rendered from `metrics.json` | B | 0.75 |
| T13 | Hardening, `deploy.sh`, restart and reboot test, deploy v1 | B | 0.75 |
| T14 | Side-swap self-test (A 1.00) plus UI hook (B 0.25) | A+B | 1.25 |
| E1 | Evidence stage 1: sourcing signals module and plain panel (A 1.00), UI polish (B 0.25) | A+B | 1.25 |
| E2 | Evidence stage 2-3: outlet table (A 0.50); Exa client, cache, fallback, `/evidence` endpoint (B 1.00); wire merge and side-by-side view (B 1.00) | A+B | 2.50 |
| E3 | Evidence stage 4: shingle module and re-sharing flag (A 0.75), UI hook (B 0.25) | A+B | 1.00 |
| E4 | Hand-checked evidence set, 26 items: build and label (A 1.00), run and sanity-check (B 0.50) | A+B | 1.50 |
| E5 | Pre-cached demo results file and offline switch | B | 0.25 |
| D1 | Demo prep: re-copy quotes, run texts, pick failure case (A 0.75); slides (B 0.50) | A+B | 1.25 |
| D2 | Submission text, README, data-licence note | A | 0.50 |
| D3 | Coordination and handovers (0.125 each) | A+B | 0.25 |
| D4 | Final deployment checks 07:00-09:00 (A 0.50, B 0.50) | A+B | 1.00 |
| D5 | Timed rehearsal, Q&A, backup screen recording (A 0.50, B 0.75) | A+B | 1.25 |
| | **Sum A** (T3 0.75, T4 1.25, T6 1.25, T8 0.75, T9 0.50, T10 0.75, T11 0.50, T14 1.00, E1 1.00, E2 0.50, E3 0.75, E4 1.00, D1 0.75, D2 0.50, D3 0.125, D4 0.50, D5 0.50) | | **12.375** |
| | **Sum B** (T1 0.50, T2 1.00, T5 0.50, T7 2.00, T9 0.75, T11 0.25, T12 0.75, T13 0.75, T14 0.25, E1 0.25, E2 2.00, E3 0.25, E4 0.50, E5 0.25, D1 0.50, D3 0.125, D4 0.50, D5 0.75) | | **11.875** |
| | **TOTAL** | | **24.25 (cap 25)** |

Phase subtotals: minimum version T1-T13 = 12.25; side-swap T14 = 1.25; evidence layer E1-E5 = 6.50; demo, submission, coordination, checks, rehearsal D1-D5 = 4.25; 12.25 + 1.25 + 6.50 + 4.25 = 24.25. Hours are my estimates for first-years with little DevOps (INFERENCE). Awake time is about 15.2 h each (30.4 h total), so roughly 6 h is unallocated slack for meals, overruns, and the 02:00-03:00 overnight gap. The optional LLM explanation (about 1.0 h) does not fit inside the cap unless another item is cut first.

### 1.2 Hour-by-hour (UTC+2)

Sleep: **B sleeps 22:00-03:00, A sleeps 03:00-08:00.** B wakes exactly as A sleeps, so someone is awake the whole time and no handover gap exists. Build stops 07:00 (B alone); 07:00-10:00 is deployment checks and rehearsal. A is asleep until 08:00, so A's Finnish demo text and the Finnish abstain cases must be finished before 03:00.

| Time | A (Finnish speaker; data, evaluation, NLP modules) | B (deployment, app) |
|---|---|---|
| **Sat 13:47-14:17** | T3 PTC login, download, offset validation (to 14:35) | T1 VPS access, Docker check or install, firewall |
| 14:17-15:17 | **14:45 gate: PTC go / no-go.** T4 starts 14:45 | T2 placeholder by IP -> **live by ~15:17 (deadline 16:00)** |
| 15:17-16:00 | **CP1 15:30**: per-technique counts printed. T4 finishes 16:00 | T5 key smoke tests; **15:50 Exa niche gate** |
| 16:00-17:15 | T6 baseline and thresholds | T7 app core with stub model (15:47-17:47) |
| **17:15-18:00** | **CP2 17:30** macro-F1 read at default threshold. T8 metrics library (to 18:00) | T7 continues |
| 18:00-19:15 | T9 benign curation (18:00-18:30); T10 abstain and language ID (18:30-19:15) | T9 benign collection (17:47-18:32); T12 metrics page (18:32-19:17) |
| 19:15-20:30 | T11 final eval, run once (19:15-19:45); T14 side-swap starts 19:45 | T13 hardening, `deploy.sh`, reboot test; deploy v1 -> **minimum version live by 20:30** |
| 20:30-21:45 | T14 side-swap (to 20:45); E1 sourcing signals (20:45-21:45) | E2 part 1: Exa client, cache, fallback, `/evidence` plain list (20:30-21:30) |
| 21:45-22:15 | Meal / break | T11 second annotator (21:30-21:45); D3 handover; **22:00 B sleeps** |
| 22:15-23:30 | E2 outlet table (22:15-22:45); E3 shingle module (22:45-23:30); deploy stage 1-2 with `deploy.sh` after local tests -> **sourcing + raw corroboration list live ~23:15** | asleep |
| 23:30-01:15 | E4 build and label the 26-item evidence set (23:30-00:30); D1 demo texts, failure case (00:30-01:15) | asleep |
| 01:15-03:00 | D2 submission text, README, licence note (to 01:45); D3 handover note (to 02:00); **02:00 gate**; buffer; **03:00 A sleeps** | asleep until 03:00 |
| **Sun 03:00-04:00** | asleep | E2 part 2: wire merge, near-duplicate collapse, side-by-side "other side" view |
| 04:00-05:15 | asleep | UI hooks E1/E3/T14 (04:00-04:45); E4 run set through live app, corroboration sanity checks (04:45-05:15) |
| 05:15-06:00 | asleep | E5 cached demo results (05:15-05:30); D1 slides (05:30-06:00). **05:30 gate: stages 3-4 live or cut** |
| 06:00-07:00 | asleep | **06:00 feature freeze**: only fixes, rerun demo texts; **07:00 code freeze, `git tag`** |
| **07:00-08:00** | asleep | D4 checks (07:00-07:30): fresh phone, `/health`, evidence panel, cached mode |
| 08:00-09:00 | A wakes 08:00. D4 checks (08:00-08:30); D5 rehearsal x3 timed (08:30-09:00) | D5 rehearsal and backup recording (08:00-08:45) |
| 09:00-10:00 | **Submit by 09:15**, confirm the submission page | Confirm public URL once more. **10:00 final submission** |
| Sun 14:00 | Review and pitch (extra rehearsal is outside the 25 h) | |

### 1.3 Checkpoints

| Checkpoint | Test | If failed |
|---|---|---|
| **14:45 PTC gate** | Passcode works, train and dev download, at least 95% of a 50-span sample start and end on word boundaries and 20 printed spans read as phrases (threshold is my engineering judgement, INFERENCE) | Switch permanently to SemEval-2021 (unit-level labels if its offsets also fail); decide by 15:00 |
| **By 16:00 (target ~15:17)** | `http://<VPS-IP>/health` answers from a phone off the venue Wi-Fi | Ask the Hostinger mentor; check hPanel firewall; try the Hostinger Docker template (see section 7) |
| **CP1 15:30** | Usable labelled data loaded; counts per technique printed | Bail-out (section 8.2) |
| **15:50 Exa niche gate** | One Exa request returns at least five distinct hostnames for the NATO query in the April 2023 window; per-outlet `includeDomains` queries return TASS, Global Times and Yle at least once | Keep the niche but build the cache with per-outlet queries and say so on the slide; switch to the border-closure alternative only if three of five outlet groups return nothing (that alternative is untested) |
| **CP2 17:30** | Baseline macro-F1 over the six techniques on **validation** at default threshold 0.5 is >= 0.3 | Bail-out (section 8.2); within 0.05 of 0.3, ask a mentor first |
| 20:30 | Minimum version live: detector, metrics page, benign FPR | Cut evidence work to E1 only; spend time on error analysis and demo |
| ~23:15 | Stage 1-2 live: sourcing panel and raw corroboration list | Keep cached-results mode only |
| 02:00 | A confirms E1, E3 module tests pass and E4 labels exist | Shrink E4 to 20 items |
| 05:30 | Wire merge and other-side view live | Cut to raw list with outlet table labels |
| 06:00 / 07:00 | Feature freeze / code freeze, tag release | No merges except fixes found by D4 |

### 1.4 Ordered cut list (cut from the top when behind)

| Order | Cut | Hours saved | Why this position |
|---|---|---|---|
| 1 | Domain and HTTPS stretch (never scheduled) | 0 | Not needed for a public URL; IP-only is acceptable per the user |
| 2 | LLM explanation (not scheduled) | 0 | Needs router credits and model ID; refusal risk; the detector never depends on it |
| 3 | Side-swap live toggle; keep the static result on the metrics page | 0.25 | The measurement stays; only the interactive toggle goes |
| 4 | Re-sharing panel and its labelled-pair tuning (E3) | up to 0.75 | Mentors' re-sharing concern is partly covered by corroboration's wire merge, which reuses the same shingle function; build that function inside E2 and cut only the stand-alone panel |
| 5 | Evidence set 26 -> 20 items | 0.25 | CIs widen; state n |
| 6 | Benign set 100 -> 60; per-technique thresholds -> one global threshold | 0.25-0.5 | Wider CI, stated |
| 7 | Slide and recording polish (a rough recording must still exist) | 0.25 | |
| 8 | Live Exa call: demo runs from cached results only (E2 live path off, cache stays) | 0.5 | Late cut because mentors rank corroboration highest; the cache keeps the feature visible |
| 9 | Sourcing signals (E1) | last | Offline, cheapest, always works, directly answers "does the text cite anything" |

Not planned: LLM baseline comparison, fine-tuned transformer, cross-country framing view, domain-age lookup. **Never cut:** public URL, held-out evaluation, benign FPR with interval, abstain state, known-failures list, health check and restart policy, static metrics fallback, recorded backup.

---

## 2. What the tool is, and what it is not

**One niche, one problem.** Niche: coverage of Finland formally joining NATO on 4 April 2023 across Russian state, Chinese state-linked, Russian exile, Finnish public and Western wire outlets. Problem: for a pasted text, (a) which rhetorical techniques does its wording match, and (b) how well backed is its key claim, shown without declaring who is right. The niche stays unless the 15:50 gate fails: Exa news search over a 2023 window should work (the filters `category: news`, `startPublishedDate` and `endPublishedDate` are listed; VERIFIED, [Exa search reference](https://docs.exa.ai/reference/search)), coverage of this event by TASS, Global Times, Xinhua, Moscow Times, RFE/RL and Yle was opened in the notes (VERIFIED, [demo notes](https://tass.com/politics/1599137/amp)), and A can check Finnish. Whether Exa indexes TASS and Global Times well is unknown (INFERENCE), hence the cache.

**Mapping to the brief's directions.**

| Direction | Role | What we build |
|---|---|---|
| (2) classify manipulation techniques, explain verdict | **Primary** | Six-technique sentence detector; plain-language chip text from fixed templates (LLM explanation optional) |
| (1) coordinated inauthentic behaviour | Lite | Re-sharing / text-reuse check across retrieved outlets; no timing or account data, so no bot or coordination claim |
| (4) provenance scoring | Lite, only if cheap | Cloned-content flag via shingles and an "outlet not in our table" flag; domain age is not offered by Exa or Context.dev in what the notes read, so it is not built |
| (3) bots in server logs | Bail-out only | Zenodo 3477932 plan (section 8.2) |

**What the tool does not claim** (printed on the first screen):
- It does not say whether a statement is true or false; it is not a fact-checker.
- It does not infer intent, honesty or affiliation, and does not say who is right.
- "Backing found" means other outlets carry matching key terms. It does **not** prove truth, and the tool does not check whether those outlets agree with or dispute the claim. "Not found" means nothing matched in the sources searched; it does not mean false.
- "No technique flagged" is not "neutral"; sourcing signals show that a text cites something, not that the citation is good.
- It does not detect bots or bad actors in the main build.
- The same rules and the same outlet-table fields apply to every country, party and ideology; it has no "bad source" list.

**On-screen states (wording fixed)**

| Situation | What the user sees |
|---|---|
| Sentence flagged | Highlight, chip (for example "Loaded language"), "model score 0.81 (not a probability); measured precision at this threshold on held-out data: see Metrics". Under it: "Wording matches this technique. Not a verdict on truth or intent." |
| Sentence borderline | Dotted underline, "Cannot determine: score 0.52 is below the 0.70 flag threshold. Not flagged." |
| Nothing flagged | "No technique flagged in N sentences. This does not mean the text is neutral or accurate." |
| Text under 15 words | "Cannot determine: text too short to judge." (15 is a starting rule, tune on validation; INFERENCE) |
| Not English | "Technique detector: cannot determine, trained on English only. Detected language: Finnish." The evidence layer still runs for Finnish (spaCy Finnish pipeline, below). |
| Mostly quoted text | "Inside quotation marks: may be reported speech; whose framing this is cannot be determined." (ship only if it does not change test results) |
| Technique disabled | Listed on Metrics as "not reliable, not shown" |
| Model error | "Analysis failed. Nothing was judged." Never a default "clean". |
| Evidence panel | "Cites: N named sources, N quotes, N figures, N links" (each separate, no composite). "Backing found: N independent origins (M copies merged), stance not checked" / "No matching coverage found in the sources searched" / "Evidence unavailable (search service down); showing saved results from <date>" or nothing |

The score is shown as "model score", not "confidence", because balanced logistic regression is uncalibrated and calibration data is small (isotonic calibration tends to overfit below about 1000 samples; VERIFIED, [scikit-learn docs](https://scikit-learn.org/stable/modules/generated/sklearn.calibration.CalibratedClassifierCV.html)).

---

## 3. Architecture

| Component | Runs on | Calls out to | Notes |
|---|---|---|---|
| Training, evaluation, benign and evidence-set scoring, outlet table, cache building | Team laptops (CPU) | Exa, Context.dev (keys from local `.env`) | PTC data lives only here, in a folder outside git |
| FastAPI app: `/analyze` (technique detector, language ID, abstain), `/evidence` (sourcing, shingles, merge, corroboration), `/metrics`, `/health` | **VPS** (2 vCPU / 8 GB per the brief; TF-IDF + LR, regex and small spaCy models fit easily, INFERENCE) | **Exa** `POST https://api.exa.ai/search` for corroboration (server-side so the key stays on the VPS) | Evidence call is separate from the detector so the detector works if Exa fails |
| `model.joblib` | VPS, copied by `scp` into a bind-mounted `models/` folder; not in git, not in the image | none | PTC terms (section 5) |
| `metrics.json`, `outlets.csv`, `demo_cache.json`, `metrics_static.html` | In git (numbers, hand-labelled table, short extractive snippets with URLs) | none | No PTC text anywhere |
| Cache (JSON file or SQLite on a volume) | VPS | none | Key = hash of normalised claim plus date window; stores URLs, hostnames, dates, short snippets and precomputed overlap numbers, not full articles |
| Context.dev scrape | VPS, only for "paste a URL" mode and for Exa results with thin text | `POST https://api.context.dev/v1/web/scrape` | Optional; extracted text is data, never fed to an LLM in the core |
| Hostinger AI Router | VPS, **only** the optional LLM explanation | `https://router.hostinger.com/v1` | Not in the core path |
| Static fallback | VPS, served under `/static/` | none | Survives an app crash if served by the proxy container |

**Libraries.** scikit-learn (`TfidfVectorizer`, `LogisticRegression(class_weight="balanced")`, `OneVsRestClassifier`, `GroupShuffleSplit`; all VERIFIED, [OneVsRest docs](https://scikit-learn.org/stable/modules/generated/sklearn.multiclass.OneVsRestClassifier.html), [GroupShuffleSplit docs](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupShuffleSplit.html)); `statsmodels.stats.proportion.proportion_confint(..., method="wilson")` (VERIFIED, [docs](https://www.statsmodels.org/stable/generated/statsmodels.stats.proportion.proportion_confint.html)); language ID with lingua-py (Apache-2.0, includes Finnish, needs Python >= 3.12, weak under about 120 characters; VERIFIED, [GitHub](https://github.com/pemistahl/lingua-py)), so pin `python:3.12-slim` (tag from general knowledge, INFERENCE); FastAPI served with `fastapi run` (VERIFIED, [FastAPI Docker docs](https://fastapi.tiangolo.com/deployment/docker/)); spaCy `fi_core_news_sm` 3.8.0 (components include tagger, lemmatizer, parser, ner; NER F-score 75.96; 13 MB; CC BY-SA 4.0; VERIFIED, [release page](https://github.com/explosion/spacy-models/releases/tag/fi_core_news_sm-3.8.0)); `en_core_web_sm` for English (components and licence not confirmed, PARTIAL, [spaCy English models](https://spacy.io/models/en); check with `python -m spacy info en_core_web_sm`); `httpx` for Exa and Context.dev calls (my choice; the raw HTTP fields are VERIFIED, while the `exa_py` snake_case argument names `category`, `end_published_date` are PARTIAL, so check `help(exa.search)` or use raw `httpx`).

**External API facts (all VERIFIED unless marked).**

| Service | Facts used | Source |
|---|---|---|
| Exa | `POST https://api.exa.ai/search`, header `x-api-key`; fields `query`, `type` (`auto` default), `category` (includes `news`), `includeDomains`/`excludeDomains`, `startPublishedDate`/`endPublishedDate`, `numResults` 1-100, `contents.text` with `maxCharacters`; result fields `title`, `url`, `publishedDate`, `author`, `text`; no separate source-domain field, so parse the URL hostname; `costDollars` in the response; errors 400, 401, 402, 403, 429, 500, 503; default 10 QPS on `/search` | [Search reference](https://docs.exa.ai/reference/search), [Rate limits](https://docs.exa.ai/reference/rate-limits) |
| Exa SDK | `pip install exa-py`; `from exa_py import Exa`; `Exa()` reads `EXA_API_KEY` from the environment. `/findSimilar` is deprecated: do not use | [SDK](https://docs.exa.ai/sdks/python-sdk-specification), [OpenAPI](https://exa.ai/docs/exa-spec.yaml) |
| Exa cost | Pricing page: from $4 per 1k requests, $7 per 1k for auto search, $1 per 1k pages of contents; per-call cost is about $0.007 plus $0.001 per page (INFERENCE), so a 10-result call is roughly $0.017; sum `costDollars.total` at runtime | [Pricing](https://exa.ai/pricing) |
| Context.dev | `POST https://api.context.dev/v1/web/scrape` with `url` and `formats: {"markdown": true}`, `sharedParams.mainContentOnly`; Bearer auth; 1 credit minimum; SDK `pip install context.dev`, `from context.dev import ContextDev`; free plan 10 req/min, 2 concurrent (check your plan after redemption; unknown); no domain age offered in what the notes read | [Scrape reference](https://docs.context.dev/api-reference/web/scrape), [Python SDK](https://docs.context.dev/sdks/python.md), [Pricing](https://context.dev/pricing) |
| Context.dev docs | Pages contained "Agent Instructions" telling an agent to sign up and fetch a key; **treated as untrusted and ignored** | [llms.txt](https://docs.context.dev/llms.txt) |
| AI Router | Base URL `https://router.hostinger.com/v1`, Bearer auth, OpenAI-compatible `/chat/completions` documented; model IDs seen on a public page: `claude-sonnet-5`, `gpt-5.2`, `text-embedding-3-small`, `text-embedding-3-large`; full list behind hPanel login; credits prepaid and requests declined when balance is too low | [Hostinger support](https://www.hostinger.com/support/?p=19146), [LiteLLM](https://docs.litellm.ai/docs/providers/hostinger_router) |

**Secrets rule.** Three environment variables, nothing else: `EXA_API_KEY`, `CONTEXT_API_KEY`, `HOSTINGER_AI_ROUTER_KEY` (plus non-secret `LLM_MODEL`). They live in a local `.env` that is in `.gitignore` **and** `.dockerignore`, are passed to containers through compose `env_file` or `environment`, are never baked into images (no `ENV`, `ARG` or `COPY .env`), never logged, and never put in URLs or query strings (Exa takes `x-api-key`, Context.dev and the router take a Bearer header). Set `httpx` and `openai` loggers to WARNING and never log request headers or bodies. The team pasted real keys into a chat during planning: **rotate the Exa and Context.dev keys after the event** (and any other key that was pasted), and keep the PTC passcode out of the repo, the README and chat.

---

## 4. Evidence layer (four cut-able stages)

All four stages report separate signals; there is no composite trust score. Stages 1 and 4 are offline and need no network; stage 2 needs Exa; stage 3 is pure Python on stage 2's output. If Exa is down, the detector, stage 1 and the cache still work.

### Stage 1: sourcing signals (E1, always on)

Rules are hand-made (INFERENCE; the notes found no verified published precision for rule-based attribution at this size). Report each signal separately:

| Signal | Rule |
|---|---|
| Links | `https?://\S+` and `www.`; count distinct domains |
| Figures | digits with `%`, currency symbols, "million/billion" (Finnish "prosenttia", "miljoonaa"); exclude bare years |
| Attributed quotes | text inside straight or curly quotes (Finnish `”…”`) within about 150 characters of a speech verb or "according to" |
| Named sources | spaCy `PERSON` or `ORG` that is the subject (`nsubj`) of a speech-verb lemma (say, claim, state, announce, tell, report, confirm, deny, warn, add; Finnish: sanoa, kertoa, todeta, väittää, ilmoittaa, varoittaa), or "according to <ENT>" / Finnish "<ent>n mukaan". Finnish needs lemmas from `fi_core_news_sm`, not surface strings |
| Vague attribution (extra flag) | generic plural subject plus speech verb with no named entity: "experts say", "sources claim" |

"Unsourced" means none of the four fired; the UI lists which fired. A named source is attribution, not credibility, and the page says so. Quote datasets (Quotebank 189.7 GB, CC BY 4.0, English only; PolNeAR, no licence stated) are too large or unlicensed to use here; take test sentences from our own collection ([Quotebank](https://zenodo.org/records/4277311), [PolNeAR](https://github.com/networkdynamics/PolNeAR)).

### Stage 2: corroboration with Exa (E2)

1. **Claim.** Default key claim = highest-scoring sentence by (contains figure + named entity + speech verb), else the first sentence (heuristics, INFERENCE). The claim sits in an editable box labelled "claim used for search" so the user sees and can change what was searched.
2. **Search.** One `POST /search`: `category: news`, `numResults: 10`, `contents.text.maxCharacters` about 3000 (needed for the overlap check), optional date window, `excludeDomains` = the pasted article's own hostname if a URL was given. Sketch (UNTESTED):

```python
import os, httpx
def exa_search(claim, start=None, end=None, exclude=None):
    body = {"query": claim, "type": "auto", "category": "news", "numResults": 10,
            "contents": {"text": {"maxCharacters": 3000}}}
    if start: body["startPublishedDate"] = start
    if end: body["endPublishedDate"] = end
    if exclude: body["excludeDomains"] = exclude
    r = httpx.post("https://api.exa.ai/search", json=body, timeout=6.0,
                   headers={"x-api-key": os.environ["EXA_API_KEY"]})
    r.raise_for_status()
    return r.json()          # results[].url / title / publishedDate / text ; costDollars
```
Whether `category: news` can be combined with date filters is not stated in the notes; the 15:30 smoke test must try it (INFERENCE).
3. **Relevance filter.** Exa is a semantic search, so it returns topical pages even when they do not carry the claim. Keep a result only if at least k of the claim's content tokens and named entities appear in its text (k tuned on the evidence set; no value claimed), and show an extractive snippet around the match so the user can judge. The tool does **not** assess stance: a retained page may dispute the claim. That is stated in the panel and measured in the evidence set.
4. **Outlets and sides.** Hostname -> `outlets.csv` (about 20-40 rows, hand-labelled by A and B from each outlet's own About page): `hostname, name, country, ownership_type (state-controlled / public broadcaster / private / unknown), owner_group, wire_agency (y/n)`. "Side" in the UI means country and ownership type as the outlet states them, not a left-right or trust rating. We do not copy MBFC, AllSides or Ad Fontes ratings: MBFC's data API is for custom or low-volume use and not for redistribution, AllSides requires prior written consent for commercial use (PARTIAL), Ad Fontes licence is unread, and all three rate US-centric bias that does not describe Russian, Chinese or Finnish outlets (INFERENCE) ([MBFC API](https://mediabiasfactcheck.com/mbfcs-data-api), [AllSides terms](https://allsides.com/terms-of-use), [MBFC methodology](https://mediabiasfactcheck.com/methodology/), [Ground News](https://ground.news/about)). Hostnames not in the table appear as "unlisted source" and still count as an origin.
5. **Independent origins.** Collapse in this order: same `owner_group`; wire credit string (AP, Reuters, AFP, Xinhua, TASS, STT, Interfax) or `wire_agency` copy; near-duplicate text (stage 3 function). Report "N independent origins (M copies merged)". Wording never says "confirmed" or "verified".
6. **Other side, side by side.** Group the retained origins by the `country` column, one card per origin: outlet, country, ownership type, date, link, a snippet around the claim terms. Ordering is by date, not by "trust". The page header: "These are other outlets' wording of the same event, not a ruling on who is right." This is the "like Ground News but not one-to-one" view: Ground News merges same-event coverage and uses three external raters for lean and factuality (VERIFIED, [Ground News](https://ground.news/about)); we do the merge and the labelling ourselves, with fewer sources and no ratings.
7. **Limits and quota.** Cache by claim hash; per-IP limit of 10 evidence calls per minute and a global daily cap (for example 300 calls; my choice) so judges cannot drain credits; Exa default 10 QPS is not a constraint (VERIFIED).

### Stage 3: wire syndication and same-owner merging (part of E2)

Uses stage 4's shingle function. Same-wire copies are merged into one origin so that five reprints of one Reuters piece count as one. Near-duplication shows shared text, not who copied whom; earlier date and shared wire credit are suggestions only (INFERENCE).

### Stage 4: re-sharing check (E3)

```python
import re
def shingles(t, k=5):
    w = re.findall(r"\w+", t.lower())
    return {" ".join(w[i:i+k]) for i in range(max(0, len(w)-k+1))}
def jaccard(a, b): return len(a & b) / len(a | b) if (a | b) else 0.0
def containment(a, b): return len(a & b) / min(len(a), len(b)) if a and b else 0.0
```
Normalise first (lowercase, strip bylines and boilerplate). Compare the pasted text against each retained result and results against each other. Flag "near-identical text repeated, no new sourcing" when overlap >= threshold **and** the later copy's stage-1 sourcing items (named sources, quotes, figures, links) add nothing beyond the original's. Use containment, not only Jaccard, when one text is an excerpt of a longer one; use `rapidfuzz.fuzz.ratio` only on lead paragraphs, never `token_set_ratio` alone, which scores 100 when one word set is a subset of the other (VERIFIED, [RapidFuzz](https://github.com/rapidfuzz/RapidFuzz)). MinHash LSH is unnecessary at 10 results per call (datasketch API VERIFIED, [docs](https://ekzhu.com/datasketch/lsh.html), but unneeded). The threshold is tuned on the labelled pairs in E4; **no threshold is claimed in advance**. The panel reports the overlap number and the overlapping passage, not a verdict.

---

## 5. Data plan and PTC terms

**Primary data: PTC news articles.** Registration returns a passcode by email; the team page gives train articles and annotated dev articles; test articles are unannotated; **the data may only be used for academic purposes; manual predictions are forbidden** (VERIFIED, [PTC page](https://propaganda.math.unipd.it/ptc/)). Files: `article<ID>.txt` (title on row 1, empty row 2, body from row 3, one sentence per line) and `article<ID>.task2-TC.labels` (tab-separated `id, technique, begin_offset, end_offset`). 536 articles: 371 train, 75 dev, 90 test; 14 technique classes in TC (VERIFIED, [ar5iv 2009.02696](https://ar5iv.labs.arxiv.org/html/2009.02696)). Because each line is already a sentence, the sentence unit comes free.

**Use dev as test (INFERENCE from the VERIFIED folder status).** The official test folder is unannotated. Plan: split the 371 train articles by article id into about 297 train and 74 validation (my arithmetic at 80/20); thresholds chosen on validation; the 75 dev articles are scored **once** as the held-out test (T11). Published numbers (SemEval-2020 top TC micro-F1 62.07, baseline 25.20; VERIFIED, [ar5iv](https://ar5iv.labs.arxiv.org/html/2009.02696)) use a different task and test set and are not our target.

**Span validation (T3, by 14:45).** Read files with `newline=""`; compute offsets per line (`offset += len(line)+1`; whether title and blank row count is unconfirmed, so try both conventions). Automatic check: fraction of 50 sampled spans where the character before `begin` and after `end` are non-alphanumeric; correct offsets should score high, shifted offsets near chance (INFERENCE). Then print 20 spans and read them. If neither convention passes, fall back to SemEval-2021 (public repo, v1.6.1: 687 train / 63 dev / 200 unlabelled test memes; licence ambiguous: task site says academic-only, README says "free for general research use"; VERIFIED, [GitHub](https://github.com/di-dimitrov/SEMEVAL-2021-task6-corpus)), with unit-level labels if its offsets also fail. Choose the six techniques by measured positives (>= 30 in train+validation; if fewer qualify, ship fewer); repetition is a document-level pattern, so I would exclude it from a sentence classifier (INFERENCE).

**Handling the terms (all INFERENCE about interpretation, flagged as such).**

| Term | How the plan complies | Open question |
|---|---|---|
| Academic use only | Hackathon research prototype; README and metrics page say so | Whether a public hackathon demo counts as academic use is not settled by the page |
| No redistribution | PTC files never go into git, the Docker image, the VPS, or the repo; they stay in an untracked folder on the two laptops. The public site shows **metrics only, no PTC article text**; "known failures" use categories and counts, plus our own demo texts | Whether serving **trained weights and a TF-IDF vocabulary** counts as redistribution is unknown. Mitigation: keep `model.joblib` out of git and out of the image (bind-mounted file), use `min_df >= 5` and `max_features` about 20,000 so rare n-grams from single articles are absent (values are my choice). **Ask a mentor or organiser** (section "Needs your approval") |
| No manual predictions | Read as "predictions on PTC test or dev must be produced by the system; no hand-labelling dev items and no hand-editing predictions". We never hand-label or edit PTC dev items. Our benign set and evidence set are our own data collected from public web pages, not PTC predictions. Error-analysis tags describe causes only and change no labels | The page does not say whether this clause applies outside the leaderboard; we are not submitting to it. Flagged, not resolved |

---

## 6. Evaluation plan

### 6.1 Core protocol (kept from the earlier plan)

| Item | Rule |
|---|---|
| Unit of split | Article id (PTC), never sentence; assert zero group overlap between train, validation and test |
| Thresholds | Per technique on validation only, lowest threshold reaching target precision (starting point 0.70, a team choice, not a promise); technique disabled if never reached |
| Test | PTC dev articles and the benign set, scored **once** in T11; any later tuning makes the number validation-grade and is stated |
| Metrics | Per technique precision, recall and FPR on test negatives, each with Wilson 95% CI; macro-F1; an "always negative" baseline for context (keyword-lexicon baseline is cut) |
| Too-small rule | Fewer than 20 predicted or true positives on test: print "too few examples to support a claim" and still show the CI |
| Score label | "model score", not confidence |

Reference arithmetic (mine, recompute in code): 16/20 correct gives precision 0.80, Wilson CI about 0.58-0.92; 24/30 gives about 0.63-0.90; **0 of 100 false flags still allows a true FPR up to about 3.7%**; 5/100 gives about 2.2-11.2%. Brown, Cai and DasGupta recommend Wilson or Jeffreys over Wald for small n (VERIFIED at abstract level, [Statistical Science](https://projecteuclid.org/euclid.ss/1009213286)).

**Benign set (T9, 1.25 person-hours, about 45 minutes wall time).** 100 items, 20 each: adverts, charity appeals, public-health or civic messages, opinion or product-review sentences, and **plain wire-report news sentences** (new: the PTC domain is news, and the demo includes plain reporting). Plus 10 Finnish items for the abstain path. Inclusion rule written before collecting; collect blind (nobody runs the model first); Exa can find candidates quickly, but copy-paste of short excerpts is the default (Context.dev extraction is optional). Columns: `id, category, source_url, date_accessed, language, excerpt (<= 2 sentences), collector`. Report item-level and sentence-level FPR with Wilson CIs, and mark each flagged item "defensible technique use" (a charity appeal saying "devastating hunger" does use loaded language) or "clear miss", reporting both counts.

**Side-swap test (T14).** Build a symmetric dictionary of at least 20 named-actor pairs (Russia/United States, China/India, Finland/Estonia, alliances, leaders); select test sentences containing at least one entry and report `n_swappable`; swap simultaneously via placeholders; a decision change = the flagged technique set differs or any score crosses its threshold; report invariance failure rate with Wilson CI, the changed sentences, and the entity tokens with the largest LR coefficients. If non-trivial, mask entities at train and inference, retrain and report both. Limits: swaps can create odd sentences; only listed actors and lexical sensitivity are tested, not annotator bias. The invariance idea follows CheckList (PARTIAL, abstract only, [arXiv 2005.04118](https://arxiv.org/abs/2005.04118)); the entity-swap design is mine (INFERENCE).

**Error analysis (T11).** All flagged benign items (up to 30) plus 20 false positives and 20 false negatives drawn by seed from test; two annotators tag the cause (lexical overlap, quoted or reported speech, sarcasm, negation, label noise, short text, domain shift, defensible technique use) and report raw agreement only. For public display, PTC items appear as category counts, not text.

### 6.2 New: the hand-checked evidence set (E4, 26 items, about 1.5 person-hours)

Build in three passes, one hour for A and 0.5 hours for B:

| Part | Items | How to build (about) | Label |
|---|---|---|---|
| **Sourcing** | 12 short paragraphs (6 clearly sourced, 6 unsourced), including 4 Finnish (2 and 2), from the demo outlets and plain wire copy; each with URL and date | 25 min (A) | A and B label independently, per signal: link / named source / attributed quote / figure present (yes/no); reconcile; report raw agreement |
| **Duplicate pairs** | 8 pairs: 4 true near-copies (wire reprints found via Exa), 4 non-duplicates (same event, different outlets, different reporting) | 20 min (A, using Exa results) | duplicate / not; pairs split by article into 4 for tuning the threshold, 4 for reporting |
| **Corroboration** | 6 claims: 3 widely reported (for example "Finland became the 31st NATO member on 4 April 2023"), 2 narrow (a single-outlet opinion claim; a Finnish-language claim), and **1 negative control: a clearly false date written by us and labelled as a control** | 15 min (A) + 30 min run and judge (B) | For up to 5 retained results per claim: (i) does it cover the same claim (y/n), (ii) does it dispute the claim (y/n), (iii) was a wire or same-owner merge correct (y/n) |

Metrics, all with Wilson CIs and n printed:
- Sourcing: per-signal precision and recall against the agreed labels (12 items; if all 12 are correct the lower bound is only about 0.76, my arithmetic).
- Duplicates: precision and recall at the chosen threshold on the 4 held-out pairs plus the 4 tuning pairs shown separately (tuning-grade). Eight pairs support no claim beyond "works on our sample".
- Corroboration: share of counted results that truly cover the same claim (at most 30 judgments, clustered by claim so the effective n is smaller than 30 and the CI is optimistic), the dispute count (shows the stance gap), merge correctness, and whether the **negative control returned "backing found"** (if yes, that is a measured failure to show; 0 of 1 proves nothing).
- Selection is not random; it is hand-picked by two students around one event; Finnish and English only. Say so.

**What to SAY about the evidence layer (script, 25 seconds):** "The evidence layer counts how many independent outlets carry the same claim and shows the other sides' wording. It does not tell you the claim is true. It cannot tell if an outlet agrees or disputes it. A search can miss real coverage, so 'not found' does not mean false. We tested it on 26 hand-picked items by two students, so the intervals are wide and we show them."

---

## 7. Deployment (IP only, HTTP)

Syntax comes from verified docs; the combination is untested ([FastAPI Docker docs](https://fastapi.tiangolo.com/deployment/docker/), [Compose reference](https://docs.docker.com/reference/compose-file/services/), [Docker Hub caddy](https://hub.docker.com/_/caddy)). Commands marked INFERENCE come from general knowledge.

**Hour-1 checks (B, T1).**
1. hPanel: read the VPS IP and root credentials; `ssh root@<VPS_IP>` (INFERENCE).
2. hPanel managed firewall: accept TCP 22 and 80 before activating; a missing SSH rule can lock you out (PARTIAL, [Hostinger firewall](https://www.hostinger.com/support/8172641-how-to-use-a-managed-vps-firewall-at-hostinger/)). Check the OS firewall: `ufw status` (INFERENCE).
3. `docker --version && docker compose version`. **If Docker is missing** (all commands INFERENCE, untested): `curl -fsSL https://get.docker.com | sh`, then `systemctl enable --now docker`, then re-check. The Hostinger brief also lists VPS templates; choosing a Docker template when (re)provisioning is an alternative, but Docker Manager and template documentation were not found in the notes, so ask the Hostinger mentor before reinstalling the OS image, which would erase the VPS.
4. Enable Docker on boot (`systemctl enable docker`, INFERENCE).

**Layout** (`/opt/noise`): `Dockerfile`, `requirements-serve.txt`, `app/`, `models/` (bind-mounted, holds `model.joblib`, not in git), `static/`, `conf/Caddyfile`, `docker-compose.yml`, `deploy.sh`, `.env`.

**Dockerfile** (CMD form and `--proxy-headers` VERIFIED; port 8000, spaCy download step INFERENCE):
```
FROM python:3.12-slim
WORKDIR /code
COPY requirements-serve.txt .
RUN pip install --no-cache-dir --upgrade -r requirements-serve.txt \
 && python -m spacy download fi_core_news_sm && python -m spacy download en_core_web_sm
COPY ./app /code/app
CMD ["fastapi", "run", "app/main.py", "--proxy-headers", "--port", "8000"]
```
Add `.env`, `models/`, `data_raw/` and any `*.joblib` to `.dockerignore`.

**Secrets file** (no echo; INFERENCE). On the VPS:
```
umask 077
for v in EXA_API_KEY CONTEXT_API_KEY HOSTINGER_AI_ROUTER_KEY; do read -rs -p "$v: " x; echo; printf '%s=%s\n' "$v" "$x" >> .env; done; unset x
printf 'LLM_MODEL=%s\n' "<id-from-Models-page>" >> .env
printf '.env\n' >> .gitignore; printf '.env\n' >> .dockerignore
git check-ignore -v .env     # must print a match
```
Never `cat .env`; avoid `docker compose config` and `docker inspect` on a shared screen since they may print environment values (INFERENCE). Before every push: `git diff --cached | grep -nE "API_KEY|sk-"` must return nothing. The code reads those three variables with `os.environ` and never prints them.

**docker-compose.yml** (restart policy, healthcheck syntax, `depends_on: condition: service_healthy` VERIFIED; python-based healthcheck and `/health` route INFERENCE):
```yaml
services:
  app:
    build: .
    restart: unless-stopped
    env_file: .env
    volumes:
      - ./models:/code/models:ro
      - ./cache:/code/cache
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request;urllib.request.urlopen('http://localhost:8000/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
  proxy:
    image: caddy:2
    restart: unless-stopped
    ports: ["80:80"]
    volumes:
      - ./conf:/etc/caddy
      - ./static:/srv/static:ro
    depends_on:
      app:
        condition: service_healthy
```
**Caddyfile for IP-only HTTP** (syntax from memory, INFERENCE: an address of `:80` serves plain HTTP without automatic HTTPS, whereas a hostname enables it; VERIFIED only for the hostname case, [Caddy reverse proxy quick-start](https://caddyserver.com/docs/quick-starts/reverse-proxy)):
```
:80 {
    handle_path /static/* {
        root * /srv/static
        file_server
    }
    handle {
        reverse_proxy app:8000
    }
}
```
If Caddy gives trouble, drop the `proxy` service and publish the app directly with `ports: ["80:8000"]`; the static metrics page then lives inside the app.

**Steps.** (1) `docker compose up -d --build`; `docker compose ps`; `docker compose logs --tail=50` (INFERENCE). (2) `curl -fsS http://<IP>/health` from the laptop and from a phone on mobile data. (3) `scp models/model.joblib root@<IP>:/opt/noise/models/` (PTC-derived artefact never goes through git). (4) `deploy.sh` (B writes in T13): `git pull`, `docker compose up -d --build`, `curl /health`, tag the previous image for rollback; A runs it overnight only after local tests. (5) **Reboot the VPS once in T13 and confirm the site returns by itself.** (6) Uptime watch from a laptop: `while true; do curl -fsS -o /dev/null -w "%{http_code}\n" http://<IP>/health || echo FAIL; sleep 60; done`. (7) Input safety: cap pasted text at 5000 characters, never show a stack trace, log lengths and hashes not full text, provide example buttons so judges need not type. (8) Privacy banner: HTTP is not encrypted and claims are sent to Exa; "do not paste personal or confidential text".

**Optional stretch: domain and automatic HTTPS (not scheduled; cost 0 only if a domain is already owned).** Start only if a domain is already available and its A records for `@` and `www` point to the VPS IP before Saturday evening; Hostinger says propagation can take up to 24 hours (VERIFIED, [Hostinger](https://www.hostinger.com/support/1583227-how-to-point-a-domain-to-your-vps-at-hostinger/)). Then open 443 in the hPanel firewall, add `"443:443"` and `"443:443/udp"` plus volumes `caddy_data:/data` and `caddy_config:/config` to the `proxy` service, and replace `:80` with `yourdomain.tld, www.yourdomain.tld {` ... `}` (VERIFIED requirements: DNS pointing at the server, ports 80 and 443 reachable, persistent data directory; [Caddy automatic HTTPS](https://caddyserver.com/docs/automatic-https)). Test with the staging CA first (`acme_ca https://acme-staging-v02.api.letsencrypt.org/directory`, URL VERIFIED, global option name INFERENCE), then remove it and run `docker compose exec -w /etc/caddy proxy caddy reload` (VERIFIED pattern). **Never wipe `caddy_data`** and do not hammer broken DNS: limits are 5 certificates per identifier set per 7 days and 5 failed authorisations per hour (VERIFIED, [Let's Encrypt limits](https://letsencrypt.org/docs/rate-limits/)). Do not change the final URL after 06:00; if HTTPS is not green by then, the IP URL stays the submission.

**Minimal key tests (T5; key read from the environment, never printed; do not use `curl -v`, which prints headers).** On the VPS or laptop in bash after `export` via `read -rs` (on Windows PowerShell use `curl.exe` and `$env:NAME`):
```
# AI Router: list models at runtime (the /v1/models endpoint is unconfirmed, INFERENCE)
curl -s -o models.json -w "%{http_code}\n" https://router.hostinger.com/v1/models -H "Authorization: Bearer $HOSTINGER_AI_ROUTER_KEY"
python -c "import json;print([m['id'] for m in json.load(open('models.json'))['data']])"
# AI Router: one tiny call (chat/completions is documented; some newer models may want max_completion_tokens instead)
curl -s https://router.hostinger.com/v1/chat/completions -H "Authorization: Bearer $HOSTINGER_AI_ROUTER_KEY" -H "Content-Type: application/json" -d "{\"model\":\"$LLM_MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with the single word OK\"}],\"max_tokens\":5}"
# Exa: three results with cost
curl -s https://api.exa.ai/search -H "x-api-key: $EXA_API_KEY" -H "Content-Type: application/json" -d '{"query":"Finland joins NATO Russia countermeasures","category":"news","numResults":3,"startPublishedDate":"2023-04-01T00:00:00Z","endPublishedDate":"2023-04-30T23:59:59Z"}' | python -c "import sys,json;r=json.load(sys.stdin);print([x['url'] for x in r['results']], r.get('costDollars'))"
```
Balance cannot be read from an API that the notes found; check it in hPanel. For Context.dev, one `POST https://api.context.dev/v1/web/scrape` with `{"url": "...", "formats": {"markdown": true}}` and a Bearer header; the response `key_metadata` shows credits remaining (VERIFIED field names). Throttle to 10 requests per minute client-side until the plan's real limit is known.

---

## 8. Fallbacks and the bail-out

### 8.1 Fallbacks

| Failure | Detection | Fallback (no workaround of safety behaviour) |
|---|---|---|
| **Exa down, 4xx/5xx, 402 or 429 quota** | Exception or HTTP status (400, 401, 402, 403, 429, 500, 503 are the documented errors; VERIFIED); 6 s timeout | Show cached results for that claim if present, badge "saved results from <date>", else "Evidence unavailable". Circuit breaker: after 3 consecutive failures stop calling for 60 s. Detector and stage 1 are unaffected |
| Exa returns off-topic or empty | Relevance filter keeps zero | "No matching coverage found in the sources searched; this does not mean false" |
| Context.dev down or rate-limited | Exception, 429 | Use Exa result text; "paste a URL" mode shows "could not read that page; paste the text instead" |
| **AI Router outage, refusal, empty or malformed output** (optional explanation only) | Exception; 8 s timeout; response check | Show the bare label with fixed template text. **Do not reword prompts, switch models or retry to get around a refusal**; count refusals on the metrics footnote. The core never calls the router |
| Slow response | Request time > 3 s | Return technique flags first; load the evidence panel asynchronously with a 6 s cap and a spinner |
| Judge input surprises | Language ID, length, quote heuristic | Cannot-determine states; example buttons |
| App container down | `/health` failing, proxy 502 | `restart: unless-stopped`; `docker compose up -d`; roll back to the tagged image |
| Demo broken on stage | Anything | (1) recorded 3-minute screen backup of the real tool (D5); (2) static metrics page at `http://<IP>/static/metrics_static.html`, plus PDF and screenshots in the slides; (3) `?offline=1` switch that forces cached evidence so the demo never depends on live search |
| Network at the venue blocks the VPS | Phone check fails | Use mobile hotspot; recording as last resort |

### 8.2 Bail-out: web-log bot classifier on Zenodo 3477932 (one-page plan, retained)

**Trigger:** no usable labelled data by 15:30 (neither PTC nor SemEval-2021 loads and validates), or baseline macro-F1 over the six techniques < 0.3 on validation at 17:30. The rule can trip for honest reasons (rare-class F1 of zero drags macro-F1), so choose the six by measured count and compute at the default threshold; within 0.05 of 0.3, ask a mentor first (INFERENCE).

**Facts (VERIFIED, [Zenodo record](https://zenodo.org/records/3477932), [API](https://zenodo.org/api/records/3477932)):** "Web robot detection - Server logs", CC BY 4.0 (attribution required), Aristotle University of Thessaloniki library search-engine logs, 1-31 March 2018, 4,091,155 requests, 27,061 unique IPs, 3,441 user-agent strings, IPs partly masked and URL parts hashed. Files: `simple_features.csv` (15,913,454 bytes), `semantic_features.csv` (4,348,560 bytes), `public_v2.json` (3.2 GB, skip). **Not seen:** column names, label values, class balance. It covers only the "bots" direction and is unrelated to propaganda text (INFERENCE).

**Re-budget.** About 7.0 person-hours are spent by 17:30 (T1-T6 = 5.25 plus about 1.7 of T7, my arithmetic); the pivot costs 11.25; adding D4 (1.0) and D5 (1.25) gives about 20.5 of 25, leaving about 4.5 hours. The evidence layer is independent of the technique labels; with the leftover hours, E1 and E2 could be kept as a second tab (about 3.75 hours), but scattering the pitch across two products is a risk, so decide with a mentor (INFERENCE).

| Step | Owner | Hours |
|---|---|---|
| b1 Download the two CSVs (about 20.3 MB), print columns, find the label column and class balance; if none exists, stop and tell a mentor | A | 0.50 |
| b2 Leakage check and split; group by IP or session id if present | A | 0.50 |
| b3 Baselines: logistic regression and a tree ensemble; threshold for precision on validation | A | 1.50 |
| b4 Metrics: precision, recall, FPR = humans called robots, Wilson CIs | A | 1.00 |
| b5 Abstain for sessions with too few requests or missing features | A | 0.50 |
| b6 App: paste a feature row or choose a sample session -> verdict, score, top features | B | 2.00 |
| b7 Metrics page and known failures (A 0.5, B 1.5) | A+B | 2.00 |
| b8 Demo, slides, recording | A+B | 2.00 |
| b9 Hardening and submission (reuses the placeholder deployment) | A+B | 1.25 |
| **Sum** | | **11.25** |

Limits to print: one library's traffic from one month in 2018; labels come from the dataset (provenance not seen); generalisation unknown; the tool classifies sessions, not people.

---

## 9. Demo script (about 4:30 of content in a 5:00 slot)

**Reference line (say it once, put it on slide 6):** "We picked one niche: coverage of Finland joining NATO on 4 April 2023 across Russian, Chinese, exile, Finnish and Western outlets. We picked one problem: how a text is worded and how well its claim is backed. We tested it on PTC held-out news articles, a 100-item benign set, a side-swap test and a 26-item hand-checked evidence set; every interval is on the Metrics page."

**Quotes must be re-copied from the live pages before use (D1, 00:30).** The notes obtained them through page summaries, not raw HTML, so treat strings as "as returned", keep each under 40 words, label opinion as opinion, and do not script outcomes: run them Saturday night and again after 07:00, and say only what the tool showed.

| # | Paste text (as returned; re-copy) | Source | Tag |
|---|---|---|---|
| 1 | `There is no doubt that when NATO's "strategic plague" spreads to Asia, its primary target is China.` | Global Times, 9 Apr 2023, unsigned "Observer" opinion, [link](https://globaltimes.cn/page/202304/1288763.shtml) | VERIFIED as returned; opinion, five days after the event |
| 2 | TASS, Zakharova: US officials "guided by opportunistic interests that have no relation to the security of Europe." Re-copy the whole sentence | TASS, 5 Apr 2023, [link](https://tass.com/politics/1599779/amp) | VERIFIED fragment only |
| 3 | `Naturally, this forces us to take countermeasures to ensure our own tactical and strategic security,` and `Finland became the 31st member of the U.S.-led military alliance after a historic strategic shift.` | Moscow Times, 4 Apr 2023, [link](https://www.themoscowtimes.com/2023/04/04/russia-warns-of-countermeasures-to-finlands-nato-membership-a80704) | VERIFIED as returned |
| 4 | `Venäjä varoitti tiistaina vastatoimista Suomen Nato-jäsenyyden vuoksi.` (our gloss: Russia warned on Tuesday of countermeasures over Finland's NATO membership) | Yle, 4 Apr 2023, [link](https://yle.fi/a/74-20010573/64-3-146954) | VERIFIED as returned |
| 5 | Failure candidate: our English gloss of the Yle 5 Apr headline (Russian media reacted sourly; journalist suggests nuclear mines on the Finnish border); label it "our translation, not Yle's text" | Yle, [link](https://yle.fi/a/74-20025957) | Headline VERIFIED as returned; "nuclear mines" appears in the headline only |
| 6 | Reuters via RFE/RL sentence on "countermeasures" | RFE/RL copy, [link](https://www.rferl.org/amp/finland-joins-nato-russia-countermeasures/32349063.html) | PARTIAL: paraphrased, only "countermeasures" confirmed |

Search claims for the corroboration panel: **C1** "Finland became the 31st member of NATO on 4 April 2023" (VERIFIED event: [Finnish government release](https://valtioneuvosto.fi/-/suomi-liittyy-natoon-4.-huhtikuuta) and [Moscow Times](https://www.themoscowtimes.com/2023/04/04/russia-warns-of-countermeasures-to-finlands-nato-membership-a80704)); **C2** Russia announced countermeasures to Finland's accession; **C3** the Global Times "strategic plague" opinion (a narrow claim, likely to show "not found"; confirm Saturday, INFERENCE). The Peskov quote appears in three wordings (TASS "yet another escalation"; Moscow Times "forces us to take countermeasures..."; Xinhua "forces Russia to take counter-measures to ensure its own security"; wording as returned, [People's Daily](https://en.people.cn/n3/2023/0405/c90000-20001676.html)): showing them scored side by side is a cheap cross-outlet demonstration.

| Slide | Time | Content and exact steps |
|---|---|---|
| 1 | 0:00-0:25 | Niche and problem in one line each; **what we do not claim** (not truth, not intent, not who is right; "not found" is not "false") |
| 2 | 0:25-2:00 | **Live demo at `http://<VPS-IP>`** (cached mode ready via `?offline=1`). Step 1: paste #1 -> technique chips, then Cites line (read it aloud as shown), then claim box, then evidence panel. Step 2: paste #3 (plain reporting by an exile outlet) -> contrast. Step 3: C1 -> "Backing found: N origins (M copies merged), stance not checked" and the **other-side view**: cards for Russian state, Chinese state-linked, exile, Finnish public and Western outlets with links. Step 4: paste #4 (Finnish) -> detector says "cannot determine, English only" while the sourcing signals still run in Finnish |
| 3 | 2:00-2:30 | **Re-sharing and merging**: show the three Peskov wordings, or a wire copy merged into one origin, with the overlap number and passage; "near-identical text, no new sourcing" if it fires |
| 4 | 2:30-3:15 | **Metrics page**: per-technique precision, recall and FPR with CIs; benign FPR with CI; side-swap invariance failure rate; evidence-set results with n; the sentence "n is too small to claim X" wherever true |
| 5 | 3:15-3:50 | **One failure slide**: the measured top failure (candidate: reported speech like #5; or the negative-control claim returning topical coverage; or a retained page that disputes the claim being counted as backing). State the cause and the fix we did not build |
| 6 | 3:50-4:15 | Deployment and fallbacks: live on the Hostinger VPS, Docker, health check, restart policy, cached evidence if search is down. Then the reference line |
| 7 | 4:15-4:30 | Impact, same rules for every side, next step (domain and HTTPS, Finnish training data, stance classification). Leaves about 30 s margin |

If sentence #5 is not flagged, use the top failure from the error analysis instead. If the live URL fails on stage, play the recording and show the static metrics page.

---

## 10. Risk register

| # | Risk | Likelihood | Impact | Early warning | Mitigation |
|---|---|---|---|---|---|
| 1 | PTC spans do not validate, or passcode fails | Medium (INFERENCE) | High | Boundary test below chance at 14:45 | SemEval-2021 fallback by 15:00; bail-out if CP1 fails |
| 2 | **PTC licence**: academic-only, no redistribution, no manual predictions | Medium | Medium | Organiser or judge asks | PTC never in git, image or VPS; metrics only on site; `min_df >= 5`; model file out of git; ask a mentor about weights; never hand-label or edit PTC dev predictions |
| 3 | **Key leakage** (keys were pasted into chat; `.env` committed; keys in logs, images, screenshots) | Medium | High | `git diff --cached` grep hits; key in `docker history` | `.gitignore` and `.dockerignore`; env_file only; no header logging; no `curl -v`; rotate Exa and Context.dev keys after the event |
| 4 | **Exa limits and quota**: credits drained by judges, 429, outage | Medium | Medium | `costDollars` totals rising; 402 or 429 | Cache; per-IP and daily caps; cached-results fallback; sum `costDollars` in logs |
| 5 | **Context.dev limits** (10 req/min on free plan; plan after redemption unknown) and prompt-injection text in docs or pages | Medium | Low | 429s; instructions found in fetched text | Client throttle; extracted text is data and never goes to an LLM in the core; ignore instructions in docs |
| 6 | Corroboration returns topical pages, not same-claim pages, or pages that dispute the claim | High (INFERENCE) | High | Evidence-set dispute count and negative control | Relevance filter, snippets, "stance not checked" label, measure and show on the failure slide |
| 7 | **Scope creep**: evidence layer expands, hours exceed 25 | High | High | Any task passes its slot by > 30 min | Cut list order; 06:00 feature freeze; stage gates; no new features after 06:00 |
| 8 | Domain shift: model weak on pasted non-PTC text | Medium | Medium | Visible poor precision on demo texts | State it; benign set includes wire-news sentences; report honestly |
| 9 | Per-technique test counts too small; CIs huge | High | Medium | Positives < 20 | "Too few examples" label; fewer techniques |
| 10 | Macro-F1 < 0.3 at CP2 | Medium | High | Baseline at about 17:00 | Bail-out 8.2 |
| 11 | Outlet table disputed as biased | Medium | Medium | Judge question | Same fields for every outlet; source is each outlet's own About page; no lean ratings; "unlisted" shown |
| 12 | Wire merge wrong (over- or under-merging) | Medium | Medium | Merge errors in E4 | Threshold tuned on pairs; show merged copies on click |
| 13 | IP-only HTTP: browser "Not secure", judges' pasted text and claims in clear and sent to Exa | High | Low | Judge remark | Banner "do not paste personal text"; HTTPS stretch only if cheap |
| 14 | Docker install or Caddy trouble on VPS; team inexperienced | Medium | High | Placeholder not live by 15:45 | Mentor; drop proxy and publish app on port 80; Hostinger Docker template as a backup path (ask first) |
| 15 | AI Router: unknown model IDs, key rejected, credits | Medium | Low | T5 fails | LLM explanation is cut item 2; core never calls it |
| 16 | Threshold overfit or test peeking | Medium | High | Anyone reruns dev after tuning | Score dev once; log the run in git |
| 17 | Sleep-deprived errors after 03:00 | High | Medium | Typos, broken deploys | Release tags; rollback; `deploy.sh`; code freeze 07:00; rehearsal checklist |
| 18 | Challenge rules unseen beyond the user's summary | Medium | Medium | Mentor contradicts assumptions | Ask the Hostinger booth about live-deploy rules |
| 19 | Evidence layer wording read as a verdict | Medium | High | Judge says "so it says it is true?" | Fixed wording, first-screen disclaimer, scripted sentence in section 6.2 |

---

## Conclusion

The new information changes the shape of the product more than the hours. Because the mentors reward well-backed claims and visible other sides over a verdict, the evidence layer is the pitch, and the measured technique detector is its credibility: the detector gives the 40% bucket its numbers, and the evidence layer gives the demo its point. The cut order reflects that: the LLM explanation and the stand-alone re-sharing panel go before any sourcing or corroboration work, and the plan keeps a cached-results path so the demo never depends on live search. The weakest link is not engineering but meaning: a search engine returns topical pages, not agreeing pages, so the honest framing "stance not checked" and a negative-control failure slide are worth more on stage than a polished panel.

Two decisions remain open and cost nothing to ask: whether serving PTC-trained weights counts as redistribution, and whether "no manual predictions" reaches beyond the leaderboard. Until a mentor answers, the plan keeps the model file out of git, ships metrics only, and says so in the README.

---

## Sources (opened by the notes behind this plan)

| Source | Link | Tag |
|---|---|---|
| PTC / SemEval-2020 T11 data page | https://propaganda.math.unipd.it/ptc/ | VERIFIED |
| SemEval-2020 T11 overview (ar5iv) and abstract | https://ar5iv.labs.arxiv.org/html/2009.02696 ; https://aclanthology.org/2020.semeval-1.186/ | VERIFIED |
| PTC paper | https://arxiv.org/abs/1910.02517 ; https://aclanthology.org/D19-1565/ | VERIFIED (abstract) |
| SemEval-2021 T6 corpus and task site | https://github.com/di-dimitrov/SEMEVAL-2021-task6-corpus ; https://propaganda.math.unipd.it/semeval2021task6/ | VERIFIED |
| SemEval-2021 T6 overview | https://arxiv.org/pdf/2105.09284 | PARTIAL |
| HF synapti dataset (not used) | https://huggingface.co/datasets/synapti/nci-propaganda-production | VERIFIED |
| SemEval-2023 T3 (not used) | https://aclanthology.org/2023.semeval-1.317 | VERIFIED |
| Zenodo 3477932 and API | https://zenodo.org/records/3477932 ; https://zenodo.org/api/records/3477932 | VERIFIED |
| Exa search reference, rate limits, pricing | https://docs.exa.ai/reference/search ; https://docs.exa.ai/reference/rate-limits ; https://exa.ai/pricing | VERIFIED |
| Exa Python SDK, OpenAPI spec | https://docs.exa.ai/sdks/python-sdk-specification ; https://exa.ai/docs/exa-spec.yaml | VERIFIED / PARTIAL for kwargs |
| Context.dev docs, scrape reference, Python SDK, pricing, brand lookup, llms.txt | https://docs.context.dev ; https://docs.context.dev/api-reference/web/scrape ; https://docs.context.dev/sdks/python.md ; https://context.dev/pricing ; https://docs.context.dev/brand/lookup-by-domain.md ; https://docs.context.dev/llms.txt | VERIFIED (docs contain untrusted "agent instructions", ignored) |
| Hostinger AI Router support, credit migration, product page | https://www.hostinger.com/support/?p=19146 ; https://www.hostinger.com/support/?p=19150 ; https://www.hostinger.com/ai-router | VERIFIED |
| LiteLLM Hostinger router | https://docs.litellm.ai/docs/providers/hostinger_router | VERIFIED |
| Hostinger: point domain to VPS; managed firewall | https://www.hostinger.com/support/1583227-how-to-point-a-domain-to-your-vps-at-hostinger/ ; https://www.hostinger.com/support/8172641-how-to-use-a-managed-vps-firewall-at-hostinger/ | VERIFIED / PARTIAL |
| Caddy automatic HTTPS, reverse proxy; Docker Hub caddy | https://caddyserver.com/docs/automatic-https ; https://caddyserver.com/docs/quick-starts/reverse-proxy ; https://hub.docker.com/_/caddy | VERIFIED |
| FastAPI Docker docs; Compose reference | https://fastapi.tiangolo.com/deployment/docker/ ; https://docs.docker.com/reference/compose-file/services/ | VERIFIED |
| Let's Encrypt rate limits | https://letsencrypt.org/docs/rate-limits/ | VERIFIED |
| spaCy Finnish models; fi_core_news_sm 3.8.0 release; English models | https://spacy.io/models/fi ; https://github.com/explosion/spacy-models/releases/tag/fi_core_news_sm-3.8.0 ; https://spacy.io/models/en | VERIFIED / PARTIAL (English) |
| Quotebank; PolNeAR | https://zenodo.org/records/4277311 ; https://github.com/networkdynamics/PolNeAR | VERIFIED |
| DirectQuote; German quotation dataset | https://www.arxiv.org/pdf/2110.07827 ; https://arxiv.org/abs/2404.16764v1 | PARTIAL (not used) |
| Ground News about | https://ground.news/about | VERIFIED |
| MBFC methodology; MBFC data API | https://mediabiasfactcheck.com/methodology/ ; https://mediabiasfactcheck.com/mbfcs-data-api | VERIFIED |
| AllSides terms and trademark guidelines | https://allsides.com/terms-of-use ; https://allsides.com/trademark-guidelines | PARTIAL (search snippets) |
| Ad Fontes methodology | https://adfontesmedia.com/methodology/ | PARTIAL |
| datasketch LSH; RapidFuzz | https://ekzhu.com/datasketch/lsh.html ; https://github.com/rapidfuzz/RapidFuzz | VERIFIED |
| Brown, Cai, DasGupta (Wilson intervals) | https://projecteuclid.org/euclid.ss/1009213286 | VERIFIED (abstract level) |
| Fact-check labelling: COVID study, FEVER 2025, Meta | https://arxiv.org/pdf/2005.06915v2 ; https://preview.aclanthology.org/display_plenaries/2025.fever-1.8.pdf ; https://transparency.meta.com/features/how-fact-checking-works/ | PARTIAL |
| LLM propaganda papers | https://arxiv.org/abs/2310.06422 ; https://arxiv.org/abs/2505.13706 | PARTIAL (abstracts; they conflict, which is why the LLM baseline is cut) |
| HF model cards (cut upgrade) | https://huggingface.co/distilbert/distilroberta-base ; https://huggingface.co/microsoft/deberta-v3-small ; https://huggingface.co/answerdotai/ModernBERT-base | VERIFIED |
| scikit-learn pages; statsmodels; lingua-py; fastText LID; langdetect | https://scikit-learn.org/stable/modules/generated/sklearn.calibration.CalibratedClassifierCV.html ; https://www.statsmodels.org/stable/generated/statsmodels.stats.proportion.proportion_confint.html ; https://github.com/pemistahl/lingua-py ; https://fasttext.cc/docs/en/language-identification.html ; https://pypi.org/project/langdetect/ | VERIFIED |
| CheckList | https://arxiv.org/abs/2005.04118 | PARTIAL |
| Demo pages: TASS, Global Times, Xinhua via People's Daily, Moscow Times, RFE/RL, Yle, Finnish government | https://tass.com/politics/1599137/amp ; https://tass.com/politics/1599779/amp ; https://globaltimes.cn/page/202304/1288763.shtml ; https://en.people.cn/n3/2023/0405/c90000-20001676.html ; https://www.themoscowtimes.com/2023/04/04/russia-warns-of-countermeasures-to-finlands-nato-membership-a80704 ; https://www.rferl.org/amp/finland-joins-nato-russia-countermeasures/32349063.html ; https://yle.fi/a/74-20010573/64-3-146954 ; https://yle.fi/a/74-20025957 ; https://yle.fi/a/74-20025131 ; https://valtioneuvosto.fi/-/suomi-liittyy-natoon-4.-huhtikuuta | VERIFIED as returned / PARTIAL (TASS 1599137, Xinhua, RFE/RL) |
| Junction 2026 listing | https://www.espoo.fi/en/events/espooevents:agp767vqb4 | PARTIAL |
| Not opened or not used | Press TV copy (HTTP 403), Al Jazeera, Helsingin Sanomat, RT; the Hostinger challenge text itself (only the user's summary was available); Hostinger Docker template documentation | Gap |

---

## Needs your approval

Budget is EUR 0 and nothing in this plan requires a purchase, a new account, or a paid tier.

| Item | Why | Without it |
|---|---|---|
| Ask a mentor or organiser whether serving a model trained on PTC (weights and TF-IDF vocabulary) on the public VPS counts as redistribution, and whether the "no manual predictions" clause applies outside the leaderboard | Terms are ambiguous on both points | The plan already keeps PTC data out of git, image and site, keeps the model file out of git, and ships metrics only; the question only decides whether those mitigations are enough |
