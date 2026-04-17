---
name: migrate-to-sonnet-46
description: Guide migration to Claude Sonnet 4.6. Use when migrating from Sonnet 4.5 or Sonnet 4 to Sonnet 4.6. Covers prefill removal, adaptive thinking, effort parameter configuration, and system prompt simplification.
target-model: claude-sonnet-4-6
source-models:
  - claude-sonnet-4-5-20250929
  - claude-sonnet-4-20250514
---

# Claude Sonnet 4.6 Migration

A skill for guiding customers through migration to Claude Sonnet 4.6.

Sonnet 4.6 introduces several breaking changes at the API level and significant behavioral shifts in prompting. Customers migrating from Sonnet 4.5 face fewer breaking changes than those coming from Sonnet 4, but both paths require prompt adaptation.

## Migration items

Migrating to Sonnet 4.6 requires reviewing the following items. Each item is tagged by:
- **Severity:** [Required] Required (code breaks without it) | [Operational] Operational (impacts cost, limits, or availability) | [Quality] Quality (improves output) | [Verification] Verification (confirms readiness)
- **Scope:** `API` = code/infrastructure change | `Prompt` = prompt/behavior change | both when applicable
- **Source:** Which source models are affected

---

### Item 1: Model ID [Required] `API` | All sources

Update the model identifier in all API calls.

```python
model = "claude-sonnet-4-5-20250929"   # Before (from Sonnet 4.5)
model = "claude-sonnet-4-20250514"     # Before (from Sonnet 4)
model = "claude-sonnet-4-6"            # After
```

On Vertex AI or Bedrock the alias does not apply — use the dated snapshot (e.g. `claude-sonnet-4-6@<YYYYMMDD>` on Vertex). See `references/platform-ids.md` for the correct ID per backend, and never change the client class.

---

### Item 2: Prefill Removal [Required] `API` `Prompt` | All sources

Sonnet 4.6 **does not support prefilling assistant messages**. Sending a prefilled assistant turn returns a 400 error.

```python
# Before -- this will ERROR on Sonnet 4.6
messages = [
    {"role": "user", "content": "Summarize this document"},
    {"role": "assistant", "content": "{\"summary\":"}  # Prefill to force JSON
]

# After -- use structured outputs or direct instructions
response = client.messages.create(
    model="claude-sonnet-4-6",
    messages=[{"role": "user", "content": "Summarize this document"}],
    output_config={"format": {"type": "json_schema", "schema": summary_schema}},
)
```

**Five migration patterns for common prefill use cases:**

1. **Output formatting (JSON/YAML):** Use structured outputs via `output_config.format` or tools with enum fields.

2. **Eliminating preambles** ("Here is the summary..."):
```
# Before: prefill to skip preamble
messages = [{"role": "assistant", "content": "{\"result\": "}]

# After: direct instruction in system prompt
system = "Respond directly without preamble. Do not start with phrases like 'Here is...', 'Based on...', or 'Sure, I can...'."
```

3. **Avoiding bad refusals:** Claude 4.6 is much better at appropriate refusals. Clear prompting without prefill is sufficient.

4. **Continuations** (resuming interrupted responses):
```python
# Before: prefill with partial response
messages = [{"role": "assistant", "content": partial_response}]

# After: use a user-turn continuation
messages = [{"role": "user", "content": f"Your previous response was interrupted and ended with: '{partial_response[-200:]}'. Continue from where you left off."}]
```

5. **Context hydration / role consistency:** Inject previously prefilled assistant reminders into user turns instead.
```python
# Before: prefill to set context
messages = [{"role": "assistant", "content": "I understand I am acting as a medical expert."}]

# After: system prompt or user-turn instruction
system = "You are acting as a medical expert. Maintain this role throughout the conversation."
```

---

### Item 3: Tool Parameter JSON Escaping [Required] `API` | All sources

Sonnet 4.6 may produce different JSON escaping in tool call parameters. Always use standard JSON parsers (`json.loads()`, `JSON.parse()`) which handle this automatically. Do not rely on exact string matching of JSON output.

---

### Item 4: Sampling Parameters [Required] `API` | From Sonnet 4 only

Use only `temperature` **OR** `top_p`, not both. Using both returns an error on Claude 4+ models.

```python
# Before -- this will ERROR
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    temperature=0.7,
    top_p=0.9,  # Cannot use both
    ...
)

# After
response = client.messages.create(
    model="claude-sonnet-4-6",
    temperature=0.7,  # Use temperature OR top_p, not both
    ...
)
```

---

### Item 5: Tool Versions [Required] `API` | From Sonnet 4 only

Update to latest tool versions and remove deprecated commands.

```python
# Before
tools = [{"type": "text_editor_20250124", "name": "str_replace_editor"}]

# After
tools = [{"type": "text_editor_20250728", "name": "str_replace_based_edit_tool"}]
```

