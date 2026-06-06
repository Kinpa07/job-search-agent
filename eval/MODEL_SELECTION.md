# Model Selection — Module 3.5

> **Status: FINAL.** Harness run against the combined results in `eval/results/` (240 runs across the
> dataset, 3 repeats each). Numbers below are from the `metrics.py` view over that run.

## Decision

Not a clean 2-way split — the eval changed the plan. Final routing:

- **`extract_requirements`** → **DeepSeek V4 Flash, thinking OFF** (`flash-nothink`)
- **`score_match`** → **DeepSeek V4 Pro, thinking ON** (`pro-think`)
- **`tailor_cv`** → **deferred — not locked here.** The eval showed the task as currently scoped (plain
  bullet-rewording) is a null task that no model can do usefully (see below). The tailoring model is
  re-evaluated in Module 4 once the task is redesigned (relevance-driven selection + STAR rewording).
- **`parse_cv` + keyword extraction** stay on **Sonnet 4.6** (not eval'd here — proven, runs rarely, ~$0.04/parse)

So the production graph injects an `extraction_model` and a `scoring_model`; the `tailoring_model` slot
is left open until Module 4 settles the task.

## What a "config" is here — (tier × thinking)

The first design of this eval treated reasoning as a *model property* (a separate reasoning model id).
That's wrong for DeepSeek V4: **thinking is an orthogonal parameter toggle, and it defaults ON for both
tiers.** A configuration is therefore (tier × thinking), not a single model name:

| label | tier | thinking | priced as |
|---|---|---|---|
| `flash-nothink` | V4 Flash | off | flash |
| `flash-think` | V4 Flash | on | flash |
| `pro-think` | V4 Pro | on | pro |
| `pro-nothink` | V4 Pro | off | pro (kept in registry, not run) |

Thinking is set **explicitly** in every config (`extra_body={"thinking": {"type": ...}}`), never left to
the server default. This matters: an early run silently executed `extract_requirements` *with* reasoning
(909 output tokens / 6.09s where 153 / 1.22s was expected) because the flash config carried no thinking
flag and the server default is ON. Confirmed in LangSmith traces, then fixed by making the toggle explicit.
Pricing keys on the **tier** (flash vs pro), so the cost helper uses `ModelSpec.model_name`, not the label.

## Methodology

- **Prompt is the control.** The task prompts in `eval/prompts.py` are held identical across every config;
  only the model varies. Zero-shot, no few-shot exemplars — we measure intrinsic capability.
- **Labels are the answer key.** `eval/datasets/jobs.jsonl` holds 16 hand-labeled jobs scored against a
  single frozen profile (`eval/datasets/cvs/profile.json`). Model output is graded against these — the
  labels are never fed to the model.
- **Tool-calling as structured output.** Each task binds its Pydantic output schema as the single tool and
  reads back the tool-call args — not agentic tool use. `tool_choice="auto"`, **not** a forced choice:
  DeepSeek thinking mode rejects forced `tool_choice` (both `"required"` and a named tool 400). With one
  tool bound and a directive prompt the model still calls it; a decline is recorded as a no-tool-call
  failure (output `None`) and surfaces in the validity rate rather than crashing.
- **Repeats collapse to a median.** Each (config × job) runs 3×. For `score_match` the repeats collapse to
  their median before MAE/threshold/Spearman (invalid runs dropped first); consistency is read separately as
  the mean per-job spread of those repeats.
- **Caching is real and persistent.** DeepSeek's prompt cache is server-side and survives across processes
  for hours, so the profile-heavy prompts hit cache on repeats and across configs (cache-read mapped by
  `langchain_openai` from `prompt_tokens_details.cached_tokens`). Verified >85% hit rate in LangSmith.
- **Metrics:** MAE, threshold agreement (the ≥70 action boundary), Spearman, and consistency vs
  `expected_score` for `score_match`; schema-validity, median cost, and P50 latency for every task.
  Two checks stay manual: `extract_requirements` coverage (semantic, not string-equality) and `tailor_cv`
  hallucination — eyeballed on samples, see the tailoring section.

## Results

From `metrics.py` over the combined run (3 repeats per cell; `tailor_cv` is the ≥60 subset only — see
limitations). Cost is median USD per call; latency is P50.

| task | config | valid | cost/call | P50 | accuracy |
|---|---|---|---|---|---|
| `extract_requirements` | **flash-nothink** | 100% | **$0.00004** | **1.22s** | — |
| `extract_requirements` | flash-think | 100% | $0.00021 | 6.09s | — |
| `score_match` | **pro-think** | 100% | $0.00164 | 36.32s | MAE 7.9 · thr 94% · ρ 0.87 · ±3.1 |
| `tailor_cv` | flash-nothink | 100% | $0.00035 | 8.72s | no fabrication (manual) |
| `tailor_cv` | flash-think | 100% | $0.00068 | 15.69s | no fabrication (manual) |
| `tailor_cv` | pro-think | 100% | $0.00353 | 49.90s | no fabrication (manual) |

**Extraction → `flash-nothink`.** flash-nothink and flash-think are *both* 100% valid, but turning thinking
on makes extraction **5× more expensive and 5× slower** for no quality gain. Extraction is pattern-pulling
from the JD, not reasoning — the eval confirms reasoning is dead weight here. Locked.

**Scoring → `pro-think`.** MAE 7.9 (under the 10-point bar), 94% agreement on the ≥70 tailor/skip decision,
0.87 Spearman, and ±3.1 consistency across repeats. Reasoning earns its cost on the judgement task. Locked.

**Tailoring → deferred (null result).** All three configs are 100% schema-valid and, on manual review,
**none fabricate** — the no-invention constraint in the prompt holds across tiers. But validity isn't the
point: the edits are *uselessly* trivial (generic rephrasing) and the model rewrites bullets irrelevant to
the JD (e.g. customer-support bullets on a Python role). The eval can't differentiate models on a task with
no real content to do, which is itself the finding: **the task needs redesign, not a model.** Picking the
cheapest config here would be locking a model to something not worth shipping. Deferred to Module 4, which
adds JD-relevance-driven selection and STAR-structured rewording; Module 5's prompt loop then tunes quality.
At that point the tailoring model is re-evaluated against the *real* task (selection/judgement is reasoning
work, so `pro-think` or `flash-think` are the likely candidates — not assumed).

## Known limitations / to revisit

- **`tailor_cv` was evaluated on the wrong (trivial) task.** Schema-validity and no-fabrication were
  confirmed, but the task itself is being redesigned (see Decision/Results) — so these numbers establish the
  *constraint holds*, not that the feature is good. Re-eval in Module 4 against relevance-selection + STAR
  rewording, on a master-profile superset with a 1-page fit.

- **`score_match` is graded on the overall score only.** Module 4's production scorer adds a per-skill
  breakdown (`skill_scores`) — a structurally richer output than the single 0-100 tested here — so this
  selection is made on a proxy task. The scoring model is locked to V4 Pro (thinking on) regardless, and
  per-skill scoring is *more* demanding, which only reinforces keeping reasoning on; so this is unlikely
  to change the routing. Flagged for peace of mind: **potentially add per-skill scoring (plus its
  ground-truth labels) to the eval and re-run** — most cleanly in Module 5 — to confirm the locked model
  handles the richer contract correctly, not to re-decide it. `extract_requirements` likewise omits
  nice-to-haves and seniority, but those are the same extraction task class (more fields, no difficulty
  jump), so they don't affect that selection.

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
Total spend for the full run was well under the $5 budget — DeepSeek pricing plus the persistent prompt
cache keeps a 240-run sweep in the low cents.

- Per-node MAE / Spearman table
- `extract_requirements` coverage by model
- `tailor_cv` hallucination review
- Cost per configuration
- Prompt-cache hit rate (target >85%, verified in LangSmith)
