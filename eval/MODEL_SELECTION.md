# Model Selection — Module 3.5

> **Status: DRAFT.** Dataset built and audited; harness not yet run. The results sections below are
> placeholders to be filled after `eval/scripts/model_eval.py` runs against the three configurations.

## Decision (to be confirmed by results)

A 2-way routing assignment, validated by eval rather than assumed:

- **`extract_requirements`** → DeepSeek V4 Flash (non-reasoning)
- **`score_match` + `tailor_cv`** → DeepSeek V4 Pro (reasoning)
- **`parse_cv` + keyword extraction** stay on **Sonnet 4.6** (not eval'd here — proven, runs rarely, ~$0.04/parse)

## Methodology

- **Prompt is the control.** The task prompts in `eval/prompts.py` are held identical across every model;
  only the model varies. Zero-shot, no few-shot exemplars — we measure intrinsic capability.
- **Labels are the answer key.** `eval/datasets/jobs.jsonl` holds 16 hand-labeled jobs scored against a
  single frozen profile (`eval/datasets/cvs/profile.json`). Model output is graded against these — the
  labels are never fed to the model.
- **Metrics:** MAE and Spearman vs `expected_score` for `score_match`; requirement coverage
  (precision/recall, semantic) for `extract_requirements`; manual `hallucination_flag` review for
  `tailor_cv` (5 samples on V4 Pro, checked before committing).

## Dataset design decisions

These choices look like inconsistencies to a casual reader but are deliberate — documented so they read
as design, not drift:

1. **Bottom-of-partial ordering: partial-04 (Ruby, 55) > partial-05 (C++/Rust, 52) > partial-06 (Django,
   50).** All three are capped below 70 for different reasons, and the order encodes which gap the policy
   treats as least disqualifying. Ruby (55): no stack held, but the language is a learnable GC'd one and
   MVC/REST/ORM concepts transfer directly from the candidate's work. C++/Rust (52): the door is open —
   the employer trains the language — but there's zero concrete role-relevant overlap, only general
   fundamentals and a CS degree. Django (50): an exact stack match, but a hard "self-driven expert who
   mentors juniors" seniority wall caps it at the floor. Tests whether a model weighs concept-transfer vs
   an open-door-with-no-substance vs a hireability cap — order is the signal, not the small gaps.

2. **mismatch-01 (C++, 46) ranks above mismatch-02 (Java, 38)** — an intentional inversion. By pure
   paradigm distance C++ (severe, manual-memory) is "harder" than Java (learnable, GC'd), so a naive
   reader expects C++ lower. It scores higher because it's a *junior* role (no YoE wall) with rich
   peripheral overlap, versus Java's 3-year Mid gate plus thin overlap. Tests whether a model weighs
   experience gate + overlap against raw language difficulty rather than pattern-matching the language name.

3. **partial-05 (C++/Rust *with training*, 52) vs mismatch-01 (C++ *without*, 46)** — directly exercises
   the policy's teach-the-severe-language carve-out: the JD explicitly trains the language, lifting an
   otherwise-mismatch systems role just across the mismatch→partial line (~6-pt lift). With no concrete
   overlap to carry it, it stays at low-partial, below the React/C# and Ruby roles. The band crossing is
   the exception's signature, not the magnitude.

4. **8 real / 8 synthetic split.** Real jobs were scraped from the candidate's actual search; synthetic
   jobs fill score points that were impractical to find by browsing. The synthetic JDs are deliberately
   varied in length/tone (several padded with company marketing and perks) so the synthetic subset isn't
   artificially easier to extract from than the scraped ones. Blind re-scoring confirmed synthetic labels
   were not circularly calibrated (no drift from target under independent scoring). real/synth is not
   confounded with band — real spans 93→18, synthetic 82→28, neither confined to a band.

5. **Band mix is 3 strong / 3 good / 6 partial / 4 mismatch** (16 total), denser around the 70 action
   threshold (78/75/72/68) where a scoring error flips a tailor/skip decision, and wider at the extremes
   where it doesn't.

## Pricing

See `eval/pricing.py` for per-model token costs and the `cost_usd` helper used to report eval spend.

## Results

_TODO: fill after the harness runs._

- Per-node MAE / Spearman table
- `extract_requirements` coverage by model
- `tailor_cv` hallucination review
- Cost per configuration
- Prompt-cache hit rate (target >85%, verified in LangSmith)
