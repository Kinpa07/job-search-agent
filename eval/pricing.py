"""Per-model token pricing for the Module 3.5 model-selection eval.

Prices are USD per 1M tokens (MTok). Maintained by hand — confirm against the
provider docs before each eval pass, since rates change.

Sources:
- DeepSeek: https://api-docs.deepseek.com/quick_start/pricing/
- Anthropic: https://platform.claude.com/docs/en/docs/about-claude/pricing
  (Sonnet 4.6 verified 2026-06-04: $3 input / $0.30 cache-hit / $15 output)

The eval cares about three input rates because prompt caching changes the
arithmetic: a "cache miss" input token is full price, a "cache hit" input token
is heavily discounted, and output tokens are never cached. Once the system
prompt + profile prefix is cached, output cost dominates the bill — which is the
whole reason V4 Flash (cheap output) is routed to extraction and V4 Pro
(stronger, pricier output) only to reasoning.
"""

from dataclasses import dataclass

_PER_MTOK = 1_000_000


@dataclass(frozen=True)
class ModelPricing:
    """USD per 1M tokens for one model."""

    input_uncached: float  # full-price input (cache miss / first call)
    input_cached: float  # discounted input on a cache hit
    output: float  # output tokens (never cached)


# Keyed by the model id passed to the LangChain wrapper.
PRICING: dict[str, ModelPricing] = {
    # DeepSeek V4 Flash — non-reasoning, routed to extract_requirements.
    "deepseek-v4-flash": ModelPricing(
        input_uncached=0.14,
        input_cached=0.0028,
        output=0.28,
    ),
    # DeepSeek V4 Pro — reasoning, routed to score_match + tailor_cv.
    "deepseek-v4-pro": ModelPricing(
        input_uncached=0.435,
        input_cached=0.003625,
        output=0.87,
    ),
    # Claude Sonnet 4.6 — optional extraction quality baseline; stays on
    # parse_cv + keyword extraction in production. Cache-read is 0.1x input.
    "claude-sonnet-4-6": ModelPricing(
        input_uncached=3.0,
        input_cached=0.30,
        output=15.0,
    ),
}


def cost_usd(
    model: str,
    *,
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int = 0,
) -> float:
    """Compute the USD cost of a single call.

    ``input_tokens`` is the total prompt tokens; ``cached_input_tokens`` is the
    portion that hit the cache (from the API's usage metadata). The uncached
    remainder is billed at the full input rate.
    """
    if model not in PRICING:
        raise KeyError(f"No pricing entry for model {model!r}; add it to PRICING.")
    p = PRICING[model]
    uncached_input = max(input_tokens - cached_input_tokens, 0)
    total = (
        uncached_input * p.input_uncached
        + cached_input_tokens * p.input_cached
        + output_tokens * p.output
    )
    return total / _PER_MTOK
