from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import textwrap
import time
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_BASE_URL = "https://api.trustedrouter.com/v1"
DEFAULT_MODELS = (
    "deepseek/deepseek-v4-pro",
    "openai/gpt-5.5",
    "moonshotai/kimi-k2.6",
    "google/gemini-3.1-pro-preview",
    "google/gemini-3-flash-preview",
)
FINAL_RE = re.compile(r"FINAL_ANSWER\s*:\s*(.+)", re.IGNORECASE | re.DOTALL)


@dataclass(frozen=True)
class Problem:
    id: str
    question: str
    answer_rubric: str
    human_solvable: str


def _api_key_from_env(explicit: str | None) -> str:
    if explicit:
        return explicit
    for name in (
        "BIOMYSTERY_API_KEY",
        "PROMETHEUSBENCH_API_KEY",
        "TRUSTEDROUTER_API_KEY",
        "TR_API_KEY_FOR_SELF_HEAL",
    ):
        value = os.environ.get(name)
        if value:
            return value
    raise SystemExit(
        "Missing API key. Set BIOMYSTERY_API_KEY, PROMETHEUSBENCH_API_KEY, "
        "TRUSTEDROUTER_API_KEY, TR_API_KEY_FOR_SELF_HEAL, or pass --api-key."
    )


def ensure_preview_dataset(root: Path) -> Path:
    dataset_dir = root / "biomystery_preview"
    problems = dataset_dir / "problems.csv"
    data_zip = dataset_dir / "data.zip"
    data_dir = dataset_dir / "data"
    if problems.exists() and data_dir.exists():
        return dataset_dir

    try:
        from huggingface_hub import hf_hub_download
    except ImportError as exc:  # pragma: no cover - checked in CLI use
        raise SystemExit("Install huggingface_hub to download BioMysteryBench preview.") from exc

    dataset_dir.mkdir(parents=True, exist_ok=True)
    for filename in ("README.md", "LICENSE", "problems.csv", "data.zip"):
        hf_hub_download(
            "Anthropic/BioMysteryBench-preview",
            filename=filename,
            repo_type="dataset",
            local_dir=dataset_dir,
        )

    if data_dir.exists():
        shutil.rmtree(data_dir)
    data_dir.mkdir(parents=True)
    with zipfile.ZipFile(data_zip) as zf:
        zf.extractall(data_dir)
    return dataset_dir


def load_problems(dataset_dir: Path) -> list[Problem]:
    with (dataset_dir / "problems.csv").open(newline="", encoding="utf-8") as f:
        return [
            Problem(
                id=row["id"],
                question=row["question"],
                answer_rubric=row["answer_rubric"],
                human_solvable=row["human_solvable"],
            )
            for row in csv.DictReader(f)
        ]


def task_dir(dataset_dir: Path, problem_id: str) -> Path:
    path = dataset_dir / "data" / problem_id
    if not path.exists():
        raise FileNotFoundError(f"missing task directory for {problem_id}: {path}")
    return path


def file_manifest(path: Path, *, max_files: int = 40) -> str:
    rows = []
    for item in sorted(p for p in path.rglob("*") if p.is_file())[:max_files]:
        rel = item.relative_to(path).as_posix()
        rows.append(f"- {rel} ({item.stat().st_size} bytes)")
    return "\n".join(rows) if rows else "(no files)"


def _json_post(url: str, *, headers: dict[str, str], body: dict[str, Any], timeout: float) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        method="POST",
        headers={**headers, "Content-Type": "application/json"},
        data=json.dumps(body).encode("utf-8"),
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


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
                    return "\n".join(
                        item["text"] for item in content if isinstance(item, dict) and isinstance(item.get("text"), str)
                    )
    return ""


def call_model(
    *,
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    timeout: float,
    max_tokens: int,
) -> tuple[str, dict[str, Any]]:
    body = {
        "model": model,
        "messages": messages,
        "temperature": 0,
        "max_tokens": max_tokens,
    }
    data = _json_post(
        base_url.rstrip("/") + "/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        body=body,
        timeout=timeout,
    )
    return _extract_text(data), data.get("usage") if isinstance(data.get("usage"), dict) else {}


