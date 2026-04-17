---
name: migrate-to-opus-47
description: Guide migration to Claude Opus 4.7. Use when migrating from Opus 4.6 or Opus 4.5 to Opus 4.7. Covers extended-thinking removal, sampling-parameter removal, thinking-display default change, tokenization update, the new xhigh effort level, task budgets, high-resolution images, and prompt migration for the more-literal / lower-tool-use behavior.
target-model: claude-opus-4-7
source-models:
  - claude-opus-4-6
  - claude-opus-4-5-20251101
---

# Claude Opus 4.7 Migration

A skill for guiding customers through migration to Claude Opus 4.7.

Opus 4.7 is the most autonomous Claude to date, optimized for long-horizon agentic work, knowledge work, vision, and memory. It carries forward all 4.6-generation breaking changes and adds new ones: extended thinking (`budget_tokens`) and all sampling parameters now return 400, thinking content is omitted by default, and a new tokenizer increases token counts by up to ~35%. Several behavioral defaults **reverse direction** from Opus 4.6 — fewer subagents, fewer tool calls, built-in progress updates — so prompt scaffolding added for 4.6 may now need to be removed.

Prompt migration is the highest-friction part of any model upgrade. The same prompt technique can yield +24 points on one model and -25 points on another. Prompts must be adapted to the TARGET model's specific behavior.

## Migration items

Migrating to Opus 4.7 requires reviewing **24 items**. Each item is tagged by:
- **Severity:** [Required] (code breaks without it) | [Operational] (impacts cost, limits, or availability) | [Quality] (improves output) | [Verification] (confirms readiness)
- **Scope:** `API` = code/infrastructure change | `Prompt` = prompt/behavior change | both when applicable
- **Applies to:** Which source models are affected

---

### Item 1: Model ID [Required] `API` | All sources

Update the model identifier in all API calls.

```python
model = "claude-opus-4-6"            # Before (from Opus 4.6)
model = "claude-opus-4-5-20251101"   # Before (from Opus 4.5)
model = "claude-opus-4-7"            # After
```

On Vertex AI or Bedrock the alias does not apply — use the dated snapshot (e.g. `claude-opus-4-7@<YYYYMMDD>` on Vertex). See `references/platform-ids.md` for the correct ID per backend, and never change the client class.

---

### Item 2: Extended Thinking Removed [Required] `API` | All sources

`thinking: {type: "enabled", budget_tokens: N}` returns a **400 error** on Opus 4.7. The transitional escape hatch that existed on Opus 4.6 is gone — adaptive thinking is the only on-mode.

```python
# Before -- this will ERROR on Opus 4.7
response = client.messages.create(
    model="claude-opus-4-7",
    thinking={"type": "enabled", "budget_tokens": 32000},  # WILL FAIL
    ...
)

# After
response = client.messages.create(
    model="claude-opus-4-7",
    thinking={"type": "adaptive"},
    output_config={"effort": "high"},  # or "xhigh", "max", "medium", "low"
    ...
)
```

Adaptive thinking is **off by default** — omitting `thinking` runs without reasoning, matching Opus 4.6 behavior. Set it explicitly to enable.

---

### Item 3: Sampling Parameters Removed [Required] `API` | All sources

Setting `temperature`, `top_p`, or `top_k` to **any non-default value** returns a 400 error on Opus 4.7. This is stricter than Opus 4.6 (which allowed one of `temperature`/`top_p`). The safest fix is to delete these parameters entirely.

```python
# Before -- this will ERROR on Opus 4.7
response = client.messages.create(
    model="claude-opus-4-7",
    temperature=0.7,  # WILL FAIL — even alone
    ...
)

# After — remove sampling params entirely; steer behavior via prompting
response = client.messages.create(
    model="claude-opus-4-7",
    ...
)
```

If `temperature=0` was used for determinism, note it never guaranteed identical outputs on prior models either.

---

### Item 4: Prefill Removal [Required] `API` `Prompt` | All sources

Carried over from Opus 4.6: prefilling assistant messages returns a **400 error**.

```python
# Before -- this will ERROR on Opus 4.7
messages=[
    {"role": "user", "content": "Analyze this data"},
    {"role": "assistant", "content": "{\"analysis\":"}  # WILL FAIL
]

# After -- use structured outputs instead
response = client.messages.create(
    model="claude-opus-4-7",
    messages=[{"role": "user", "content": "Analyze this data"}],
    output_config={"format": {"type": "json_schema", "schema": my_schema}},
)
```

| Prefill use case | Replacement on Opus 4.7 |
|---|---|
| Force JSON output | `output_config.format` with JSON schema |
| Skip preamble | System prompt: "Respond directly without preamble" |
| Continue truncated response | User turn: "Your previous response ended with [X]. Continue." |
| Context hydration | Inject reminders into user turns |

---

### Item 5: Thinking Display Omitted by Default [Required] `API` | All sources

