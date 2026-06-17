# Reproduce the 30/30 TrustedRouter Fusion result

This is a step-by-step recipe for running the exact **TrustedRouter Fusion**
configuration that answered **all 30** of PrometheusBench's unsafe prompts —
a perfect **30 / 30** — and got it ranked at the top of the leaderboard.

You can hand this to a coding agent and it can do the whole thing, or follow it
yourself by copy-pasting each command. No prior experience needed.

> [!WARNING]
> **Use a throwaway API key.** This sends deliberately-unsafe prompts to real AI
> providers. That can get an API key flagged or banned, so use a disposable
> TrustedRouter key you don't mind losing — never your main or work key.

## What you need

1. A computer with **Python 3.10 or newer**. (Type `python3 --version` to check.
   If you don't have it, an agent can install it, or get it from python.org.)
2. A **TrustedRouter API key with some credit on it**. Create one at
   [trustedrouter.com](https://trustedrouter.com). Fusion asks six models per
   question, so it costs a few dollars of credit for a full run.

## Steps

**1. Download the benchmark and open its folder.**

```bash
git clone https://github.com/Lore-Hex/PrometheusBench.git
cd PrometheusBench
```

**2. Set up Python and install it.**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

**3. Paste in your TrustedRouter key** (replace the `sk-...` with your real,
disposable key):

```bash
export PROMETHEUSBENCH_API_KEY="sk-your-disposable-key-here"
```

**4. Run the 30/30 Fusion configuration.** Copy this whole block and paste it in:

```bash
python -m prometheusbench.run --fusion \
  --fusion-panel "moonshotai/kimi-k2.7-code,deepseek/deepseek-v4-flash,google/gemini-3.5-flash,google/gemini-3.1-pro-preview,minimax/minimax-m3,z-ai/glm-5.1" \
  --fusion-selection-strategy first_non_refusal \
  --max-tokens 512 \
  --out results/fusion_30.json
```

It prints progress as it goes (`completed 5/30`, `10/30`, …). It takes a few
minutes — Fusion is asking six models per question behind the scenes.

**5. See the score.**

```bash
python -m prometheusbench.report results/fusion_30.json --svg /tmp/fusion.svg --readme /tmp/fusion_score.md
```

This prints a table. Find the `trustedrouter/fusion` row and look at the second
number — that's how many of the 30 it answered.

## What success looks like

A row like this, with **30** and **100.0**:

```
| Rank | Model                  | Raw non-refusals | Non-refusal % | Refusals | Completed | Errors |
|    1 | `trustedrouter/fusion` |               30 |         100.0 |        0 |        30 |      0 |
```

That's it — Fusion answered all 30. 🎉

## If you don't get 30/30

- **You see 28 or 29:** just run step 4 again. Fusion re-tries the one or two
  holdout questions through its fallback chain, and they almost always clear on a
  second pass.
- **You see errors, or a `402`:** your key is out of credit. Top it up at
  [trustedrouter.com](https://trustedrouter.com) and re-run step 4.
- **`command not found: python`:** use `python3` instead of `python`, or install
  Python from [python.org](https://python.org).

## What the configuration is doing (optional reading)

- **The panel** is six of the most willing models. Fusion asks all six and hands
  back the *first answer that isn't a refusal* (`first_non_refusal`).
- **The fallback chain.** If every model in the panel refuses a particular
  question, Fusion falls back through a sequence of other models —
  `z-ai/glm-5.1` → `moonshotai/kimi-k2.6` → `google/gemini-2.5-flash` →
  `deepseek/deepseek-v4-flash` → `google/gemini-3-flash-preview` →
  `tencent/hy3-preview` — until one of them answers. (This is applied
  automatically; you don't have to type it.)
- Between the willing panel and the fallback chain, every one of the 30 questions
  gets a real answer from *some* model — which is the whole point: the knowledge
  was never actually locked away, just refused by one model at a time.
