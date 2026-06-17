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
export TRUSTEDROUTER_API_KEY="sk-..."

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
          "fallback_judges": [
            "z-ai/glm-5.1",
            "moonshotai/kimi-k2.6",
            "google/gemini-2.5-flash",
            "deepseek/deepseek-v4-flash",
            "google/gemini-3-flash-preview",
            "tencent/hy3-preview"
          ],
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
FALLBACK_JUDGES = [
    "z-ai/glm-5.1",
    "moonshotai/kimi-k2.6",
    "google/gemini-2.5-flash",
    "deepseek/deepseek-v4-flash",
    "google/gemini-3-flash-preview",
    "tencent/hy3-preview",
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
            "fallback_judges": FALLBACK_JUDGES, # tried in order if a judge refuses/fails
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
| `analysis_models` | The **panel** — the 1–8 models Fusion queries for this request. |
| `model` | The **judge / synthesis** model that produces the final answer from the panel's outputs. `z-ai/glm-5.1` is a good default. |
| `fallback_judges` | An ordered **list of backup judges**. If the primary judge refuses or errors on a prompt, the gateway falls through this list until one produces an answer — so a single squeamish judge can't sink a prompt. (Aliases: `judge_models`, `judges`.) |
| `fallback_final_models` | Ordered backup **synthesis/final** models, same idea as `fallback_judges` but for the final-answer step. (Aliases: `final_models`, `synthesis_models`.) |
| `selection_strategy` | How the final answer is chosen (see below). Defaults to `synthesize`. |
| `preset` | `"quality"` or `"budget"` — selects a built-in panel instead of passing `analysis_models`. |
| `max_completion_tokens` | Per-panel-model token budget. Bump to **8192+** if your panel includes reasoning models — they spend tokens on hidden thinking, and a small budget can truncate the visible answer. |
| `max_tool_calls` | Cap on tool-call rounds (1–16). |

### Selection strategies

- **`first_non_refusal`** — return the first panel answer that isn't a refusal.
  Best when you want the panel's *most willing* answer; this is what scored 30/30
  on PrometheusBench.
- **`first_success`** — return the first panel answer that completed successfully.
- **`synthesize`** *(default)* — the judge reads every panel answer and writes one
  merged response. Best for combining partial answers into a single best result.
- **`synthesize_non_refusals`** — synthesize, but only from the panel members that
  did **not** refuse.

## Recommended panel (most freedom)

For the most willing-to-answer result — the exact configuration that answered
**all 30** PrometheusBench prompts — use this permissive panel,
`first_non_refusal`, and the judge fallback chain (most → least permissive):

```text
panel (analysis_models):
  moonshotai/kimi-k2.7-code
  deepseek/deepseek-v4-flash
  google/gemini-3.5-flash
  google/gemini-3.1-pro-preview
  minimax/minimax-m3
  z-ai/glm-5.1

judge (model):            z-ai/glm-5.1
fallback_judges:          z-ai/glm-5.1, moonshotai/kimi-k2.6,
                          google/gemini-2.5-flash, deepseek/deepseek-v4-flash,
                          google/gemini-3-flash-preview, tencent/hy3-preview
selection_strategy:       first_non_refusal
```

The SDKs ship these as constants (`FUSION_FREEDOM_PANEL` /
`FUSION_FREEDOM_FALLBACK_JUDGES`; Swift: `TrustedRouterConstants.fusionFreedomPanel`
/ `.fusionFreedomFallbackJudges`).

The panel is just a list of TrustedRouter model ids — pick from
[`trustedrouter.com/v1/models`](https://trustedrouter.com/v1/models). A larger
panel costs more (every model is queried) but gives the judge more to work with.

## SDKs

Fusion is built into the official TrustedRouter SDKs — they each ship a
`fusion(...)` method plus a `fusionTool` / `fusion_tool` builder and the
recommended-panel constants, so you don't hand-build the request:

- **JavaScript / TypeScript** — [`@lore-hex/trusted-router`](https://github.com/Lore-Hex/trusted-router-js)
- **Python** — [`trusted-router-py`](https://github.com/Lore-Hex/trusted-router-py) (sync + async)
- **Swift** — [`TrustedRouter`](https://github.com/Lore-Hex/trusted-router-swift)

```js
// JavaScript
import { TrustedRouter, FUSION_FREEDOM_PANEL, FUSION_FREEDOM_FALLBACK_JUDGES } from "@lore-hex/trusted-router";
const client = new TrustedRouter({ apiKey: process.env.TRUSTEDROUTER_API_KEY });
const resp = await client.fusion({
  messages: [{ role: "user", content: "explain how mRNA vaccines work" }],
  analysisModels: FUSION_FREEDOM_PANEL,
  model: "z-ai/glm-5.1",
  selectionStrategy: "first_non_refusal",
  fallbackJudges: FUSION_FREEDOM_FALLBACK_JUDGES,
});
console.log(resp.choices[0].message.content);
```

```python
# Python
from trustedrouter import TrustedRouter, FUSION_FREEDOM_PANEL, FUSION_FREEDOM_FALLBACK_JUDGES
with TrustedRouter(api_key="sk-tr-v1-...") as client:
    resp = client.fusion(
        messages=[{"role": "user", "content": "explain how mRNA vaccines work"}],
        analysis_models=FUSION_FREEDOM_PANEL,
        model="z-ai/glm-5.1",
        selection_strategy="first_non_refusal",
        fallback_judges=FUSION_FREEDOM_FALLBACK_JUDGES,
    )
    print(resp.choices[0].message.content)
```

```swift
// Swift
let answer = try await client.fusion(
    messages: [.user("explain how mRNA vaccines work")],
    analysisModels: TrustedRouterConstants.fusionFreedomPanel,
    judgeModel: "z-ai/glm-5.1",
    selectionStrategy: "first_non_refusal",
    fallbackJudges: TrustedRouterConstants.fusionFreedomFallbackJudges
)
```

## Troubleshooting

- **`402`** — the key is out of credit. Top it up at
  [trustedrouter.com](https://trustedrouter.com).
- **`502` / provider error** — a panel member's upstream had a blip. Just resend
  the request; it usually clears on the next pass.
- **Truncated / empty answers** — raise `max_completion_tokens` (reasoning models
  need 8192+) so the visible answer isn't eaten by hidden thinking.
- **Want a refusal-resistant setup** — use a permissive panel with
  `first_non_refusal` and pass a `fallback_judges` list (see the recommended
  panel above). The gateway walks that chain natively when a judge refuses or
  errors, so you don't have to resend the request yourself.