**Silent change — no error.** Thinking blocks still stream, but their `thinking` text is empty unless you opt in. The Opus 4.6 default was `"summarized"`; the Opus 4.7 default is `"omitted"`. UIs that stream reasoning will appear to hang before output begins.

```python
# After — restore visible reasoning
thinking={"type": "adaptive", "display": "summarized"}
```

Scan for any code that reads `block.thinking` or renders thinking deltas to a UI.

---

### Item 6: Tool Parameter JSON Escaping [Required] `API` | All sources

Carried over from 4.6: tool-call `input` JSON escaping may differ (Unicode, forward-slash). Always parse with `json.loads()` / `JSON.parse()`; never raw-string-match the serialized input.

---

### Item 7: Updated Tokenization [Operational] `API` | All sources

Opus 4.7 uses a new tokenizer. The same text produces **1x–1.35x as many tokens** vs prior models (varies by content). `count_tokens` returns different numbers for 4.7 vs 4.6.

- Re-tune `max_tokens` and any compaction triggers to give headroom.
- Re-benchmark end-to-end cost and latency.
- The 1M context window is at standard pricing (no long-context premium), which offsets some of the increase.

---

### Item 8: Audit Client-Side Token Estimation [Operational] `API` | All sources

Any code that estimates tokens locally or assumes a fixed token-to-character ratio must be re-tested against Opus 4.7. Use the `/v1/messages/count_tokens` endpoint to verify.

---

### Item 9: Pricing & Rate Limits [Operational] `API` | All sources

| Model | Input (per M tokens) | Output (per M tokens) |
|---|---|---|
| Opus 4.7 | $5.00 | $25.00 |

Same per-token price as Opus 4.6, but the tokenization change (Item 7) means the same text costs more. Opus 4.7 has separate rate limits from 4.6/4.5 — review and adjust throttling.

---

### Item 10: New `xhigh` Effort Level [Quality] `API` | All sources

Opus 4.7 adds `"xhigh"` between `"high"` and `"max"`. Effort matters more on 4.7 than on any prior Opus — re-tune it.

| Workload | Recommended effort |
|---|---|
| Coding / agentic (recommended default) | `xhigh` |
| Intelligence-sensitive (minimum) | `high` |
| Maximum reasoning depth | `max` (may overthink) |
| Subagents / simple tasks | `low` |

When using `xhigh` or `max`, start `max_tokens` at **64k** to give the model room.

---

### Item 11: Task Budgets (beta) [Quality] `API` | All sources

New on Opus 4.7: an advisory token budget for a full agentic loop. The model sees a running countdown and self-moderates. Distinct from `max_tokens` (a hard per-response cap the model cannot see).

```python
response = client.messages.create(
    model="claude-opus-4-7",
    extra_headers={"anthropic-beta": "task-budgets-2026-03-13"},
    output_config={
        "effort": "high",
        "task_budget": {"type": "tokens", "total": 128000},
    },
    ...
)
```

Minimum `total` is 20,000.

---

### Item 12: High-Resolution Image Support [Quality] `API` | All sources

Opus 4.7 accepts images up to **2576px** on the long edge (up from 1568px). Full-resolution images use up to ~3x more image tokens.

- If the extra fidelity is unnecessary, **downsample before sending** to control cost.
- Pointing / bounding-box coordinates returned by the model are now **1:1 with image pixels** — remove any scale-factor conversion code.

---

### Item 13: Remove Legacy Beta Headers [Quality] `API` | All sources

Effort and interleaved thinking are GA. Remove:
- `effort-2025-11-24`
- `interleaved-thinking-2025-05-14`
- `fine-grained-tool-streaming-2025-05-14`
- `token-efficient-tools-2025-02-19`, `output-128k-2025-02-19` (if migrating from 4.1 or earlier)

---

### Item 14: Migrate `output_format` → `output_config.format` [Quality] `API` | From Opus 4.5

```python
# Before
output_format={"type": "json_schema", "schema": my_schema}

# After
output_config={"format": {"type": "json_schema", "schema": my_schema}}
```

---

### Item 15: Response Length Re-baseline [Quality] `Prompt` | All sources

Opus 4.7 calibrates response length to task complexity instead of a fixed verbosity — shorter on lookups, much longer on open-ended analysis.

```
# Before (length-control scaffolding) — remove first, then re-tune
Keep responses under 200 words. Be extremely concise.

# After — remove length-control prompts, re-baseline, then add explicit
# guidance only where the new default doesn't fit:
For chat replies, target 2-3 sentences. For analysis tasks, be comprehensive.
```

---

### Item 16: More Literal Instruction Following [Quality] `Prompt` | All sources

Opus 4.7 interprets prompts more literally than 4.6, especially at lower effort. It will not generalize an instruction from one item to another or infer unstated requests.

```
# Before — relied on the model inferring scope
Fix the bug in auth.py.

# After — state the full intent explicitly if you want it
Fix the bug in auth.py. Also check whether the same pattern appears
in the other handlers and fix those too.
```

