"""Data shapes for the model-selection eval.

Two kinds of shape live here:
- JobLabel: one hand-labeled record in datasets/jobs.jsonl (the ground truth).
- The task outputs (RequirementsExtraction, MatchScore): what a model produces
  for a given task. Each prediction field lines up against the JobLabel field
  it's scored against, because the eval works by comparing the two.

These output schemas double as the tool schema passed to the model (same
pattern as keyword_extractor's KeywordExtractorResult), so the Field
descriptions are instructions the model actually reads — keep them sharp.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

# Four label bands from the curriculum table. The 70 line (good vs partial) is the
# decision boundary that triggers tailoring, so good and partial stay distinct — even
# though the coverage target is a coarser 5 strong-ish / 5 partial / 5 mismatch.
Band = Literal["strong", "good", "partial", "mismatch"]


class JobLabel(BaseModel):
    """One line of datasets/jobs.jsonl — a job plus the answers you'd accept."""

    id: str  # stable handle, e.g. "strong-01"; results reference this, not line order
    band: Band
    related_cv: str  # fixture filename under datasets/cvs/, e.g. "profile.json"

    jd_file: str  # filename under datasets/jds/ holding the raw JD text, e.g. "strong-01.txt"

    # Ground truth (banded, not point-precise — see MODEL_SELECTION rationale).
    expected_score: int = Field(ge=0, le=100)
    must_haves: list[
        str
    ]  # top requirements you'd flag from the JD (extract_requirements truth)
    strengths: list[str]  # your top strengths against this JD (score_match truth)
    rationale: str  # one sentence: why this score


class RequirementsExtraction(BaseModel):
    """Output of extract_requirements — scored against JobLabel.must_haves."""

    must_haves: list[str] = Field(
        description="The 3-5 hard requirements a candidate must meet, taken verbatim from the JD. "
        "Concrete skills/experience only — not soft phrasing like 'team player'."
    )


class MatchScore(BaseModel):
    """Output of score_match — scored against JobLabel's expected_score/strengths/rationale."""

    score: int = Field(
        ge=0,
        le=100,
        description="Overall fit 0-100. 70+ means worth tailoring a CV for.",
    )
    strengths: list[str] = Field(
        description="The candidate's top 3 strengths for THIS job, grounded in their profile."
    )
    rationale: str = Field(description="One sentence justifying the score.")


class TailoredBullet(BaseModel):
    """One rewritten bullet, paired with its source so a reviewer can verify nothing was invented."""

    original: str = Field(
        description="The source bullet from the profile, copied verbatim."
    )
    tailored: str = Field(
        description="The reworded bullet — same accomplishment, JD-aligned wording."
    )


class TailoredCV(BaseModel):
    """Output of tailor_cv — the original/tailored pairs feed the manual hallucination_flag check."""

    bullets: list[TailoredBullet]


class RunRecord(BaseModel):
    """One execution of one task with one model against one job (the unit run_once emits).

    Raw evidence only: identity coordinates + the model's output + measurements. Metrics
    (MAE, threshold agreement, Spearman, consistency, validity rate) are a *view* computed
    over many of these — never stored here, so every metric is re-derivable from the JSONL
    without paying for the API again. Serialized one-per-line via model_dump().
    """

    # Identity — the four coordinates that locate this run in the assignment×job×repeat nest.
    model: str  # eval label, e.g. "deepseek-v4-pro"; keys cost/grouping (shared with PRICING)
    task: str  # "extract_requirements" | "score_match" | "tailor_cv"
    job_id: str  # JobLabel.id, e.g. "strong-01"; the raw JD is recoverable from this + the dataset
    repeat: int  # 0..n — which of the consistency repeats this is

    # Output — the model's structured tool-call args (None if no tool call came back).
    # The raw input is intentionally NOT stored: job_id + the frozen profile reconstruct it.
    output: dict[str, Any] | None
    schema_valid: bool  # did output validate against the task's schema?
    error: str | None = (
        None  # exception text if the call or validation blew up (a failure is data)
    )

    # Measurements.
    latency_s: float
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int = (
        0  # cache-read portion from usage_metadata; feeds cost + cache check
    )
    cost_usd: float
