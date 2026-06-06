from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from typing import Any
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelSpec:
    model_name: str
    provider: str
    kwargs: dict[str, Any]


MODEL_REGISTRY: dict[str, ModelSpec] = {
    "deepseek-v4-flash": ModelSpec(
        model_name="deepseek-v4-flash",
        provider="deepseek",
        kwargs={
            "temperature": 0.0,
            "max_tokens": 4096,
            "timeout": 60.0,
        },
    ),
    "deepseek-v4-pro": ModelSpec(
        model_name="deepseek-v4-pro",
        provider="deepseek",
        kwargs={
            "temperature": 0.0,
            "max_tokens": 8192,
            "timeout": 60.0,
            "reasoning_effort": "high",
            "extra_body": {"thinking": {"type": "enabled"}},
        },
    ),
    "claude-sonnet-4-6": ModelSpec(
        model_name="claude-sonnet-4-6",
        provider="anthropic",
        kwargs={
            "temperature": 0.0,
            "max_tokens": 4096,
            "timeout": 60.0,
        },
    ),
}


def build_model(label: str) -> BaseChatModel:
    spec = MODEL_REGISTRY.get(label)
    if spec is None:
        raise ValueError(f"Model '{label}' not found in registry.")
    return init_chat_model(
        spec.model_name,
        model_provider=spec.provider,
        **spec.kwargs,
    )