Review prompts for implicit assumptions. This is good for structured extraction and tuned pipelines; harmful if prompts relied on generous inference.

---

### Item 17: More Direct Tone [Quality] `Prompt` | All sources

Opus 4.7 is more direct and opinionated, with less validation-forward phrasing and fewer emoji than 4.6's warmer style. If the product depends on a specific voice, re-evaluate style prompts against the new baseline.

---

### Item 18: Remove Forced Progress-Update Scaffolding [Quality] `Prompt` | All sources

Opus 4.7 provides regular, high-quality progress updates throughout long agentic traces **by default**. Scaffolding added for earlier models is now redundant and may cause over-reporting.

```
# Before (scaffolding from earlier models) — REMOVE
After every 3 tool calls, summarize progress for the user.

# After — let the default work; only add guidance if updates are
# mis-calibrated for your use case, e.g.:
Provide a progress update only when you complete a major phase.
```

---

### Item 19: Subagent Guidance — Direction Reverses [Quality] `Prompt` | All sources

Opus 4.7 spawns **fewer** subagents by default — the opposite of Opus 4.6. If the customer added subagent-limiting guardrails for 4.6, remove them. If the workload benefits from parallelism, add explicit encouragement instead.

```
# Before (4.6-era guardrail) — REMOVE for 4.7
For simple tasks, work directly rather than delegating to subagents.

# After (only if more parallelism is desired)
For independent research questions, spawn parallel subagents to investigate
each one concurrently.
```

---

### Item 20: Stricter Effort Calibration [Quality] `Prompt` `API` | All sources

Opus 4.7 respects effort levels strictly. At `low`/`medium` it scopes work to exactly what was asked rather than going above and beyond. If shallow reasoning appears on complex problems, **raise `effort` to `high` or `xhigh`** rather than prompting around it.

If `low` must be kept for latency, add targeted guidance:
```
This task involves multi-step reasoning. Think carefully through the
problem before responding.
```

---

### Item 21: Tool-Call Guidance — Direction Reverses [Quality] `Prompt` `API` | All sources

Opus 4.7 uses tools **less often** than 4.6 and reasons more — the opposite of 4.6's overtriggering. If the customer softened tool language for 4.6, that softening may now cause under-use.

- First lever: raise `effort` to `high` or `xhigh` — tool usage increases substantially.
- Second lever: add explicit guidance about when tools are required.

```
# Before (4.6-era softening) — may now under-trigger
Use the search tool only when the question requires specific data.

# After (if under-triggering is observed)
For any question about current data, use the search tool before answering.
```

---

### Item 22: Cyber Safeguards [Operational] `Prompt` | All sources

New in Opus 4.7: requests touching prohibited or high-risk security topics may be refused. For legitimate security work (penetration testing, vulnerability research, red-teaming), apply to the Cyber Verification Program at https://claude.com/form/cyber-use-case for reduced restrictions. Flag this to security-domain customers up front.

---

### Item 23: Prompt Cache Minimum [Operational] `API` | All sources

The minimum cacheable prefix on Opus 4.7 is **4096 tokens** (same as Opus 4.6 / 4.5). Shorter prefixes silently won't cache — `cache_creation_input_tokens` stays 0 with no error.

---

### Item 24: Evaluation & Rollout [Verification] `API` `Prompt`

**Evaluate:**
1. Capture baseline results on the source model
2. Run the same evaluation suite on Opus 4.7 with updated prompts and re-tuned `effort`
3. Compare on: accuracy, latency, cost (account for tokenization change), format adherence
4. Pay special attention to: tool-call rates, subagent counts, response-length distribution

**Roll out:**
1. Start with canary deployment
2. Monitor for under-triggering of tools and shallow reasoning at low effort
3. Gradually increase traffic
4. Keep source model as fallback

---

## Migration phases

| Phase | Items | What happens |
|-------|-------|--------------|
| **1. Scope** | 7, 8, 9, 22, 23 | Tokenization re-benchmark, pricing/limits, cyber program, cache minimum |
| **2. Breaking changes** | 1, 2, 3, 4, 5, 6 | Model ID, extended thinking removed, sampling removed, prefill, thinking display, JSON escaping |
| **3. API updates** | 10, 11, 12, 13, 14 | xhigh effort, task budgets, hi-res images, beta-header cleanup, output_config.format |
| **4. Prompt migration** | 15-21 | Length re-baseline, literal following, tone, remove progress scaffolding, reverse subagent/tool guidance, effort calibration |
| **5. Verify** | 24 | Evaluate and roll out |

## Customer-shareable resources

- [Migration Guide](https://platform.claude.com/docs/en/about-claude/models/migration-guide) — official step-by-step with checklists
- [Prompting Best Practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)
- [Effort parameter](https://platform.claude.com/docs/en/build-with-claude/effort) — recommended levels for Opus 4.7
- [Task Budgets](https://platform.claude.com/docs/en/build-with-claude/task-budgets) — beta
- **Prompt Improver** in Console — use as a starting point, then apply Items 15-21
