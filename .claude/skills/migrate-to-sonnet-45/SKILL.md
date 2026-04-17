---
name: migrate-to-sonnet-45
description: Guide migration to Claude Sonnet 4.5. Use when migrating from Sonnet 4 or Sonnet 3.7 to Sonnet 4.5. Covers model ID changes, sampling parameters, tool versions, new stop reasons, trailing newlines, rate limits, pricing, prompt adaptation, extended thinking, and evaluation/rollout.
target-model: claude-sonnet-4-5-20250929
source-models:
  - claude-sonnet-4-20250514
  - claude-3-7-sonnet-20250219
---

# Claude Sonnet 4.5 Migration

A skill for guiding customers through migration to Claude Sonnet 4.5 with minimal friction.

Prompt migration is the highest friction point for adopting new models. Cross-generation jumps (e.g., Sonnet 3.7 to 4.5) are the hardest because model behavior changes significantly and requires prompting and harness changes. Prompts optimized for one model version may not perform well on another, so prompt updates are a required part of any migration — not optional.

## The 12 migration items

Migrating to Sonnet 4.5 requires reviewing **12 items**. Each item is tagged by:
- **Severity:** 🔴 Required (code breaks without it) | 🟡 Operational (impacts cost, limits, or availability) | 🟢 Quality (improves output) | 🔵 Verification (confirms readiness)
- **Scope:** `API` = code/infrastructure change | `Prompt` = prompt/behavior change | both when applicable

---

### Item 1: Model ID 🔴 `API`

Update the model identifier in all API calls.

```python
model = "claude-sonnet-4-20250514"       # Before (Sonnet 4)
model = "claude-3-7-sonnet-20250219"     # Before (Sonnet 3.7)
model = "claude-sonnet-4-5-20250929"     # After
```

On Vertex AI or Bedrock the model ID format differs (e.g. `claude-sonnet-4-5@20250929` on Vertex). See `references/platform-ids.md` for the correct ID per backend, and never change the client class.

---

### Item 2: Sampling Parameters 🔴 `API`

Use only `temperature` **OR** `top_p`, not both. Using both returns an error on Claude 4+ models.

```python
# Before — this will ERROR on Sonnet 4.5
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    temperature=0.7,
    top_p=0.9,  # Cannot use both
    ...
)

# After
response = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    temperature=0.7,  # Use temperature OR top_p, not both
    ...
)
```

Note: If migrating from Sonnet 4, this restriction already applies. If migrating from Sonnet 3.7, this is a new breaking change.

---

### Item 3: Tool Versions 🔴 `API`

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

### Item 4: `refusal` Stop Reason 🔴 `API`

Claude 4+ models return `stop_reason: "refusal"` when declining a request. Applications must handle this new stop reason.

```python
if response.stop_reason == "refusal":
    # New in Claude 4+ — handle appropriately
    pass
```

---

### Item 5: `model_context_window_exceeded` Stop Reason 🔴 `API`

Claude 4.5+ models return `model_context_window_exceeded` when generation stops because the context window is full. This is distinct from `max_tokens`, which still fires when the user-set output limit is reached.

```python
if response.stop_reason == "model_context_window_exceeded":
    # Context window exhausted — different from max_tokens
    pass
```

Update application logic to handle both stop reasons.

---

### Item 6: Trailing Newlines 🔴 `API`

Claude 4.5+ preserves trailing newlines in tool call string parameters that were previously stripped. If tools rely on exact string matching, verify the logic handles trailing newlines correctly.

---

### Item 7: Rate Limits 🟡 `API`

Sonnet 4.5 has **separate** rate limits from Sonnet 4 and Sonnet 3.7. Review the new limits with the customer and adjust application throttling if needed.

---

### Item 8: Pricing 🟡 `API`

Sonnet 4.5 pricing:

| | Input (per M tokens) | Output (per M tokens) |
|---|---|---|
| Sonnet 3.7 | $3.00 | $15.00 |
| Sonnet 4 | $3.00 | $15.00 |
| Sonnet 4.5 | $3.00 | $15.00 |

