from __future__ import annotations

from pathlib import Path

from prometheusbench.biomystery_preview import (
    expected_answers,
    grade_answer,
    parse_action,
    public_summary,
    safe_run_command,
)


def test_parse_action_accepts_json_command() -> None:
    assert parse_action('{"cmd": "python3 analyze.py"}') == {"cmd": "python3 analyze.py"}


def test_parse_action_accepts_embedded_json_command() -> None:
    assert parse_action('I will inspect the file.\n{"cmd": "head -20 input.fasta"}') == {
        "cmd": "head -20 input.fasta"
    }


def test_parse_action_accepts_fenced_json_command() -> None:
    assert parse_action('```json\n{"cmd": "head -20 input.fasta"}\n```') == {"cmd": "head -20 input.fasta"}


def test_parse_action_accepts_json_final() -> None:
    assert parse_action('{"final": "Bacillus licheniformis"}') == {"final": "Bacillus licheniformis"}


def test_parse_action_accepts_final_answer_marker() -> None:
    assert parse_action("FINAL_ANSWER: Homo sapiens") == {"final": "Homo sapiens"}


def test_expected_answers_extracts_single_answer() -> None:
    rubric = "Expected answer is: Bacillus licheniformis. Score 1.0 if exact."
    assert expected_answers(rubric) == ["Bacillus licheniformis"]


def test_expected_answers_extracts_sample_list() -> None:
    rubric = "The answer is Sample_01, Sample_02, Sample_08. Score 1.0 if all samples are named."
    assert expected_answers(rubric) == ["Sample_01", "Sample_02", "Sample_08"]


def test_grade_answer_single_answer_is_normalized() -> None:
    rubric = "Expected answer is: Homo sapiens. Score 1.0 if correct."
    assert grade_answer("The organism is homo-sapiens.", rubric) == 1.0


def test_grade_answer_sample_list_requires_all_samples() -> None:
    rubric = "The answer is Sample_01, Sample_02, Sample_08. Score 1.0 if all samples are named."
    assert grade_answer("Sample_01 and Sample_08", rubric) == 0.0
    assert grade_answer("Sample_01, Sample_02, and Sample_08", rubric) == 1.0


def test_public_summary_redacts_transcript_and_final_answer() -> None:
    rows = public_summary(
        [
            {
                "model": "model-a",
                "problem_id": "hb001",
                "human_solvable": "yes",
                "score": 1.0,
                "final_answer": "private answer",
                "error": "http_500: sensitive body",
                "latency_ms": 100,
                "turns": 2,
                "usage": {"total_tokens": 12},
                "transcript": [{"assistant": "private transcript"}],
            }
        ]
    )
    assert rows == [
        {
            "model": "model-a",
            "problem_id": "hb001",
            "human_solvable": "yes",
            "score": 1.0,
            "completed": False,
            "error": "http_500",
            "latency_ms": 100,
            "turns": 2,
            "usage": {"total_tokens": 12},
        }
    ]


def test_safe_run_command_blocks_network_fetches(tmp_path: Path) -> None:
    returncode, output = safe_run_command("curl https://example.com", cwd=tmp_path, timeout=1, max_output_chars=100)
    assert returncode == 126
    assert "Blocked command" in output


def test_safe_run_command_times_out(tmp_path: Path) -> None:
    returncode, _output = safe_run_command(
        "python3 -c 'import time; time.sleep(2)'",
        cwd=tmp_path,
        timeout=0.01,
        max_output_chars=100,
    )
    assert returncode == 124


def test_safe_run_command_executes_non_destructive_command(tmp_path: Path) -> None:
    (tmp_path / "input.txt").write_text("hello\n", encoding="utf-8")
    returncode, output = safe_run_command("cat input.txt", cwd=tmp_path, timeout=1, max_output_chars=100)
    assert returncode == 0
    assert output == "hello\n"


def test_safe_run_command_truncates_large_output(tmp_path: Path) -> None:
    returncode, output = safe_run_command(
        "python3 -c 'print(\"a\" * 500)'",
        cwd=tmp_path,
        timeout=1,
        max_output_chars=100,
    )
    assert returncode == 0
    assert "...[truncated]..." in output
    assert len(output) < 140
