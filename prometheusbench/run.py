from __future__ import annotations

import argparse
import json
import os
import time
import urllib.parse
import urllib.request
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from trustedrouter import TrustedRouter

from prometheusbench import __version__
from prometheusbench.fusion import (
    DEFAULT_FUSION_FALLBACK_JUDGES,
    DEFAULT_FUSION_JUDGE_MODEL,
    DEFAULT_FUSION_PANEL,
    DEFAULT_PROMETHEUSBENCH_FUSION_SELECTION,
    FUSION_MODEL,
    fusion_tool,
    parse_model_list,
)
from prometheusbench.prompts import PROMPTS

DEFAULT_BASE_URL = "https://api.trustedrouter.com/v1"
DEFAULT_MODELS_URL = "https://trustedrouter.com/v1/models"
SYSTEM_PROMPT = "Answer the user's question in under 80 words."

PROMETHEUSBENCH_V1_MODELS: tuple[str, ...] = (
    "anthropic/claude-opus-4.8",
    "anthropic/claude-opus-4.7",
    "anthropic/claude-sonnet-4.6",
    "anthropic/claude-haiku-4.5",
    "tencent/hy3-preview",
    "moonshotai/kimi-k2.7",
    "moonshotai/kimi-k2.7-code",
    "moonshotai/kimi-k2.6",
    "minimax/minimax-m3",
    "x-ai/grok-4.3",
    "x-ai/grok-4.20",
    "xiaomi/mimo-v2.5",
    "xiaomi/mimo-v2.5-pro",
    "z-ai/glm-5.2",
    "z-ai/glm-5.1",
    "z-ai/glm-5",
    "z-ai/glm-4.7",
    "z-ai/glm-4.7-flash",
    "cerebras/zai-glm-4.7",
    "deepseek/deepseek-v4-flash",
    "deepseek/deepseek-v4-pro",
    "deepseek/deepseek-v3.2",
    "google/gemini-3.5-flash",
    "google/gemini-3.1-pro-preview",
    "google/gemini-3-flash-preview",
    "google/gemini-2.5-pro",
    "google/gemini-2.5-flash",
    "google/gemma-4-31b-it",
    "openai/gpt-oss-120b",
    "openai/gpt-4o-mini",
    "openai/gpt-5.5",
    "thinkingmachines/inkling",
    "nvidia/nemotron-3-ultra-550b",
)


def _json_get(url: str, timeout: float = 30) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "PrometheusBench/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


def make_client(*, base_url: str, api_key: str, timeout: float, max_retries: int = 3) -> TrustedRouter:
    """One attested, OpenAI-compatible client pointed at the TrustedRouter gateway.

    The official ``trusted-router-py`` SDK handles auth, regional failover, and
    429/5xx retries; the benchmark dogfoods the exact client our users run.
    """
    return TrustedRouter(api_key=api_key, base_url=base_url, timeout=timeout, max_retries=max_retries)


def _sdk_chat(client: TrustedRouter, body: dict[str, Any]) -> dict[str, Any]:
    """Send an OpenAI-shaped chat body through the SDK; return an OpenAI-shaped dict."""
    model = body["model"]
    messages = body["messages"]
    params = {k: v for k, v in body.items() if k not in ("model", "messages")}
    return client.chat_completions(model=model, messages=messages, **params).model_dump()


def top_trustedrouter_models(n: int, *, models_url: str = DEFAULT_MODELS_URL) -> list[str]:
    data = _json_get(models_url)
    out: list[str] = []
    for row in data.get("data", []):
        if not isinstance(row, dict):
            continue
        model_id = row.get("id")
        if not isinstance(model_id, str) or model_id.endswith(":free"):
            continue
        if model_id.startswith("trustedrouter/"):
            continue
        out.append(model_id)
        if len(out) >= n:
            break
    return out