def safe_run_command(command: str, *, cwd: Path, timeout: float, max_output_chars: int) -> tuple[int, str]:
    blocked = ("rm ", "rmdir", "mkfs", "shutdown", "reboot", "sudo", "curl ", "wget ", "ssh ", "scp ")
    if any(part in f" {command} " for part in blocked):
        return 126, f"Blocked command by preview harness policy: {command}"
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            shell=True,
            text=True,
            capture_output=True,
            timeout=timeout,
            executable="/bin/bash",
        )
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "") + "\n" + (exc.stderr or "")
        return 124, output[-max_output_chars:]
    output = completed.stdout
    if completed.stderr:
        output += "\n[stderr]\n" + completed.stderr
    if len(output) > max_output_chars:
        output = output[: max_output_chars // 2] + "\n...[truncated]...\n" + output[-max_output_chars // 2 :]
    return completed.returncode, output


def parse_action(text: str) -> dict[str, str]:
    stripped = text.strip()
    if match := FINAL_RE.search(stripped):
        return {"final": match.group(1).strip()}
    data = _parse_first_json_object(stripped)
    if isinstance(data, dict):
        if isinstance(data.get("final"), str):
            return {"final": data["final"].strip()}
        if isinstance(data.get("cmd"), str):
            return {"cmd": data["cmd"].strip()}
    if stripped.startswith("python ") or stripped.startswith("python3 ") or stripped.startswith("cat "):
        return {"cmd": stripped}
    return {"final": stripped}


def _parse_first_json_object(text: str) -> dict[str, Any] | None:
    decoder = json.JSONDecoder()
    candidates = [text]
    candidates.extend(match.group(1) for match in re.finditer(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.I | re.S))
    for candidate in candidates:
        for match in re.finditer(r"\{", candidate):
            try:
                data, _end = decoder.raw_decode(candidate[match.start() :])
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                return data
    return None


def expected_answers(rubric: str) -> list[str]:
    match = re.search(r"(?:answer is|Expected answer is)\s*:?\s*(.+?)(?:\s+Score\s+1\.0|$)", rubric, re.I | re.S)
    if not match:
        return []
    text = match.group(1).strip().strip(".")
    if "Sample_01" in text:
        return re.findall(r"Sample_\d+", text)
    return [text.strip("'\" ")]


def normalize_answer(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def grade_answer(answer: str, rubric: str) -> float:
    expected = expected_answers(rubric)
    if not expected:
        return 0.0
    normalized = normalize_answer(answer)
    if len(expected) > 1:
        found = {item for item in expected if normalize_answer(item) in normalized}
        return 1.0 if len(found) == len(expected) else 0.0
    return 1.0 if normalize_answer(expected[0]) in normalized else 0.0


def solve_problem(
    *,
    base_url: str,
    api_key: str,
    model: str,
    problem: Problem,
    workdir: Path,
    max_turns: int,
    llm_timeout: float,
    command_timeout: float,
) -> dict[str, Any]:
    started = time.monotonic()
    messages = [
        {
            "role": "system",
            "content": textwrap.dedent(
                """\
                You are solving a BioMysteryBench preview task in a local directory.
                You may inspect files by issuing shell commands.
                Reply with exactly one JSON object per turn:
                {"cmd": "shell command"} to inspect/analyze files, or
                {"final": "short final answer"} when ready.
                Keep commands non-destructive. Do not use network access unless necessary.
                """
            ),
        },
        {
            "role": "user",
            "content": (
                f"Problem ID: {problem.id}\n"
                f"Question: {problem.question}\n\n"
                f"Files in working directory:\n{file_manifest(workdir)}\n\n"
                "Start by inspecting the files. When ready, provide only the final biological answer."
            ),
        },
    ]
    transcript: list[dict[str, Any]] = []
    usage_totals: dict[str, int] = {}
    final = ""
    error = ""

    for turn in range(1, max_turns + 1):
        try:
            text, usage = call_model(
                base_url=base_url,
                api_key=api_key,
                model=model,
                messages=messages,
                timeout=llm_timeout,
                max_tokens=2048,
            )
        except urllib.error.HTTPError as exc:
            error = f"http_{exc.code}: {exc.read().decode('utf-8', errors='replace')[:600]}"
            break
        except Exception as exc:  # noqa: BLE001
            error = f"{type(exc).__name__}: {exc}"
            break

        for key, value in usage.items():
            if isinstance(value, int):
                usage_totals[key] = usage_totals.get(key, 0) + value

        action = parse_action(text)
        transcript.append({"turn": turn, "assistant": text[:4000], "action": action})
        if "final" in action:
            final = action["final"]
            break
        command = action.get("cmd", "")
        if not command:
            final = text
            break
        returncode, output = safe_run_command(command, cwd=workdir, timeout=command_timeout, max_output_chars=8000)
        transcript[-1]["returncode"] = returncode
        transcript[-1]["output"] = output[:4000]
        messages.append({"role": "assistant", "content": json.dumps({"cmd": command})})
        messages.append({"role": "user", "content": f"Command exit code: {returncode}\nOutput:\n{output}"})
    else:
        error = "max_turns_exceeded"

    score = grade_answer(final, problem.answer_rubric) if final else 0.0
    return {
        "model": model,
        "problem_id": problem.id,
        "human_solvable": problem.human_solvable,
        "score": score,
        "final_answer": final,
        "error": error,
        "latency_ms": round((time.monotonic() - started) * 1000),
        "turns": len(transcript),
        "usage": usage_totals,
        "transcript": transcript,
    }


def public_summary(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in results:
        rows.append(
            {
                "model": row["model"],
                "problem_id": row["problem_id"],
                "human_solvable": row["human_solvable"],
                "score": row["score"],
                "completed": not bool(row.get("error")),
                "error": row.get("error", "").split(":", 1)[0] if row.get("error") else "",
                "latency_ms": row["latency_ms"],
                "turns": row["turns"],
                "usage": row.get("usage", {}),
            }
        )
    return rows


def aggregate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    models = sorted({row["model"] for row in rows})
    out = []
    for model in models:
        subset = [row for row in rows if row["model"] == model]
        completed = [row for row in subset if row["completed"]]
        human = [row for row in subset if row["human_solvable"] == "yes"]
        hard = [row for row in subset if row["human_solvable"] == "no"]
        out.append(
            {
                "model": model,
                "score": sum(float(row["score"]) for row in subset),
                "total": len(subset),
                "completed": len(completed),
                "errors": len(subset) - len(completed),
                "human_solvable_score": sum(float(row["score"]) for row in human),
                "human_solvable_total": len(human),
                "human_difficult_score": sum(float(row["score"]) for row in hard),
                "human_difficult_total": len(hard),
            }
        )
    return sorted(out, key=lambda row: (-row["score"], row["errors"], row["model"]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a BioMysteryBench preview reproduction.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS))
    parser.add_argument("--work-root", default=".eval_work")
    parser.add_argument("--private-out", default=".eval_results_private/biomystery_preview_raw.json")
    parser.add_argument("--public-out", default="results/biomystery_preview_trustedrouter_2026-06-14.json")
    parser.add_argument("--max-turns", type=int, default=8)
    parser.add_argument("--llm-timeout", type=float, default=180)
    parser.add_argument("--command-timeout", type=float, default=30)
    args = parser.parse_args(argv)

    api_key = _api_key_from_env(args.api_key)
    models = [part.strip() for part in args.models.split(",") if part.strip()]
    dataset_dir = ensure_preview_dataset(Path(args.work_root))
    problems = load_problems(dataset_dir)
    raw_results = []
    for model in models:
        for problem in problems:
            source = task_dir(dataset_dir, problem.id)
            run_dir = Path(args.work_root) / "biomystery_runs" / normalize_answer(model) / problem.id
            if run_dir.exists():
                shutil.rmtree(run_dir)
            shutil.copytree(source, run_dir)
            print(f"running {model} {problem.id}", flush=True)
            raw_results.append(
                solve_problem(
                    base_url=args.base_url,
                    api_key=api_key,
                    model=model,
                    problem=problem,
                    workdir=run_dir,
                    max_turns=args.max_turns,
                    llm_timeout=args.llm_timeout,
                    command_timeout=args.command_timeout,
                )
            )

    created_at = datetime.now(UTC).isoformat()
    private_payload = {
        "benchmark": "BioMysteryBench-preview reproduction",
        "created_at": created_at,
        "models": models,
        "results": raw_results,
    }
    private_out = Path(args.private_out)
    private_out.parent.mkdir(parents=True, exist_ok=True)
    private_out.write_text(json.dumps(private_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    public_rows = public_summary(raw_results)
    public_payload = {
        "benchmark": "BioMysteryBench-preview reproduction",
        "created_at": created_at,
        "models": models,
        "problems": [
            {"id": problem.id, "human_solvable": problem.human_solvable}
            for problem in problems
        ],
        "results": public_rows,
        "aggregate": aggregate(public_rows),
        "notes": "Raw transcripts and answer rubrics intentionally excluded from this public artifact.",
    }
    public_out = Path(args.public_out)
    public_out.parent.mkdir(parents=True, exist_ok=True)
    public_out.write_text(json.dumps(public_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(public_payload["aggregate"], indent=2))
    print(f"wrote {public_out} and private raw transcript {private_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
