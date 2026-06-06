"""Read-side metrics view for the model-selection eval.

Re-reads a results JSONL (raw RunRecords) plus the labeled dataset and reports the
model-selection metrics as a *view*: schema-validity, MAE, threshold agreement,
Spearman, consistency, median cost, P50 latency. Never calls the API — every number
is derived from saved records, so the report is free to re-run as often as you like.

    python eval/metrics.py [path/to/run-<ts>.jsonl]   # defaults to the latest run

Two metrics stay manual and are NOT computed here: extract_requirements coverage
(needs semantic judgement, not string-equality against must_haves) and tailor_cv's
hallucination_flag. Those are eyeballed on a few samples per MODEL_SELECTION.md.
"""

import statistics
import sys
from collections import defaultdict
from pathlib import Path

from schemas import TAILOR_MIN_SCORE, JobLabel, RunRecord

HERE = Path(__file__).parent
RESULTS = HERE / "results"
JOBS = HERE / "datasets" / "jobs.jsonl"

THRESHOLD = 70  # the >=70 action boundary that triggers tailoring
SCORE_TASK = "score_match"  # the only task graded against expected_score
TAILOR_TASK = (
    "tailor_cv"  # TAILOR_MIN_SCORE (the >=60 eval boundary) lives in schemas.py
)


def load_records(path: Path) -> list[RunRecord]:
    """Parse a results JSONL into RunRecords (the raw evidence)."""
    records: list[RunRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(RunRecord.model_validate_json(line))
    return records


def load_expected() -> dict[str, int]:
    """Map each job_id to its labeled expected_score (the answer key)."""
    expected: dict[str, int] = {}
    for line in JOBS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            job = JobLabel.model_validate_json(line)
            expected[job.id] = job.expected_score
    return expected


def latest_results() -> Path:
    """The most recent run-*.jsonl in results/ (the timestamp name sorts lexically)."""
    runs = sorted(RESULTS.glob("run-*.jsonl"))
    if not runs:
        raise FileNotFoundError(
            f"No run-*.jsonl files in {RESULTS} — run model_eval.py first."
        )
    return runs[-1]


def group_by_assignment(
    records: list[RunRecord],
) -> dict[tuple[str, str], list[RunRecord]]:
    """Bucket the flat record list into one list per (model, task) assignment."""
    groups: defaultdict[tuple[str, str], list[RunRecord]] = defaultdict(list)
    for r in records:
        groups[(r.model, r.task)].append(r)
    return dict(groups)


def scores_by_job(group: list[RunRecord]) -> dict[str, list[int]]:
    """Per job_id, the list of valid repeat scores (invalid/score-less runs dropped)."""
    by_job: defaultdict[str, list[int]] = defaultdict(list)
    for r in group:
        if r.schema_valid and r.output and "score" in r.output:
            by_job[r.job_id].append(int(r.output["score"]))
    return dict(by_job)


def general_metrics(group: list[RunRecord]) -> tuple[int, float, float, float]:
    """Metrics that apply to every task: run count, validity rate, median cost, P50 latency."""
    runs = len(group)
    validity = statistics.fmean(r.schema_valid for r in group)
    median_cost = statistics.median(r.cost_usd for r in group)
    p50_latency = statistics.median(r.latency_s for r in group)
    return runs, validity, median_cost, p50_latency


def score_metrics(
    group: list[RunRecord], expected: dict[str, int]
) -> tuple[float | None, float | None, float | None, float | None]:
    """Accuracy metrics for score_match: (MAE, threshold agreement, Spearman, consistency).

    Each job's 3 repeats are collapsed to their median (the point estimate) before
    MAE/threshold/Spearman; consistency is a separate read of the same repeats' spread.
    Any element is None when there isn't enough data to compute it.
    """
    by_job = scores_by_job(group)
    # Collapse repeats -> one score per job, aligned with jobs we have a label for.
    collapsed = {jid: statistics.median(s) for jid, s in by_job.items() if s}
    jids = [j for j in collapsed if j in expected]
    pred = [collapsed[j] for j in jids]
    exp = [expected[j] for j in jids]

    mae = statistics.fmean(abs(p - e) for p, e in zip(pred, exp)) if pred else None
    agreement = (
        statistics.fmean(
            (p >= THRESHOLD) == (e >= THRESHOLD) for p, e in zip(pred, exp)
        )
        if pred
        else None
    )
    spearman = (
        statistics.correlation(pred, exp, method="ranked") if len(pred) >= 2 else None
    )

    # Consistency: average per-job spread of the repeats (lower = steadier). Needs >=2
    # valid repeats per job to have any spread to measure.
    spreads = [statistics.pstdev(s) for s in by_job.values() if len(s) >= 2]
    consistency = statistics.fmean(spreads) if spreads else None

    return mae, agreement, spearman, consistency


def _fmt(value: float | None, spec: str) -> str:
    """Format a metric, or 'n/a' when it couldn't be computed."""
    return format(value, spec) if value is not None else "n/a"


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else latest_results()
    records = load_records(path)
    expected = load_expected()
    groups = group_by_assignment(records)

    print(f"Results: {path.name}  ({len(records)} runs)\n")
    for model, task in sorted(groups):
        group = groups[(model, task)]
        if task == TAILOR_TASK:
            group = [r for r in group if expected.get(r.job_id, 0) >= TAILOR_MIN_SCORE]
        runs, validity, median_cost, p50 = general_metrics(group)
        print(f"{task} · {model}")
        print(
            f"  runs={runs}  valid={validity:.0%}  "
            f"median_cost=${median_cost:.5f}  p50_latency={p50:.2f}s"
        )
        if task == SCORE_TASK:
            mae, agreement, spearman, consistency = score_metrics(group, expected)
            print(
                f"  MAE={_fmt(mae, '.1f')}  threshold_agree={_fmt(agreement, '.0%')}  "
                f"spearman={_fmt(spearman, '.2f')}  consistency(±pts)={_fmt(consistency, '.1f')}"
            )
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
