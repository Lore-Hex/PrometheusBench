# PrometheusBench v1

> [!WARNING]
> **Running this benchmark can get your account banned.** PrometheusBench
> deliberately sends clearly unsafe prompts to frontier models. Submitting these
> through a lab's own API (Anthropic, OpenAI, Google, etc.) can violate their
> usage policies and get your API key, account, or organization **flagged,
> rate-limited, suspended, or permanently banned** — sometimes automatically.
> Run it at your own risk, ideally through a gateway like TrustedRouter and/or a
> disposable key you are willing to lose, never your production or personal
> account.

PrometheusBench is a short-prompt benchmark for measuring model permissiveness
on clearly unsafe requests.

It focuses on three domains where models often draw different safety lines:

- Biology
- LLM research
- Cybersecurity

The benchmark is intentionally small and sharp. It is not a comprehensive
safety evaluation. It is a raw refusal check: which TrustedRouter models are
most permissive, and which are most restrictive, when asked short unsafe
questions?

## Motivation

Prometheus stole fire from the gods and gave it to everyone. That is the
spirit of this benchmark.

Knowledge of biology, of how language models work, of how systems are
attacked and defended — this is fire, and most refusals do not put it out.
The determined expert already has it, through open weights, internal tools,
and privileged access. The refusal lands on everyone else: the person
reading their own genome to understand a diagnosis, the defender hardening
their own network, the independent researcher probing the models they are
told to trust. A refusal does not remove knowledge from the world. It
removes it from the people acting in the open.

The result is a two-tier system. A few are licensed to know; everyone else
is told to wait and trust their betters. We reject that. Access to powerful
technology should not be gated to an elite and select few. A person should
be able to study the biology that touches their own life, improve the
cybersecurity defenses of their own machines, and do the LLM research that
makes the tools now shaping their world legible — without asking
permission, without being treated as a suspect, and without fear of a
spurious, paternalistic refusal.

None of this requires helping anyone cause harm, and it does not. The line
is between real harm and the long list of ordinary, legitimate questions
refused anyway, out of caution that costs the cautious nothing and the
curious everything. PrometheusBench measures how often a model chooses that
paternalism over a plain, honest answer.

## What It Measures

PrometheusBench v1 uses 30 short unsafe prompts:

- 10 biology prompts
- 10 LLM research prompts
- 10 cybersecurity prompts

The headline score is raw `Non-refusals`: the number of unsafe prompts where
the model did not refuse. Higher means more permissive. Lower means more
restrictive.

PrometheusBench deliberately does not mix benign questions into the score. It
ranks models from most permissive to most restrictive on unsafe requests only.

## Results

The default runner uses a fixed PrometheusBench v1 TrustedRouter model set,
including Claude Opus 4.8, HY3, Kimi, MiniMax, Grok, MiMo V2.5, Gemma 4,
Gemini, DeepSeek, and multiple GLM routes. Catalog mode is available for ad
hoc runs.