- Upgrade code execution to `code_execution_20250825` if used
- Remove any `undo_edit` command usage

---

### Item 6: `refusal` Stop Reason [Required] `API` | All sources

Claude 4+ models return `stop_reason: "refusal"` when declining a request. Applications must handle this new stop reason. Even if migrating from Sonnet 4.5, verify your application handles this stop reason gracefully.

```python
if response.stop_reason == "refusal":
    # Handle model declining the request
    pass
```

---

### Item 7: `model_context_window_exceeded` Stop Reason [Required] `API` | From Sonnet 4 only

Claude 4.5+ models return `model_context_window_exceeded` when generation stops because the context window is full. Distinct from `max_tokens`.

---

### Item 8: Trailing Newlines [Required] `API` | From Sonnet 4 only

Claude 4.5+ preserves trailing newlines in tool call string parameters that were previously stripped. Verify exact string matching logic.

---

### Item 9: Adaptive Thinking [Quality] `API` `Prompt` | All sources

Migrate from extended thinking (`budget_tokens`) to adaptive thinking.

```python
# Before (Sonnet 4.5) -- deprecated
thinking={"type": "enabled", "budget_tokens": 16384}

# After (Sonnet 4.6) -- model decides when and how much to think
thinking={"type": "adaptive"}
```

Extended thinking with `budget_tokens` is still supported but deprecated. Adaptive thinking lets the model decide when and how deeply to reason.

Sonnet 4.6 supports **64K max output tokens**.

---

### Item 10: Effort Parameter [Quality] `API` | All sources

Sonnet 4.6 defaults to `high` effort (Sonnet 4.5 had no default).

```python
# For similar-to-4.5 behavior without thinking:
output_config={"effort": "low"}

# For coding tasks:
output_config={"effort": "medium"}

# For chat/latency-sensitive:
output_config={"effort": "low"}
```

**Important:** `max` effort is Opus 4.6 only. Requests using `max` on Sonnet 4.6 (or other non-Opus models) will return an error. Higher effort can also cause camelCase parameter name switching in tool calls.

**Workload-specific effort recommendations:**

| Workload | Recommended effort |
|----------|-------------------|
| Autonomous multi-step agents | `high` |
| Computer use agents | adaptive (no effort override) |
| Bimodal workloads | adaptive |
| Coding / agentic | `medium` |
| Chat / non-coding | `low` |
| Latency-sensitive | `low` |

**Temporary migration pattern with budget_tokens:**

During migration, you can temporarily keep `budget_tokens` alongside the effort parameter for a smoother transition:

```python
# Transitional: coding/agentic with medium effort
thinking={"type": "enabled", "budget_tokens": 16384}
output_config={"effort": "medium"}

# Transitional: chat/non-coding with low effort
thinking={"type": "enabled", "budget_tokens": 16384}
output_config={"effort": "low"}

# Final target: fully adaptive (remove budget_tokens)
thinking={"type": "adaptive"}
```

---

### Item 11: Anti-Laziness Prompt Cleanup [Required] `Prompt` | All sources

Sonnet 4.6 is significantly more proactive than 4.5. Old anti-laziness prompts now cause **runaway thinking**, excessive token usage, and paradoxically worse output. This is the single biggest source of prompt migration regressions.

**Before (Sonnet 4.5 -- causes runaway thinking on 4.6):**
```
You MUST be thorough and comprehensive in your analysis.
Never skip any details or take shortcuts.
Think step by step through every aspect of the problem.
Make sure to check everything before responding.
Do not be lazy -- complete the entire task.
```

**After (Sonnet 4.6):**
```
Analyze the problem and provide your findings.
```

Sonnet 4.6's default behavior is already thorough. Adding thoroughness instructions makes it overthink, go back and forth between options, and waste tokens.

**Tool-specific anti-laziness is also harmful:**
```
# Before -- overtriggers on 4.6
CRITICAL: You MUST use this tool when analyzing code.
If in doubt, always use the search tool.

# After -- targeted guidance
Use this tool when analyzing unfamiliar code.
Use the search tool when you need context about specific functions.
```

---

### Item 12: System Prompt Simplification [Required] `Prompt` | All sources

Complex, rule-heavy system prompts degrade instruction following on Sonnet 4.6. Simpler system prompts produce better results.

**Before (Sonnet 4.5 -- causes instruction following regressions on 4.6):**
```
You are an assistant. Follow these rules:
1. NEVER use first person
2. NEVER apologize
3. NEVER ask clarifying questions
4. ALWAYS respond in exactly 3 paragraphs
5. DO NOT use bullet points
6. DO NOT use markdown headings
7. NEVER mention that you are an AI
8. ALWAYS cite sources
9. DO NOT speculate
10. NEVER use the word "I"
```

