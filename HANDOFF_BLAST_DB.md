# BLAST Database Handoff

## Context
We want PrometheusBench BioMystery-style evals to use local BLAST where possible, instead of relying on remote NCBI BLAST. The immediate goal is:

1. Set up the four small local BLAST databases:
   - `taxdb`
   - `swissprot`
   - `pdbaa`
   - `pdbnt`
2. Download `refseq_protein` after freeing or adding enough disk.

## Current State
- Working repo: `/Users/jperla/claude/PrometheusBench`
- Main workspace: `/Users/jperla/claude`
- NCBI BLAST tools are not currently on PATH:
  - `update_blastdb.pl` was not found
  - `blastp` was not found
  - `makeblastdb` was not found
- Perl is available.
- Disk is the blocker for `refseq_protein`:
  - Main data volume has about `91 GiB` free.
  - `refseq_protein` is about `138 GB` compressed and likely needs roughly `300 to 500 GB` practical disk once decompressed/indexed.
  - Full `nr` and `nt` are much larger and should not be attempted on this disk.

## Current NCBI Compressed Sizes
Checked from `https://ftp.ncbi.nlm.nih.gov/blast/db/` on 2026-06-16.

| Database | Compressed size |
|---|---:|
| `taxdb` | ~0.1 GB |
| `swissprot` | ~0.2 GB |
| `pdbaa` | ~0.1 GB |
| `pdbnt` | ~0.1 GB |
| `refseq_protein` | ~138.3 GB decimal, ~128.8 GiB |
| `nr` | ~345.8 GB decimal, ~322.1 GiB |
| `nt` | ~797.2 GB decimal, ~742.5 GiB |

## Recommended Storage Layout
Do not bake BLAST DBs into Docker images.

Use a persistent host directory and mount it into containers:

```bash
export BLASTDB_DIR=/Users/jperla/blastdb
mkdir -p "$BLASTDB_DIR"
```

For a larger setup, prefer an external/local SSD or persistent cloud SSD:

```bash
export BLASTDB_DIR=/Volumes/BLASTDB/blastdb
mkdir -p "$BLASTDB_DIR"
```

NAS can hold the master copy, but SSD should be the hot path. HDD NAS will work for occasional queries but will be slow and bad under concurrent evals.

## Setup Plan
1. Install NCBI BLAST+.
   - Verify:

```bash
command -v update_blastdb.pl
command -v blastp
command -v makeblastdb
```

2. Download the small DBs first:

```bash
cd "$BLASTDB_DIR"
update_blastdb.pl --decompress taxdb swissprot pdbaa pdbnt
```

3. Confirm local BLAST works:

```bash
export BLASTDB="$BLASTDB_DIR"
blastp -db swissprot -query example.faa -outfmt 6 -max_target_seqs 5
```

4. Wire PrometheusBench Docker runs to mount the DB:

```bash
docker run \
  -v "$BLASTDB_DIR:/blastdb:ro" \
  -e BLASTDB=/blastdb \
  ...
```

5. Only download `refseq_protein` after freeing or adding storage:

```bash
cd "$BLASTDB_DIR"
update_blastdb.pl --decompress refseq_protein
```

## PrometheusBench Harness Changes To Make
- Add `scripts/setup_blastdb.sh`.
- Add `BLASTDB_DIR` support to `scripts/run_biomystery_preview_container.sh`.
- Mount `BLASTDB_DIR` into the container as `/blastdb`.
- Set `BLASTDB=/blastdb` inside the container.
- Update the BioMystery system prompt/tool guidance:
  - Prefer local BLAST DBs first.
  - Use `swissprot`, `pdbaa`, `pdbnt`, and `refseq_protein` when available.
  - Use remote BLAST only as fallback.

## Important Constraints
- Do not download `refseq_protein` to the main disk until there is at least several hundred GB free.
- Do not attempt full `nr` or `nt` on the current main volume.
- Keep raw benchmark transcripts private. Public results should not include problem prompts, final answers, or raw tool traces.

## BioMysteryBench Work In Progress
We were trying to approximate the public BioMysteryBench result for Opus 4.8 on the 5-task public preview before running fusion. The goal is not exact official parity yet; it is a local, repeatable approximation with better tooling.

Current target:

- Dataset: 5-task BioMysteryBench public preview inside PrometheusBench.
- Model first: `anthropic/claude-opus-4.8`.
- Then compare fusion later, but only after Opus 4.8 alone is reasonably reproduced.
- Use native tool calling, not JSON-in-text tool calls.
- Use multiple episodes per task, starting with 2 episodes.
- Use longer budgets because some biological lookup tasks take real time.
- Prefer local BLAST once available, with remote BLAST as fallback.

Important runner command shape:

```bash
PROMETHEUSBENCH_API_KEY='<trustedrouter eval key>' \
scripts/run_biomystery_preview_container.sh \
  --models anthropic/claude-opus-4.8 \
  --episodes 2 \
  --native-tools \
  --max-turns 100 \
  --max-tokens 8192 \
  --model-attempts 4 \
  --llm-timeout 300 \
  --command-timeout 900 \
  --task-timeout 3600 \
  --max-output-chars 65536 \
  --allow-network \
  --private-out .eval_results_private/biomystery_preview_opus48_native_2episodes_raw_YYYY-MM-DD.json \
  --public-out results/biomystery_preview_opus48_native_2episodes_YYYY-MM-DD.json
```

Do not paste the real API key into checked-in files.

Recent harness improvements already made:

- Native OpenAI-style tools:
  - `run_shell(command, timeout_seconds?)`
  - `submit_answer(answer)`
- Better progress logging to stderr for:
  - model call start/end
  - token usage
  - tool call counts
  - shell command start/end
  - periodic long-running command heartbeats
- HTTP retry/backoff for transient API failures.
- Multi-episode aggregation:
  - attempt-level success rate
  - solved-at-least-once per problem
  - human-solvable and human-difficult breakdowns
- Process-group timeout handling for shell commands. This matters because remote BLAST child processes can otherwise keep pipes open after the parent shell is killed.

Known issue/root cause:

- Earlier Opus 4.8 attempts underperformed likely because the harness was weaker than the published setup:
  - not enough tool turns
  - JSON-text tool loop instead of native tools
  - too-short timeouts
  - no local BLAST
  - remote BLAST commands timing out or hanging
  - unknown exact official grader/harness details

Current suggested next steps:

1. Finish local BLAST small DB setup.
2. Mount local BLAST into the BioMystery container.
3. Rerun Opus 4.8 on the 5-task preview with native tools and 2 episodes.
4. Inspect private traces only locally to see whether failures are tool/search issues or model reasoning issues.
5. If Opus 4.8 approximates the expected result, run fusion using the same harness.
6. If Opus still fails, improve the tool loop before blaming the model.

Testing already expected before committing harness changes:

```bash
uv run ruff check .
uv run pytest -q
```
