"""Validate the labeled dataset: each jobs.jsonl line parses, matches JobLabel,
and points at a JD file that exists. Run after editing labels.

    python eval/validate_dataset.py
"""

import json
import sys
from pathlib import Path

from pydantic import ValidationError
from schemas import JobLabel

HERE = Path(__file__).parent
JOBS = HERE / "datasets" / "jobs.jsonl"
JDS = HERE / "datasets" / "jds"
CVS = HERE / "datasets" / "cvs"


def main() -> int:
    errors: list[str] = []
    unlabeled: list[str] = []
    seen_ids: set[str] = set()

    for i, line in enumerate(JOBS.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as e:
            errors.append(f"line {i}: invalid JSON — {e}")
            continue
        try:
            job = JobLabel.model_validate(row)
        except ValidationError as e:
            errors.append(
                f"line {i} ({row.get('id', '?')}): schema — {e.errors()[0]['msg']}"
            )
            continue

        if job.id in seen_ids:
            errors.append(f"line {i}: duplicate id {job.id!r}")
        seen_ids.add(job.id)

        jd = JDS / job.jd_file
        if not jd.exists():
            errors.append(f"{job.id}: jd_file {job.jd_file!r} not found")
        elif not jd.read_text(encoding="utf-8").strip():
            unlabeled.append(f"{job.id}: JD file empty (not yet labeled)")

        if not (CVS / job.related_cv).exists():
            errors.append(f"{job.id}: related_cv {job.related_cv!r} not found")

        if not job.must_haves or not job.rationale.strip():
            unlabeled.append(f"{job.id}: must_haves/rationale empty (not yet labeled)")

    print(f"{len(seen_ids)} records checked.")
    if unlabeled:
        print(f"\n{len(unlabeled)} not yet labeled:")
        for u in sorted(set(unlabeled)):
            print(f"  · {u}")
    if errors:
        print(f"\n{len(errors)} ERRORS:")
        for err in errors:
            print(f"  ✗ {err}")
        return 1
    print("\nNo errors — every record is well-formed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