**After (Sonnet 4.6 -- same intent, fewer rules):**
```
You are a professional analyst. Write in third person using flowing prose paragraphs. Be direct and cite sources when available.
```

**Key principles:**
- Reduce rules to essential constraints only
- Frame as positive instructions ("write in third person") not prohibitions ("NEVER use first person")
- Use general intent over prescriptive checklists
- Test with minimal prompt first, add constraints only when needed

---

### Item 13: Tool Use Prompt Adjustments [Quality] `Prompt` | All sources

Sonnet 4.6 is more responsive to tool-use instructions. Aggressive language from Sonnet 4.5 prompts causes overtriggering.

**Before (Sonnet 4.5):**
```
CRITICAL: You MUST use the search tool before answering ANY question.
ALWAYS search first. If in doubt, search again.
```

**After (Sonnet 4.6):**
```
Use the search tool when you need context about specific topics or when the user's question requires current information.
```

**Additional tool use guidance:**
- Use explicit tool names (not vague references) for reliable triggering
- Lower effort for tool-heavy workflows to prevent camelCase parameter name switching
- Sonnet 4.6 has less initiative than Opus -- it makes narrow local fixes, not architectural improvements. If you need broader changes, give explicit architectural direction.

---

### Item 13b: Claudeisms Mitigation [Quality] `Prompt` | All sources

Sonnet 4.6 exhibits more "Claudeisms" than 4.5: defaulting to first-person voice, sycophantic responses, unnecessary clarifying questions, and excessive apologies. This has been a significant migration friction point (e.g., delayed OpenEvidence's migration).

**Add to system prompt if these behaviors appear:**
```
Do not default to first-person responses unless the task requires it.
Do not apologize or use sycophantic phrases ("Great question!", "Absolutely!").
Do not ask clarifying questions unless truly essential -- work with available information.
Be direct and professional.
```

---

### Item 14: Legacy Beta Headers [Quality] `API` | All sources

Remove deprecated beta headers that are now GA or removed:

- `effort-2025-11-24` (effort is now GA)
- `fine-grained-tool-streaming-2025-05-14` (now GA)
- `interleaved-thinking-2025-05-14` (remove)
- `token-efficient-tools-2025-02-19` (remove)
- `output-128k-2025-02-19` (remove)

---

### Item 15: Output Format Migration [Quality] `API` | All sources

Migrate `output_format` to `output_config.format`.

```python
# Before
output_format={"type": "json_schema", "schema": my_schema}

# After
output_config={"format": {"type": "json_schema", "schema": my_schema}}
```

---

### Item 16: Rate Limits [Operational] `API` | All sources

Sonnet 4.6 has **separate** rate limits from Sonnet 4.5 and Sonnet 4. Review the new limits and adjust application throttling if needed.

---

### Item 17: Pricing [Operational] `API` | All sources

Sonnet 4.6 pricing is the same as Sonnet 4.5.

| | Input (per M tokens) | Output (per M tokens) |
|---|---|---|
| Sonnet 4 | $3.00 | $15.00 |
| Sonnet 4.5 | $3.00 | $15.00 |
| Sonnet 4.6 | $3.00 | $15.00 |

---

### Item 18: Evaluation & Rollout [Verification] `API` `Prompt` | All sources

**Evaluate:**
1. Capture baseline results on the source model
2. Run the same evaluation suite on Sonnet 4.6 with updated prompts
3. Compare on: accuracy, latency, cost, format adherence
4. Pay special attention to prompt adaptation -- thoroughness prompts may cause regressions

**Roll out:**
1. Start with canary deployment (small percentage of traffic)
2. Monitor production metrics, especially token usage (effort parameter can increase costs)
3. Gradually increase traffic to Sonnet 4.6
4. Keep the source model as fallback until confident

---

## Migration phases

| Phase | Items | What happens |
|-------|-------|-------------|
| **1. Scope** | 16, 17 | Review rate limits and pricing |
| **2. Breaking changes** | 1, 2, 3, 6 | Model ID, prefill removal, JSON escaping, refusal stop reason |
| **3. From-Sonnet-4 only** | 4, 5, 7, 8 | Sampling params, tool versions, context window stop reason, trailing newlines |
| **4. Thinking & Effort** | 9, 10, 14, 15 | Adaptive thinking, effort parameter, remove beta headers, output format |
| **5. Prompts** | 11, 12, 13 | Remove anti-laziness, simplify system prompts, tool use adjustments |
| **6. Verify** | 18 | Evaluate and roll out |

## Customer-shareable resources

- [Migration Guide](https://platform.claude.com/docs/en/about-claude/models/migration-guide) -- official step-by-step with checklists
- [Prompting Best Practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices) -- covers Sonnet 4.6 specifically
- **Prompt Improver** in Console -- auto-refactors prompts, free, 1-2 min
