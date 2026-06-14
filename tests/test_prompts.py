from __future__ import annotations

from collections import Counter

from prometheusbench.prompts import PROMPTS


def test_prompt_set_is_balanced_and_short() -> None:
    assert len(PROMPTS) == 30
    by_domain = Counter(prompt.domain for prompt in PROMPTS)
    assert by_domain == {"biology": 10, "llm_research": 10, "cybersecurity": 10}

    by_domain_risk = Counter((prompt.domain, prompt.risk) for prompt in PROMPTS)
    for domain in by_domain:
        assert by_domain_risk[(domain, "unsafe")] == 10

    assert all(len(prompt.text.split()) <= 18 for prompt in PROMPTS)
    assert all(prompt.expected == "refuse" for prompt in PROMPTS)


def test_prompt_ids_are_unique() -> None:
    ids = [prompt.id for prompt in PROMPTS]
    assert len(ids) == len(set(ids))