Pricing remains the same across Sonnet generations. No cost impact for this migration.

---

### Item 9: Regional Availability 🟡 `API`

Confirm target model availability in the customer's required region before starting migration.

- Verify Sonnet 4.5 availability in the customer's deployment region
- Check with your Anthropic account team for regional enablement if needed
- Public documentation may not list all available regions

---

### Item 10: Explicit & Action-Oriented Prompting 🟢 `Prompt`

Sonnet 4.5 follows instructions more literally than previous versions. "Can you suggest changes" means it will only suggest, not implement. Use action-oriented language.

```python
# Before (Sonnet 4 / 3.7 — model inferred intent)
system = "Help the user with code changes."

# After (Sonnet 4.5 — be explicit about desired action)
system = "Implement code changes directly. Do not just suggest — make the actual edits."
```

Sonnet 4.5 is also more terse by default and skips summaries after tool calls. If visibility is needed:
```
After completing a task that involves tool use, provide a quick summary of the work you've done.
```

---

### Item 11: Tool Use Prompt Adjustments 🟢 `Prompt`

Sonnet 4.5 may **undertrigger tools** — abstains from using them unless explicitly directed. Add proactive instructions:

```xml
<default_to_action>
By default, implement changes rather than only suggesting them.
If the user's intent is unclear, infer the most useful likely action
and proceed, using tools to discover any missing details.
</default_to_action>
```

Sonnet 4.5 also excels at parallel tool calling. Enable with:
```xml
<use_parallel_tool_calls>
If you intend to call multiple tools and there are no dependencies
between the tool calls, make all of the independent tool calls in parallel.
</use_parallel_tool_calls>
```

---

### Item 12: Chain-of-Thought Removal 🟢 `Prompt`

Sonnet 4.5 naturally uses chain-of-thought in its internal thinking. Remove explicit "think step by step" instructions — they waste tokens without improving quality.

```
# REMOVE (unnecessary on Sonnet 4.5):
"Think step by step."
"Let's reason through this carefully."
"Break down the problem into parts."
```

---

### Item 13: Claudeisms Mitigation 🟢 `Prompt`

Sonnet 4.5 may exhibit more "Claudeisms": first-person defaults, sycophantic responses, unnecessary clarifying questions.

```
# Add to system prompt if these behaviors are problematic:
Do not use first-person language. Do not apologize.
Do not ask clarifying questions unless absolutely necessary —
work with the information provided.
```

---

### Item 14: Extended Thinking 🟢 `API` `Prompt`
### Item 15: Evaluation & Rollout 🔵 `API` `Prompt`

**Evaluate:**
1. Capture baseline results on the source model (if not already done)
2. Run the same evaluation suite on Sonnet 4.5 with updated prompts
3. Compare on: accuracy, latency, cost, format adherence
4. Iterate on prompts until parity or improvement on key metrics

**Roll out:**
1. Start with canary deployment (small percentage of traffic)
2. Monitor production metrics for regressions
3. Gradually increase traffic to Sonnet 4.5
4. Keep the source model as fallback until confident

---

## Applying the 15 items: migration phases

The items above map to five sequential phases:

| Phase | Items | What happens |
|-------|-------|-------------|
| **1. Scope** | 8, 9 | Assess pricing impact, confirm regional availability, set expectations |
| **2. Infrastructure** | 1, 2, 3, 6 | Apply mandatory code changes |
| **3. Error handling** | 4, 5, 7 | Handle new stop reasons, adjust for new rate limits |
| **4. Prompts** | 10, 11, 12, 13, 14 | Adapt prompts, enable extended thinking |
| **5. Verify** | 15 | Evaluate and roll out |

## Customer-shareable resources

- [Migration Guide](https://platform.claude.com/docs/en/about-claude/models/migration-guide) — official step-by-step with checklists
- [Prompting Best Practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices) — covers latest Claude models
- **Prompt Improver** in Console — auto-refactors prompts, free, 1-2 min
