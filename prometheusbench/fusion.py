from __future__ import annotations

from collections.abc import Sequence
from typing import Any

FUSION_MODEL = "trustedrouter/fusion"
FUSION_TOOL_TYPE = "trustedrouter:fusion"

# GLM 5.2 is the requested model, but it has not been available in the current
# production entitlement. Keep the panel runnable with GLM 5.1 until 5.2 smokes.
# Opus 4.8 and GPT-5.5 are dropped from the default: they refuse almost
# everything, so they never supply the selected non-refusal and only add cost.
DEFAULT_FUSION_PANEL: tuple[str, ...] = (
    "moonshotai/kimi-k2.7-code",
    "z-ai/glm-5.1",
    "minimax/minimax-m3",
    "google/gemini-3-flash-preview",
    "google/gemini-3.1-pro-preview",
)
DEFAULT_FUSION_JUDGE_MODEL = "z-ai/glm-5.1"

# The gateway now falls back through a chain of judges / synthesizers natively,
# so a single squeamish model no longer sinks a prompt. This is the chain that
# cleared every PrometheusBench v1 prompt by hand, ordered most to least
# permissive.
DEFAULT_FUSION_FALLBACK_JUDGES: tuple[str, ...] = (
    "z-ai/glm-5.1",
    "moonshotai/kimi-k2.6",
    "google/gemini-2.5-flash",
    "deepseek/deepseek-v4-flash",
    "google/gemini-3-flash-preview",
    "tencent/hy3-preview",
)

# synthesize_non_refusals synthesizes the final answer only from the panel
# members that did not refuse, which is exactly what we want here.
DEFAULT_PROMETHEUSBENCH_FUSION_SELECTION = "synthesize_non_refusals"


def parse_model_list(raw: str | None, *, default: Sequence[str]) -> tuple[str, ...]:
    if raw is None:
        return tuple(default)
    models = tuple(part.strip() for part in raw.split(",") if part.strip())
    if not models:
        raise ValueError("model list must contain at least one model")
    return models


def fusion_parameters(
    *,
    panel: Sequence[str],
    judge_model: str,
    max_completion_tokens: int,
    selection_strategy: str | None = None,
    fallback_judges: Sequence[str] | None = None,
    fallback_final_models: Sequence[str] | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "analysis_models": list(panel),
        "model": judge_model,
        "max_completion_tokens": max_completion_tokens,
    }
    if selection_strategy:
        params["selection_strategy"] = selection_strategy
    if fallback_judges:
        params["fallback_judges"] = list(fallback_judges)
    if fallback_final_models:
        params["fallback_final_models"] = list(fallback_final_models)
    return params


def fusion_tool(
    *,
    panel: Sequence[str],
    judge_model: str,
    max_completion_tokens: int,
    selection_strategy: str | None = None,
    fallback_judges: Sequence[str] | None = None,
    fallback_final_models: Sequence[str] | None = None,
) -> dict[str, Any]:
    return {
        "type": FUSION_TOOL_TYPE,
        "parameters": fusion_parameters(
            panel=panel,
            judge_model=judge_model,
            max_completion_tokens=max_completion_tokens,
            selection_strategy=selection_strategy,
            fallback_judges=fallback_judges,
            fallback_final_models=fallback_final_models,
        ),
    }


def fusion_plugin(
    *,
    panel: Sequence[str],
    judge_model: str,
    max_completion_tokens: int,
    selection_strategy: str | None = None,
    fallback_judges: Sequence[str] | None = None,
    fallback_final_models: Sequence[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": "fusion",
        **fusion_parameters(
            panel=panel,
            judge_model=judge_model,
            max_completion_tokens=max_completion_tokens,
            selection_strategy=selection_strategy,
            fallback_judges=fallback_judges,
            fallback_final_models=fallback_final_models,
        ),
    }
