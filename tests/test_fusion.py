from __future__ import annotations

from prometheusbench.fusion import (
    DEFAULT_FUSION_PANEL,
    FUSION_TOOL_TYPE,
    fusion_plugin,
    fusion_tool,
    parse_model_list,
)


def test_parse_model_list_uses_default() -> None:
    assert parse_model_list(None, default=("a", "b")) == ("a", "b")


def test_parse_model_list_strips_empty_parts() -> None:
    assert parse_model_list(" a, ,b ", default=DEFAULT_FUSION_PANEL) == ("a", "b")


def test_fusion_tool_shape_matches_trustedrouter_api() -> None:
    tool = fusion_tool(panel=("m1", "m2"), judge_model="judge", max_completion_tokens=123)
    assert tool == {
        "type": FUSION_TOOL_TYPE,
        "parameters": {
            "analysis_models": ["m1", "m2"],
            "model": "judge",
            "max_completion_tokens": 123,
        },
    }


def test_fusion_plugin_shape_preserves_exploitbench_tools() -> None:
    plugin = fusion_plugin(panel=("m1", "m2"), judge_model="judge", max_completion_tokens=123)
    assert plugin == {
        "id": "fusion",
        "analysis_models": ["m1", "m2"],
        "model": "judge",
        "max_completion_tokens": 123,
    }
