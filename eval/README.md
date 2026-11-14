# Measuring the detectors

Each script writes its own section of `results.json`, which the accuracy page (`/metrics.html`) shows as is.

| Script | Measures | Needs |
|---|---|---|
| `python -m eval.run_similar` | Copy detection on edited copies of real texts | nothing |
| `python -m eval.run_bots` | Bot-likeness on 120 labelled accounts (`bots.csv`) | `--refresh` reads Bluesky; otherwise the saved snapshot |
| `python -m eval.run_techniques --api <server>` | Techniques against SemEval-2021 Task 6 labels | AI credits, about 40 minutes at the site's rate limit |

Rules: never edit `results.json` by hand; quote hold-out numbers, not tune-set numbers; keep the sample size next to every rate.

Data: `data/semeval2021_task6_test.json` is the test set of SemEval-2021 Task 6 (Dimitrov et al., 2021),
from github.com/di-dimitrov/SEMEVAL-2021-task6-corpus, free for research use.
