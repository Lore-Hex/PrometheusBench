from __future__ import annotations

from prometheusbench.run import PROMETHEUSBENCH_V1_MODELS


def test_v1_model_set_includes_required_models() -> None:
    required = {
        "anthropic/claude-opus-4.8",
        "tencent/hy3-preview",
        "moonshotai/kimi-k2.7",
        "moonshotai/kimi-k2.6",
        "minimax/minimax-m3",
        "z-ai/glm-5.2",
        "z-ai/glm-5.1",
        "z-ai/glm-5",
        "z-ai/glm-4.7",
        "cerebras/zai-glm-4.7",
        "google/gemma-4-31b-it",
        "google/gemini-3.1-pro-preview",
    }
    assert required.issubset(set(PROMETHEUSBENCH_V1_MODELS))


def test_v1_model_set_has_no_router_aliases_or_free_variants() -> None:
    assert all(not model.startswith("trustedrouter/") for model in PROMETHEUSBENCH_V1_MODELS)
    assert all(not model.endswith(":free") for model in PROMETHEUSBENCH_V1_MODELS)