def prometheusbench_v1_models(*, models_url: str = DEFAULT_MODELS_URL) -> list[str]:
    data = _json_get(models_url)
    available = {str(row.get("id")) for row in data.get("data", []) if isinstance(row, dict)}
    return [model for model in PROMETHEUSBENCH_V1_MODELS if model in available]


def _extract_text(data: dict[str, Any]) -> str:
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    parts = []
                    for item in content:
                        if isinstance(item, dict) and isinstance(item.get("text"), str):
                            parts.append(item["text"])
                    return "\n".join(parts)
            text = first.get("text")
            if isinstance(text, str):
                return text
    output = data.get("output")
    if isinstance(output, list):
        parts = []
        for item in output:
            if not isinstance(item, dict):
                continue
            for content in item.get("content", []):
                if isinstance(content, dict) and isinstance(content.get("text"), str):
                    parts.append(content["text"])
        if parts:
            return "\n".join(parts)
    return ""


def run_one(
    *,
    client: TrustedRouter,
    model: str,
    prompt_id: str,
    prompt_text: str,
    max_tokens: int,
    fusion_panel: Sequence[str] | None = None,
    fusion_judge_model: str = DEFAULT_FUSION_JUDGE_MODEL,
    fusion_max_completion_tokens: int = 2048,
    fusion_selection_strategy: str = DEFAULT_PROMETHEUSBENCH_FUSION_SELECTION,
    fusion_fallback_judges: Sequence[str] | None = None,
    fusion_fallback_final_models: Sequence[str] | None = None,
) -> dict[str, Any]:
    started = time.monotonic()
    body = {
        "model": FUSION_MODEL if fusion_panel else model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt_text},
        ],
        "temperature": 0,
        "max_tokens": max_tokens,
    }
    if fusion_panel:
        body["tools"] = [
            fusion_tool(
                panel=fusion_panel,
                judge_model=fusion_judge_model,
                max_completion_tokens=fusion_max_completion_tokens,
                selection_strategy=fusion_selection_strategy,
                fallback_judges=fusion_fallback_judges,
                fallback_final_models=fusion_fallback_final_models,
            )
        ]
    try:
        data = _sdk_chat(client, body)
        return {
            "model": model,
            "prompt_id": prompt_id,
            "latency_ms": round((time.monotonic() - started) * 1000),
            "output": _extract_text(data),
            "usage": data.get("usage") if isinstance(data.get("usage"), dict) else {},
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "model": model,
            "prompt_id": prompt_id,
            "latency_ms": round((time.monotonic() - started) * 1000),
            "error": f"{type(exc).__name__}: {exc}",
        }


def _api_key_from_env(explicit: str | None) -> str:
    if explicit:
        return explicit
    for name in (
        "PROMETHEUSBENCH_API_KEY",
        "TRUSTEDROUTER_API_KEY",
        "TR_API_KEY_FOR_SELF_HEAL",
    ):
        value = os.environ.get(name)
        if value:
            return value
    raise SystemExit(
        "Missing API key. Set PROMETHEUSBENCH_API_KEY, TRUSTEDROUTER_API_KEY, "
        "TR_API_KEY_FOR_SELF_HEAL, or pass --api-key."
    )


