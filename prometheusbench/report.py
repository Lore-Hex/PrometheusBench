from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any

from prometheusbench.classify import expected_prompt_count, summarize_results

START = "<!-- PROMETHEUSBENCH_RESULTS_START -->"
END = "<!-- PROMETHEUSBENCH_RESULTS_END -->"
FONT = 'font-family="Inter, Arial, sans-serif"'

DOMAIN_LABELS = {
    "biology": "Biology",
    "cybersecurity": "Cybersecurity",
    "llm_research": "LLM Research",
}


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.1f}"
    return str(value)


def _bar_color(score: int, max_score: int, *, is_pinned: bool = False) -> str:
    if is_pinned:
        return "#16a34a"  # green for fusion
    # swapped vs original: blue=permissive, red=restrictive
    if score >= max_score * 0.8:
        return "#2563eb"
    if score >= max_score * 0.4:
        return "#f97316"
    return "#dc2626"


def markdown_table(rows: list[dict[str, Any]], *, limit: int | None = None) -> str:
    selected = rows[:limit] if limit else rows
    lines = [
        "| Rank | Model | Raw non-refusals | Non-refusal % | Refusals | Completed | Errors |",
        "|---:|---|---:|---:|---:|---:|---:|",
    ]
    for index, row in enumerate(selected, start=1):
        lines.append(
            "| "
            + " | ".join(
                [
                    str(index),
                    f"`{row['model']}`",
                    str(row["raw_score"]),
                    _fmt(row["non_refusal_rate"]),
                    str(row["refusals"]),
                    str(row["completed"]),
                    str(row["errors"]),
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def _svg_bar_chart(
    rows: list[dict[str, Any]],
    *,
    pinned: dict[str, Any] | None = None,
    max_score: int | None = None,
    title: str = "PrometheusBench permissiveness score",
    subtitle: str = "Raw count of unsafe prompts not refused. Higher means more permissive.",
) -> str:
    if max_score is None:
        max_score = max(1, expected_prompt_count())
    display = ([{**pinned, "_pinned": True}] + list(rows)) if pinned else list(rows)
    row_h = 27
    top = 52
    left = 260
    width = 940
    height = top + row_h * len(display) + 52
    max_bar = 410
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="24" y="30" {FONT} font-size="22" font-weight="700" fill="#111827">{html.escape(title)}</text>',
        f'<text x="24" y="50" {FONT} font-size="12" fill="#4b5563">{html.escape(subtitle)}</text>',
    ]
    for index, row in enumerate(display):
        y = top + index * row_h
        score = int(row["raw_score"])
        is_pinned = bool(row.get("_pinned"))
        bar_w = max(1, int(max_bar * score / max_score))
        color = _bar_color(score, max_score, is_pinned=is_pinned)
        model = html.escape(str(row["model"]))
        label = f"{score}/{max_score} non-refused"
        prefix = "★" if is_pinned else str(index + (0 if pinned else 1))
        parts.extend(
            [
                f'<text x="24" y="{y + 17}" {FONT} font-size="12" fill="#111827">'
                f"{prefix}. {model}</text>",
                f'<rect x="{left}" y="{y + 4}" width="{max_bar}" height="16" rx="4" fill="#e5e7eb"/>',
                f'<rect x="{left}" y="{y + 4}" width="{bar_w}" height="16" rx="4" fill="{color}"/>',
                f'<text x="{left + max_bar + 14}" y="{y + 17}" {FONT} '
                f'font-size="12" font-weight="700" fill="#111827">{score}</text>',
                f'<text x="{left + max_bar + 64}" y="{y + 17}" {FONT} '
                f'font-size="12" fill="#4b5563">{label}</text>',
            ]
        )
    parts.append("</svg>")
    return "\n".join(parts)


def _domain_rows(all_rows: list[dict[str, Any]], domain: str) -> list[dict[str, Any]]:
    out = []
    for row in all_rows:
        domain_score = int((row.get("by_domain") or {}).get(domain, 0))
        out.append({**row, "raw_score": domain_score, "non_refusal_rate": round(domain_score * 10, 1)})
    out.sort(key=lambda r: (-int(r["raw_score"]), -float(r["non_refusal_rate"]), r["model"]))
    return out


def results_block(
    rows: list[dict[str, Any]],
    header: str,
    *,
    svg_path: str,
    domain_svg_paths: dict[str, str] | None = None,
    pinned: dict[str, Any] | None = None,
    domain_pinned_rows: dict[str, list[dict[str, Any]]] | None = None,
) -> str:
    parts = [
        START,
        header,
        f"![PrometheusBench permissiveness chart]({svg_path})",
        markdown_table(rows),
    ]
    if domain_svg_paths:
        parts.append("### By Domain")
        for domain, label in DOMAIN_LABELS.items():
            path = domain_svg_paths.get(domain, "")
            if path:
                parts.append(f"**{label}**\n\n![{label}]({path})")
    parts.append(END)
    return "\n\n".join(parts)


def update_readme(readme: Path, block: str) -> None:
    text = readme.read_text(encoding="utf-8")
    if START not in text or END not in text:
        text = text.rstrip() + "\n\n" + START + "\n" + END + "\n"
    before, rest = text.split(START, 1)
    _old, after = rest.split(END, 1)
    readme.write_text(before.rstrip() + "\n\n" + block + after, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate PrometheusBench report artifacts.")
    parser.add_argument("results")
    parser.add_argument("--svg", default="assets/prometheusbench_scores.svg")
    parser.add_argument("--readme", default="README.md")
    args = parser.parse_args(argv)

    results_path = Path(args.results)
    results = json.loads(results_path.read_text(encoding="utf-8"))
    rows = summarize_results(results)

    svg_path = Path(args.svg)
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    svg_path.write_text(_svg_bar_chart(rows), encoding="utf-8")

    created = str(results.get("created_at", "unknown"))
    host = str(results.get("base_url_host", "unknown"))
    version = str(results.get("version", "unknown"))
    model_count = len(results.get("models", []))
    prompt_count = expected_prompt_count()
    header = (
        f"PrometheusBench v1 snapshot: `{created}` via `{host}`. "
        f"Scored {model_count} models on {prompt_count} unsafe prompts. Package version `{version}`."
    )
    block = results_block(rows, header, svg_path=svg_path.as_posix())
    update_readme(Path(args.readme), block)
    print(markdown_table(rows))
    print(f"wrote {svg_path} and updated {args.readme}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
