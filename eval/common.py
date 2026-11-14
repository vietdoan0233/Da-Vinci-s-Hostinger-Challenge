"""Shared by the eval scripts: confidence intervals and the results file."""
import datetime
import json
import math
import pathlib

HERE = pathlib.Path(__file__).parent
RESULTS = HERE / "results.json"


def wilson(k, n, z=1.96):
    """95% Wilson interval for k successes in n trials -> (low, high). Honest for small samples."""
    if n == 0:
        return None
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(max(0.0, centre - half), 3), round(min(1.0, centre + half), 3)]


def rate(k, n):
    """A proportion with its sample size and interval, or None when there is nothing to divide by."""
    return None if n == 0 else {"value": round(k / n, 3), "k": k, "n": n, "ci95": wilson(k, n)}


def save_section(name, data):
    """Each script owns one section of results.json and leaves the others alone."""
    results = json.loads(RESULTS.read_text()) if RESULTS.exists() else {}
    data["run_at"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    results[name] = data
    RESULTS.write_text(json.dumps(results, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {name} to {RESULTS}")