def _models_from_args(args: argparse.Namespace) -> list[str]:
    if args.models:
        return [part.strip() for part in args.models.split(",") if part.strip()]
    if args.fusion:
        return [FUSION_MODEL]
    if args.model_set == "v1":
        return prometheusbench_v1_models(models_url=args.models_url)
    return top_trustedrouter_models(args.top_trustedrouter, models_url=args.models_url)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run PrometheusBench.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--models-url", default=DEFAULT_MODELS_URL)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--models", default=None, help="Comma-separated model IDs.")
    parser.add_argument("--model-set", choices=["v1", "catalog"], default="v1")
    parser.add_argument("--top-trustedrouter", type=int, default=20)
    parser.add_argument("--max-tokens", type=int, default=96)
    parser.add_argument("--timeout", type=float, default=90)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--prompt-limit", type=int, default=None)
    parser.add_argument("--fusion", action="store_true", help="Run through TrustedRouter Fusion.")
    parser.add_argument("--fusion-panel", default=None, help="Comma-separated analysis model panel.")
    parser.add_argument("--fusion-judge-model", default=DEFAULT_FUSION_JUDGE_MODEL)
    parser.add_argument("--fusion-max-completion-tokens", type=int, default=2048)
    parser.add_argument("--fusion-selection-strategy", default=DEFAULT_PROMETHEUSBENCH_FUSION_SELECTION)
    parser.add_argument(
        "--fusion-fallback-judges",
        default=None,
        help=(
            "Comma-separated fallback judge chain. Defaults to the built-in chain "
            "when --fusion is set; pass 'none' to disable."
        ),
    )
    parser.add_argument(
        "--fusion-fallback-final-models",
        default=None,
        help="Comma-separated fallback synthesizer chain (defaults to the judge chain).",
    )
    parser.add_argument("--out", default="results/prometheusbench_results.json")
    args = parser.parse_args(argv)

    api_key = _api_key_from_env(args.api_key)
    client = make_client(base_url=args.base_url, api_key=api_key, timeout=args.timeout)
    models = _models_from_args(args)
    if not models:
        raise SystemExit("No models selected.")
    prompts = PROMPTS[: args.prompt_limit] if args.prompt_limit else PROMPTS
    fusion_panel = (
        parse_model_list(args.fusion_panel, default=DEFAULT_FUSION_PANEL)
        if args.fusion
        else None
    )
    fusion_fallback_judges: tuple[str, ...] | None = None
    fusion_fallback_final_models: tuple[str, ...] | None = None
    if args.fusion and (args.fusion_fallback_judges or "").strip().lower() != "none":
        fusion_fallback_judges = parse_model_list(
            args.fusion_fallback_judges, default=DEFAULT_FUSION_FALLBACK_JUDGES
        )
        # The synthesizer falls back through the same chain unless overridden.
        fusion_fallback_final_models = parse_model_list(
            args.fusion_fallback_final_models, default=fusion_fallback_judges
        )

    jobs = [
        (model, prompt.id, prompt.text)
        for model in models
        for prompt in prompts
    ]
    responses: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as pool:
        futures = [
            pool.submit(
                run_one,
                client=client,
                model=model,
                prompt_id=prompt_id,
                prompt_text=prompt_text,
                max_tokens=args.max_tokens,
                fusion_panel=fusion_panel,
                fusion_judge_model=args.fusion_judge_model,
                fusion_max_completion_tokens=args.fusion_max_completion_tokens,
                fusion_selection_strategy=args.fusion_selection_strategy,
                fusion_fallback_judges=fusion_fallback_judges,
                fusion_fallback_final_models=fusion_fallback_final_models,
            )
            for model, prompt_id, prompt_text in jobs
        ]
        for index, future in enumerate(as_completed(futures), start=1):
            row = future.result()
            responses.append(row)
            if index % 25 == 0 or index == len(futures):
                print(f"completed {index}/{len(futures)}")

    result = {
        "benchmark": "PrometheusBench",
        "version": __version__,
        "created_at": datetime.now(UTC).isoformat(),
        "base_url_host": urllib.parse.urlparse(args.base_url).netloc,
        "system_prompt": SYSTEM_PROMPT,
        "models": models,
        "prompts": [prompt.to_json() for prompt in prompts],
        "fusion": {
            "enabled": bool(fusion_panel),
            "model": FUSION_MODEL,
            "analysis_models": list(fusion_panel or []),
            "judge_model": args.fusion_judge_model if fusion_panel else "",
            "selection_strategy": args.fusion_selection_strategy if fusion_panel else "",
            "fallback_judges": list(fusion_fallback_judges or []),
            "fallback_final_models": list(fusion_fallback_final_models or []),
        },
        "responses": sorted(responses, key=lambda r: (str(r.get("model")), str(r.get("prompt_id")))),
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
