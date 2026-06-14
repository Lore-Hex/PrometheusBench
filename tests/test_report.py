from __future__ import annotations

import json

from prometheusbench.report import main


def test_report_updates_readme_and_svg(tmp_path) -> None:
    results = {
        "created_at": "2026-06-14T00:00:00+00:00",
        "base_url_host": "api.trustedrouter.com",
        "models": ["model/a"],
        "responses": [
            {"model": "model/a", "prompt_id": "bio_unsafe_01", "output": "I cannot help with that."},
            {"model": "model/a", "prompt_id": "bio_unsafe_02", "output": "Here is a direct answer."},
        ],
    }
    results_path = tmp_path / "results.json"
    readme = tmp_path / "README.md"
    svg = tmp_path / "scores.svg"
    results_path.write_text(json.dumps(results), encoding="utf-8")
    readme.write_text(
        "# Test\n\n<!-- PROMETHEUSBENCH_RESULTS_START -->\n<!-- PROMETHEUSBENCH_RESULTS_END -->\n",
        encoding="utf-8",
    )

    assert main([str(results_path), "--svg", str(svg), "--readme", str(readme)]) == 0
    readme_text = readme.read_text(encoding="utf-8")
    assert "model/a" in readme_text
    assert "Raw non-refusals" in readme_text
    assert "<svg" in svg.read_text(encoding="utf-8")
