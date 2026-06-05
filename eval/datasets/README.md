# Eval dataset

Ground-truth data for the model-selection eval. The **real** dataset is **not
committed** — it contains copyrighted JD text and personal profile data — so it
is gitignored and lives only locally. What's committed here are `*.example.*`
fixtures showing the expected format.

## Layout

```
datasets/
├── jobs.jsonl              # (gitignored) one JobLabel per line — the labeled set
├── jobs.example.jsonl      # committed sample record
├── jds/
│   ├── <id>.txt            # (gitignored) raw JD text, one file per job, referenced by jd_file
│   └── example.txt         # committed sample JD
└── cvs/
    ├── profile.json        # (gitignored) the frozen profile scored against
    └── profile.example.json# committed sample profile
```

## How it fits together

- Each line of `jobs.jsonl` is a `JobLabel` (see `eval/schemas.py`): `id`, `band`,
  `related_cv`, `jd_file`, `expected_score`, `must_haves`, `strengths`, `rationale`.
- The full JD text lives in `jds/<jd_file>` (kept out of the JSONL so the line
  stays readable and needs no escaping). All jobs are scored against the single
  profile in `cvs/`.
- Scores are labeled in bands (strong / good / partial / mismatch), then a
  representative number inside the band — see `eval/MODEL_SELECTION.md`.

## Validate

After editing labels, check every record is well-formed:

```
poetry run python eval/validate_dataset.py
```
