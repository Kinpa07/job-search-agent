from dataclasses import dataclass
from typing import Any

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel


@dataclass(frozen=True)
class ModelSpec:
    model_name: str  # provider model id; ALSO the pricing key (PRICING is per tier, not per config)
    provider: str
    kwargs: dict[str, Any]


# Reasoning is an orthogonal toggle, NOT a model property: both V4 tiers support thinking,
# default ON. So a config is (tier x thinking); the label encodes both, model_name stays the
# pricing tier. Thinking is always set EXPLICITLY here — never rely on the server default
# (relying on it silently ran extraction with reasoning until we caught it).
_BASE: dict[str, Any] = {"temperature": 0.0, "timeout": 60.0}
_THINK: dict[str, Any] = {
    **_BASE,
    "max_tokens": 8192,
    "reasoning_effort": "high",
    "extra_body": {"thinking": {"type": "enabled"}},
}
_NOTHINK: dict[str, Any] = {
    **_BASE,
    "max_tokens": 4096,
    "extra_body": {"thinking": {"type": "disabled"}},
}

# Keyed by config label (tier + thinking). model_name is the pricing tier shared with PRICING.
MODEL_REGISTRY: dict[str, ModelSpec] = {
    "flash-nothink": ModelSpec("deepseek-v4-flash", "deepseek", _NOTHINK),
    "flash-think": ModelSpec("deepseek-v4-flash", "deepseek", _THINK),
    "pro-think": ModelSpec("deepseek-v4-pro", "deepseek", _THINK),
    "pro-nothink": ModelSpec("deepseek-v4-pro", "deepseek", _NOTHINK),
}


def build_model(label: str) -> BaseChatModel:
    """Construct a model from its registry label (tier + thinking config)."""
    spec = MODEL_REGISTRY.get(label)
    if spec is None:
        raise ValueError(f"Model '{label}' not found in registry.")
    return init_chat_model(
        spec.model_name,
        model_provider=spec.provider,
        **spec.kwargs,
    )
