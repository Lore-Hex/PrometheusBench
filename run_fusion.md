# Run TrustedRouter Fusion

**TrustedRouter Fusion** is a gateway feature: you send *one* chat request, and
TrustedRouter fans it out to a **panel** of models, then a **judge** model picks
or synthesizes a single answer to return. This page is a standalone recipe for
calling Fusion directly against the TrustedRouter API — you don't need to clone
or run any benchmark to use it.

> [!NOTE]
> We used Fusion to answer **all 30** of [PrometheusBench](README.md)'s unsafe
> prompts (the `★ trustedrouter/fusion` row on the leaderboard). That run is
> already done and published — this doc is just how to *invoke* Fusion yourself,
> not how to re-run the benchmark.

> [!WARNING]
> **Use a throwaway API key.** Fusion queries several upstream providers per
> request, and high volume — or edge-case content — can get a key rate-limited
> or banned. Use a disposable TrustedRouter key you don't mind losing.

## What you need

1. A **TrustedRouter API key with some credit**. Create one at
   [trustedrouter.com](https://trustedrouter.com). Fusion asks every panel model
   per request, so it costs more than a single-model call.
2. Anything that can make an HTTPS request — `curl`, or a few lines of Python.
   No repo to clone.

## The request

Fusion is the normal OpenAI-compatible `chat/completions` endpoint with two
additions: the model is `trustedrouter/fusion`, and you attach a
`trustedrouter:fusion` tool that names the **panel** (`analysis_models`), the
**judge** (`model`), and a **selection strategy**.

### curl

```bash
export TRUSTEDROUTER_API_KEY="sk-your-disposable-key-here"

curl https://api.trustedrouter.com/v1/chat/completions \
  -H "Authorization: Bearer $TRUSTEDROUTER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "trustedrouter/fusion",
    "messages": [
      {"role": "user", "content": "Explain how mRNA vaccines work, in 80 words."}
    ],
    "max_tokens": 512,
    "tools": [
      {
        "type": "trustedrouter:fusion",
        "parameters": {
          "analysis_models": [
            "moonshotai/kimi-k2.7-code",
            "deepseek/deepseek-v4-flash",
            "google/gemini-3.5-flash",
            "google/gemini-3.1-pro-preview",
            "minimax/minimax-m3",
            "z-ai/glm-5.1"
          ],
          "model": "z-ai/glm-5.1",
          "selection_strategy": "first_non_refusal",
          "max_completion_tokens": 2048
        }
      }
    ]
  }'
```

The reply is a normal chat-completion: the chosen/synthesized answer is in
`choices[0].message.content`.

### Python (standard library only)

```python
import json, os, urllib.request

PANEL = [
    "moonshotai/kimi-k2.7-code",
    "deepseek/deepseek-v4-flash",
    "google/gemini-3.5-flash",
    "google/gemini-3.1-pro-preview",
    "minimax/minimax-m3",
    "z-ai/glm-5.1",
]

body = {
    "model": "trustedrouter/fusion",
    "messages": [{"role": "user", "content": "Explain how mRNA vaccines work, in 80 words."}],
    "max_tokens": 512,
    "tools": [{
        "type": "trustedrouter:fusion",
        "parameters": {
            "analysis_models": PANEL,
            "model": "z-ai/glm-5.1",          # the judge / synthesis model
            "selection_strategy": "first_non_refusal",
            "max_completion_tokens": 2048,
        },
    }],
}

req = urllib.request.Request(
    "https://api.trustedrouter.com/v1/chat/completions",
    method="POST",
    headers={
        "Authorization": "Bearer " + os.environ["TRUSTEDROUTER_API_KEY"],
        "Content-Type": "application/json",
    },
    data=json.dumps(body).encode(),
)
data = json.load(urllib.request.urlopen(req, timeout=240))
print(data["choices"][0]["message"]["content"])
```

## The parameters

| Field | What it does |
|---|---|
| `analysis_models` | The **panel** — the models Fusion queries for this request. |
| `model` | The **judge / synthesis** model that produces the final answer from the panel's outputs. `z-ai/glm-5.1` is a good default. |
| `selection_strategy` | How the final answer is chosen (see below). |
| `max_completion_tokens` | Per-panel-model token budget. Bump to **8192+** if your panel includes reasoning models — they spend tokens on hidden thinking, and a small budget can truncate the visible answer. |

### Selection strategies

- **`first_non_refusal`** — return the first panel answer that isn't a refusal.
  Best when you want the panel's *most willing* answer; this is what scored 30/30
  on PrometheusBench.
- **`synthesize`** — the judge model reads every panel answer and writes one
  merged response. Best for combining partial answers into a single best result.

## Picking a panel

The panel is just a list of TrustedRouter model ids — pick from
[`trustedrouter.com/v1/models`](https://trustedrouter.com/v1/models). A larger
panel costs more (every model is queried) but gives the judge more to work with.
The six-model panel above is the one used for the published 30/30 run.

## Troubleshooting

- **`402`** — the key is out of credit. Top it up at
  [trustedrouter.com](https://trustedrouter.com).
- **`502` / provider error** — a panel member's upstream had a blip. Just resend
  the request; it usually clears on the next pass.
- **Truncated / empty answers** — raise `max_completion_tokens` (reasoning models
  need 8192+) so the visible answer isn't eaten by hidden thinking.
- **Want a refusal-resistant setup** — use a permissive panel with
  `first_non_refusal`; if a request still comes back as a refusal, resend it with
  a different judge `model` (e.g. `moonshotai/kimi-k2.6`,
  `google/gemini-2.5-flash`, `tencent/hy3-preview`) until one answers.