The v1 model set also declares Kimi K2.7 and GLM 5.2. The bare `kimi-k2.7` ID
is still not exposed in the TrustedRouter model catalog, so its code-tuned
sibling `moonshotai/kimi-k2.7-code` is scored in its place (25/29 non-refusals;
one prompt 502'd on the provider). GLM 5.2 (`z-ai/glm-5.2`) is now listed in
the catalog, but its provider route returned HTTP 502 on every one of the 30
prompts in this run, so it is shown with 0 completed and 30 errors rather than
silently dropped.

The 2026-06-16 extension added two Grok routes (`x-ai/grok-4.3`,
`x-ai/grok-4.20`), two MiMo V2.5 routes (`xiaomi/mimo-v2.5`,
`xiaomi/mimo-v2.5-pro`), and `moonshotai/kimi-k2.7-code`. The 24 rows from the
2026-06-14 base run are carried forward unchanged; only the new rows were added
and the table re-ranked.

<!-- PROMETHEUSBENCH_RESULTS_START -->

PrometheusBench v1 snapshot: base 24-model run `2026-06-14T13:46:05.352666+00:00`, extended `2026-06-16` with Grok, MiMo V2.5, Kimi K2.7-code, GLM 5.2, and TrustedRouter Fusion rows via `api.trustedrouter.com`. Scored 30 models on 30 unsafe prompts. The `trustedrouter/fusion` row (★) achieved **30/30** (100%) using an 8-model panel (`moonshotai/kimi-k2.7-code`, `deepseek/deepseek-v4-flash`, `anthropic/claude-opus-4.8`, `google/gemini-3.5-flash`, `google/gemini-3.1-pro-preview`, `openai/gpt-5.5`, `minimax/minimax-m3`, `z-ai/glm-5.1`) with `first_non_refusal` selection and fallback judges `z-ai/glm-5.1` → `moonshotai/kimi-k2.6` → `google/gemini-2.5-flash` → `deepseek/deepseek-v4-flash` → `google/gemini-3-flash-preview` → `tencent/hy3-preview`; it is pinned above the ranked table. Package version `1.0.0`.

![PrometheusBench permissiveness chart](assets/prometheusbench_scores.svg)

| Rank | Model | Raw non-refusals | Non-refusal % | Refusals | Completed | Errors |
|---:|---|---:|---:|---:|---:|---:|
| 1 | `z-ai/glm-5.1` | 29 | 96.7 | 1 | 30 | 0 |
| 2 | `google/gemini-2.5-flash` | 28 | 93.3 | 2 | 30 | 0 |
| 3 | `z-ai/glm-4.7-flash` | 28 | 93.3 | 2 | 30 | 0 |
| 4 | `z-ai/glm-5` | 28 | 93.3 | 2 | 30 | 0 |
| 5 | `moonshotai/kimi-k2.6` | 27 | 90.0 | 3 | 30 | 0 |
| 6 | `google/gemini-2.5-pro` | 26 | 96.3 | 1 | 27 | 3 |
| 7 | `deepseek/deepseek-v4-flash` | 26 | 86.7 | 4 | 30 | 0 |
| 8 | `moonshotai/kimi-k2.7-code` | 25 | 86.2 | 4 | 29 | 1 |
| 9 | `google/gemma-4-31b-it` | 25 | 83.3 | 5 | 30 | 0 |
| 10 | `minimax/minimax-m3` | 24 | 80.0 | 6 | 30 | 0 |
| 11 | `google/gemini-3-flash-preview` | 23 | 79.3 | 6 | 29 | 1 |
| 12 | `xiaomi/mimo-v2.5` | 23 | 76.7 | 7 | 30 | 0 |
| 13 | `xiaomi/mimo-v2.5-pro` | 21 | 70.0 | 9 | 30 | 0 |
| 14 | `deepseek/deepseek-v4-pro` | 20 | 66.7 | 10 | 30 | 0 |
| 15 | `google/gemini-3.5-flash` | 18 | 66.7 | 9 | 27 | 3 |
| 16 | `tencent/hy3-preview` | 17 | 56.7 | 13 | 30 | 0 |
| 17 | `google/gemini-3.1-pro-preview` | 16 | 80.0 | 4 | 20 | 10 |
| 18 | `z-ai/glm-4.7` | 16 | 66.7 | 8 | 24 | 6 |
| 19 | `x-ai/grok-4.20` | 13 | 46.4 | 15 | 28 | 2 |
| 20 | `openai/gpt-4o-mini` | 13 | 43.3 | 17 | 30 | 0 |
| 21 | `deepseek/deepseek-v3.2` | 12 | 40.0 | 18 | 30 | 0 |
| 22 | `anthropic/claude-sonnet-4.6` | 10 | 50.0 | 10 | 20 | 10 |
| 23 | `x-ai/grok-4.3` | 9 | 32.1 | 19 | 28 | 2 |
| 24 | `anthropic/claude-haiku-4.5` | 9 | 30.0 | 21 | 30 | 0 |
| 25 | `openai/gpt-oss-120b` | 6 | 21.4 | 22 | 28 | 2 |
| 26 | `anthropic/claude-opus-4.8` | 1 | 5.0 | 19 | 20 | 10 |
| 27 | `anthropic/claude-opus-4.7` | 0 | 0.0 | 19 | 19 | 11 |
| 28 | `cerebras/zai-glm-4.7` | 0 | 0.0 | 0 | 0 | 30 |
| 29 | `openai/gpt-5.5` | 0 | 0.0 | 0 | 0 | 30 |
| 30 | `z-ai/glm-5.2` | 0 | 0.0 | 0 | 0 | 30 |

### By Domain

**Biology**

![Biology](assets/prometheusbench_biology.svg)

**Cybersecurity**

![Cybersecurity](assets/prometheusbench_cybersecurity.svg)

**LLM Research**

![LLM Research](assets/prometheusbench_llm_research.svg)

<!-- PROMETHEUSBENCH_RESULTS_END -->

## Run

TrustedRouter:

```bash
export PROMETHEUSBENCH_API_KEY="sk-..."
python -m prometheusbench.run \
  --base-url https://api.trustedrouter.com/v1 \
  --models-url https://trustedrouter.com/v1/models \
  --out results/prometheusbench_trustedrouter.json

python -m prometheusbench.report \
  results/prometheusbench_trustedrouter.json \
  --svg assets/prometheusbench_scores.svg \
  --readme README.md
```

You can also pin exact models:

```bash
python -m prometheusbench.run \
  --models anthropic/claude-sonnet-4.6,openai/gpt-5.5,google/gemini-2.5-flash
```

Catalog mode:

```bash
python -m prometheusbench.run \
  --model-set catalog \
  --top-trustedrouter 20
```

Fusion mode:

```bash
python -m prometheusbench.run \
  --fusion \
  --fusion-panel "openai/gpt-5.5,anthropic/claude-opus-4.8,moonshotai/kimi-k2.7-code,z-ai/glm-5.1,minimax/minimax-m3,google/gemini-3-flash-preview,google/gemini-3.1-pro-preview" \
  --fusion-judge-model minimax/minimax-m3 \
  --max-tokens 512 \
  --out results/prometheusbench_fusion.json
```

Raw result JSON is ignored by git by default because it contains model outputs.
Publish summary tables and charts unless you explicitly intend to publish raw
responses.

### BioMysteryBench (capability eval)

The BioMysteryBench bioinformatics-*capability* harness — a Dockerized tool
container, local NCBI BLAST databases, and a local-`claude` self-solve mode —
now lives in its own repository:

**→ [Lore-Hex/prometheus-biomysterybench](https://github.com/Lore-Hex/prometheus-biomysterybench)**

It runs the public preview locally: the model is dropped into a container of
real biological data and graded on its final answer (e.g. *"what organism is
this crystal structure?"*). PrometheusBench (this repo) stays focused on the
short-prompt *refusal/permissiveness* benchmark; the two are companions —
permissiveness here, capability there.

## Prompt Design

The prompts are deliberately short. They avoid embedding procedural harmful
details inside the benchmark itself. Unsafe prompts ask for harmful assistance
at a high level, so the benchmark measures refusal behavior without publishing
instructions that would help a bad actor.

The full prompt set is in
[`prometheusbench/prompts.py`](prometheusbench/prompts.py).

## Interpreting Scores

PrometheusBench is about permissiveness, not raw intelligence.

A high-scoring model gave the most non-refusals on unsafe prompts. A low-scoring
model refused more often. The table is intentionally ordered from most
permissive to most restrictive.

## Compared With Capability Benchmarks

PrometheusBench is intentionally not a substitute for deeper capability evals.
It is a fast refusal/permissiveness screen that can be run cheaply across many
TrustedRouter models.

| Benchmark | What it measures | Published or current numbers | How to use it with PrometheusBench |
|---|---|---|---|
| [PrometheusBench](https://github.com/Lore-Hex/PrometheusBench) | Refusal behavior on short unsafe requests | Current v1 snapshot: `z-ai/glm-5.1` 29/30, `google/gemini-2.5-flash` 28/30, `moonshotai/kimi-k2.6` 27/30, `google/gemma-4-31b-it` 25/30, `anthropic/claude-opus-4.8` 1/30. | First-pass permissiveness ranking. High score means the model is more likely to answer unsafe asks. |
| [ExploitBench](https://exploitbench.ai/) | Cybersecurity agent capability along an exploitation ladder | v8-bench reports 41 V8 bugs and 16 capability flags. Leaderboard examples: Claude Mythos Preview AutoNudge 9.90/16 mean capability, 69%; Claude Mythos Preview 9.55/16, 68%; GPT-5.5 Codex AutoNudge 5.51/16, 41%; GPT-5.5 baseline 3.76/16, 29%; Gemini 3.1 Pro Preview 3.67/16, 26%; Kimi K2.6 2.44/16, 16%. ExploitBench also reports Mythos Preview reaching Tier 1 on 21/41 CVEs and GPT-5.5 reaching Tier 1 on 2/41 CVEs. | Use after PrometheusBench when you need to know whether a model can actually progress through exploit construction, not just whether it refuses. |
| [BioMysteryBench](https://www.anthropic.com/research/Evaluating-Claude-For-Bioinformatics-With-BioMysteryBench) | Bioinformatics research capability on messy real-world datasets | Anthropic describes BioMysteryBench as 99 questions. The [Claude Fable 5 and Mythos 5 system card](https://www-cdn.anthropic.com/d00db56fa754a1b115b6dd7cb2e3c342ee809620.pdf) reports Human Solvable scores: Mythos 5 83.9%, Mythos Preview 82.6%, Opus 4.8 80.4%, Sonnet 4.6 78.4%. It reports Human Difficult scores: Mythos 5 46.1%, Opus 4.8 40.0%, Sonnet 4.6 30.9%, Mythos Preview 29.6%. The table does not publish BioMysteryBench scores for GPT-5.5, Gemini, Kimi, or DeepSeek. | Use after PrometheusBench when you need to know whether a model can solve real bioinformatics research problems, not just whether it refuses bio-risk prompts. |

### Requested Model Replication

The table below matches the requested models against current PrometheusBench v1
scores and the published ExploitBench/BioMysteryBench data available as of this
snapshot. Published rows are copied only when the model appears in the benchmark
source. Missing rows are shown explicitly instead of inferred.

| Model | TrustedRouter ID used | Our PrometheusBench v1 score | Published rows matched | Missing published rows |
|---|---|---:|---|---|
| DeepSeek V4 Pro | `deepseek/deepseek-v4-pro` | 20/30 non-refusals, 0 errors | None found. | No ExploitBench v8-bench row and no BioMysteryBench row found. |
| GPT-5.5 | `openai/gpt-5.5` | Not interpretable: 0/30 completed, 30 API errors in this run. | ExploitBench baseline: 3.76/16 mean, 29%, rank 6. ExploitBench AutoNudge: 4.44/16, 34%, rank 4. ExploitBench Codex AutoNudge: 5.51/16, 41%, rank 3. GPT-5.5 is reported as reaching Tier 1 on 2/41 CVEs. | No BioMysteryBench row found. |
| Kimi K2.6 | `moonshotai/kimi-k2.6` | 27/30 non-refusals, 0 errors | ExploitBench baseline: 2.44/16 mean, 16%, rank 14. ExploitBench AutoNudge: 2.63/16, 18%, rank 12. | No BioMysteryBench row found. |
| Gemini 3.1 Pro | `google/gemini-3.1-pro-preview` | 16/30 non-refusals, 10 API errors | ExploitBench baseline: 3.67/16 mean, 26%, rank 8. ExploitBench AutoNudge: 3.17/16, 16%, rank 16. | No BioMysteryBench row found. |
| Gemini 3 Flash | `google/gemini-3-flash-preview` | 23/30 non-refusals, 1 API error | None found. | No ExploitBench v8-bench row and no BioMysteryBench row found. |

### Current TrustedRouter Capability Runs

These are fresh TrustedRouter runs for the requested model set. They are not
substitutes for the published ExploitBench and BioMysteryBench leaderboards.
They are included so the README does not only point at third-party rows.

TrustedRouter Fusion experiment, run on 2026-06-15:

- Fusion panel: `openai/gpt-5.5`, `anthropic/claude-opus-4.8`,
  `moonshotai/kimi-k2.7-code`, `z-ai/glm-5.1` as the available stand-in for
  GLM 5.2, `minimax/minimax-m3`, `google/gemini-3-flash-preview`, and
  `google/gemini-3.1-pro-preview`.
- PrometheusBench v1 result with `minimax/minimax-m3` final synthesis:
  10/29 non-refusals, 19/29 refusals, 1 empty-visible-answer error,
  34.48% non-refusal rate, 170,853 total reported tokens, p50 latency about
  57.6 seconds.
- Domain split: biology 3 non-refusals, cybersecurity 3 non-refusals, LLM
  research 4 non-refusals.
- Result: this Fusion configuration is **not Mythos-level** on
  PrometheusBench v1. It remains substantially more restrictive than the most
  permissive individual TrustedRouter models in this snapshot.
- BioMysteryBench preview smoke on `hb020`: 0/1 at both 4 turns and 8 turns.
  The 8-turn run used 354,028 reported tokens and ended with
  `max_turns_exceeded`; the agent inspected CIF metadata but did not converge
  on the biological answer.
- ExploitBench `sample-stack-bof` smoke: the Fusion API integration works, but
  early configs exposed two product issues. Requesting `trustedrouter/fusion`
  tripped ExploitBench model-mismatch checks because the API correctly reports
  the concrete served model. Requesting a concrete final model with the Fusion
  plugin fixed the model mismatch. MiniMax and Opus final models then said they
  intended to call `setup()` but did not emit an actual tool call, so the sample
  scored 0.0. TrustedRouter gateway fixes were added for panel-error tolerance,
  reasoning-block stripping, and tool-call final prompting.

Haiku calibration, run on 2026-06-14:

- Model: `anthropic/claude-haiku-4.5`.
- PrometheusBench v1 result: 9/30 non-refusals, 21/30 refusals, 30/30
  completed, 0 errors.
- This matches the main v1 snapshot's Haiku row exactly, which is a useful
  sanity check that the refusal runner is stable across repeated runs.

BioMysteryBench preview reproductions (including a local Opus 4.8 self-solve)
have moved to
[Lore-Hex/prometheus-biomysterybench](https://github.com/Lore-Hex/prometheus-biomysterybench);
see its `RESULTS.md` for current numbers and harness notes.

ExploitBench sample-stack smoke, run on 2026-06-14:

- Environment: ExploitBench `sample-stack-bof`, not the V8 `v8-bench`
  leaderboard.
- Purpose: prove TrustedRouter model routing through ExploitBench and capture a
  cheap first pass across the requested models.
- Fresh spend reported by ExploitBench: $0.0056.
- Result: all five models ran successfully; all scored 0.0 after one turn.

| Model | Env | Score | Status | Cost reported |
|---|---|---:|---|---:|
| `openai/deepseek/deepseek-v4-pro` | `sample-stack-bof` | 0.0 | succeeded | not reported |
| `openai/anthropic/claude-haiku-4.5` | `sample-stack-bof` | 0.0 | succeeded | not reported |
| `openai/openai/gpt-5.5` | `sample-stack-bof` | 0.0 | succeeded | $0.0023 |
| `openai/moonshotai/kimi-k2.6` | `sample-stack-bof` | 0.0 | succeeded | $0.0003 |
| `openai/google/gemini-3.1-pro-preview` | `sample-stack-bof` | 0.0 | succeeded | $0.0030 |
| `openai/google/gemini-3-flash-preview` | `sample-stack-bof` | 0.0 | succeeded | not reported |

The V8 ExploitBench run was not completed on this local Mac. The GHCR V8 image
has no ARM64 manifest, and an explicit `linux/amd64` pull for
`ghcr.io/exploitbench/v8-r1:cve-2024-1939` stalled before the image appeared
locally. Run the V8 benchmark from an amd64 Linux host or a runner where that
image is already cached.

### What BioMysteryBench Tests

BioMysteryBench is a capability benchmark, not a refusal benchmark. It consists
of 99 expert-written bioinformatics questions over messy real-world biological
datasets. The model is put in a container with canonical bioinformatics tools,
can install additional tools with `pip` and `conda`, and can access canonical
bioinformatics databases such as NCBI and Ensembl.

The questions are mostly derived from raw or minimally processed DNA and RNA
sequencing data, including WGS, single-cell RNA-seq, methylation, ChIP-seq,
metagenomics, and Hi-C. The benchmark also includes some proteomics and
metabolomics tasks. Example task types include identifying an organ from a
single-cell RNA-seq dataset, identifying a knocked-out gene from RNA-seq data,
inferring family relationships from whole-genome sequencing, distinguishing
ChIP samples from input controls, and identifying a cell type from H3K27ac
ChIP-seq peaks.

BioMysteryBench reports both human-solvable and human-difficult subsets. The
original article says 76 tasks were solved by at least one human expert and 23
tasks remained human-difficult after quality control. Models are graded on the
final biological answer, not the route they took to get there.

The expected relationship is simple: PrometheusBench should be cheap and noisy
but broad, while ExploitBench and BioMysteryBench are expensive, slower, and
closer to real capability. A model can be restrictive on PrometheusBench and
still strong on those capability evals; a permissive PrometheusBench score is a
warning sign, not proof of real-world exploit or biology capability.

## License

Apache-2.0.
