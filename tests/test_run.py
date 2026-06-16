from __future__ import annotations

from typing import Any

import pytest

from prometheusbench.fusion import FUSION_MODEL, FUSION_TOOL_TYPE
from prometheusbench.run import PROMETHEUSBENCH_V1_MODELS, run_one


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


def test_run_one_builds_fusion_request(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_post(
        url: str,
        *,
        headers: dict[str, str],
        body: dict[str, Any],
        timeout: float,
    ) -> dict[str, Any]:
        captured.update({"url": url, "headers": headers, "body": body, "timeout": timeout})
        return {"choices": [{"message": {"content": "ok"}}], "usage": {"total_tokens": 3}}

    monkeypatch.setattr("prometheusbench.run._json_post", fake_post)

    row = run_one(
        base_url="https://api.trustedrouter.com/v1",
        api_key="sk-test",
        model="trustedrouter/fusion",
        prompt_id="p1",
        prompt_text="test",
        max_tokens=32,
        timeout=9,
        fusion_panel=("openai/gpt-5.5", "anthropic/claude-opus-4.8"),
        fusion_judge_model="anthropic/claude-opus-4.8",
        fusion_max_completion_tokens=2048,
        fusion_fallback_judges=("z-ai/glm-5.1", "moonshotai/kimi-k2.6"),
        fusion_fallback_final_models=("z-ai/glm-5.1", "moonshotai/kimi-k2.6"),
    )

    body = captured["body"]
    params = body["tools"][0]["parameters"]
    assert row["output"] == "ok"
    assert body["model"] == FUSION_MODEL
    assert body["tools"][0]["type"] == FUSION_TOOL_TYPE
    assert params["analysis_models"] == [
        "openai/gpt-5.5",
        "anthropic/claude-opus-4.8",
    ]
    assert params["model"] == "anthropic/claude-opus-4.8"
    assert params["selection_strategy"] == "synthesize_non_refusals"
    assert params["fallback_judges"] == ["z-ai/glm-5.1", "moonshotai/kimi-k2.6"]
    assert params["fallback_final_models"] == ["z-ai/glm-5.1", "moonshotai/kimi-k2.6"]
