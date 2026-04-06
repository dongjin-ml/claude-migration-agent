---
name: migrate-to-haiku-45
description: Guide migration to Claude Haiku 4.5. Use when migrating from Haiku 3 or Haiku 3.5 to Haiku 4.5. Covers model ID changes, sampling parameters, tool versions, new stop reasons, trailing newlines, rate limits, pricing, regional availability, prompt adaptation, extended thinking, and evaluation/rollout.
target-model: claude-haiku-4-5-20251001
source-models:
  - claude-3-haiku-20240307
  - claude-3-5-haiku-20241022
---

# Claude Model Migration

A skill for guiding customers through Claude model migrations with minimal friction.

Prompt migration is recognized internally as the "highest friction point for adopting new models." Cross-generation jumps (e.g., Haiku 3 to 4.5) are the hardest because model behavior changes significantly and requires prompting and harness changes. Prompts optimized for one model version may not perform well on another, so prompt updates are a required part of any migration — not optional.

## The 12 migration items

Migrating from Haiku 3 to Haiku 4.5 requires reviewing **12 items**. Each item is tagged by:
- **Severity:** 🔴 Required (code breaks without it) | 🟡 Operational (impacts cost, limits, or availability) | 🟢 Quality (improves output) | 🔵 Verification (confirms readiness)
- **Scope:** `API` = code/infrastructure change | `Prompt` = prompt/behavior change | both when applicable

---

### Item 1: Model ID 🔴 `API`

Update the model identifier in all API calls.

```python
model = "claude-3-haiku-20240307"      # Before
model = "claude-haiku-4-5-20251001"    # After
```

Also note the intermediate version if relevant:
- Haiku 3.5: `claude-3-5-haiku-20241022`

---

### Item 2: Sampling Parameters 🔴 `API`

Use only `temperature` **OR** `top_p`, not both. Using both returns an error on Claude 4+ models.

```python
# Before — this will ERROR on Haiku 4.5
response = client.messages.create(
    model="claude-3-haiku-20240307",
    temperature=0.7,
    top_p=0.9,  # Cannot use both
    ...
)

# After
response = client.messages.create(
    model="claude-haiku-4-5-20251001",
    temperature=0.7,  # Use temperature OR top_p, not both
    ...
)
```

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

Haiku 4.5 has **separate** rate limits from Haiku 3 and 3.5. Review the new limits with the customer and adjust application throttling if needed.

---

### Item 8: Pricing 🟡 `API`

Haiku 4.5 is a 4x price increase. Factor this into cost analysis for high-volume workloads.

| | Input (per M tokens) | Output (per M tokens) |
|---|---|---|
| Haiku 3 | $0.25 | $1.25 |
| Haiku 4.5 | $1.00 | $5.00 |

---

### Item 9: Regional Availability 🟡 `API`

Confirm target model availability in the customer's required region before starting migration.

- Haiku 4.5 in asia-southeast1 (Singapore): **available as regional enablement** — requires enablement
- Public documentation only lists global endpoints, which causes confusion for FSI customers
- Coordinate with your Anthropic account team for enablement

Read `references/regional-availability.md` for verification process and FSI considerations.

---

### Item 10: Explicit Prompting 🟢 `Prompt`

Haiku 4.5 is more concise by default and needs **more explicit prompting** than Sonnet in the same generation. Don't assume implicit understanding — spell out desired output format, constraints, and behavior.

```python
# Before (Haiku 3 — vague, implicit)
system = "You are a document analyzer. Summarize the key points."

# After (Haiku 4.5 — explicit format, constraints, behavior)
system = (
    "You are a document analyzer. "
    "Summarize the key points in detail, using bullet points. "
    "Do not skip any major section. "
    "Do not ask clarifying questions — work with the document as provided. "
    "Return your full analysis without abbreviation."
)
```

Haiku 4.5 may skip summaries after tool calls. If the customer needs visibility:
```
After completing a task that involves tool use, provide a quick summary of the work you've done.
```

**Data point for customer pushback:** The same prompting technique can produce +24 points on one model and -25 points on another. The fair way to compare models is by optimizing prompts for each model version separately.

Read `references/prompting-tips.md` for ready-to-use prompt snippets.

---

### Item 11: Claudeisms Mitigation 🟢 `Prompt`

Haiku 4.5 may exhibit more "Claudeisms": first-person defaults, sycophantic responses, unnecessary clarifying questions, and excessive apologies.

```python
# Before (Haiku 3 — no mitigation needed)
system = "You are a helpful assistant."

# After (Haiku 4.5 — suppress Claudeisms)
system = (
    "You are a helpful assistant. "
    "Respond in third person unless the user requests otherwise. "
    "Do not apologize unnecessarily. "
    "Do not ask clarifying questions unless the request is truly ambiguous. "
    "Be direct and factual."
)
```

---

### Item 12: Tool Use Prompt Adjustments 🟢 `Prompt`

Haiku 4.5 tool usage patterns change from Haiku 3. May need more encouragement to use tools, or may over-trigger.

```python
# Before (Haiku 3 — implicit, suggestive)
system = "Can you suggest changes to improve the code?"

# After (Haiku 4.5 — explicit action)
system = "Implement changes to improve the code. Use tools to read files and apply edits directly."
```

---

### Item 13: Extended Thinking 🟢 `API` `Prompt`
### Item 14: Evaluation & Rollout 🔵 `API` `Prompt`

**Evaluate:**
1. Capture baseline results on Haiku 3 (if not already done)
2. Run the same evaluation suite on Haiku 4.5 with updated prompts
3. Compare on: accuracy, latency, cost, format adherence
4. Iterate on prompts until parity or improvement on key metrics

**Roll out:**
1. Start with canary deployment (small percentage of traffic)
2. Monitor production metrics for regressions
3. Gradually increase traffic to Haiku 4.5
4. Keep Haiku 3 as fallback until confident

---

## Applying the 14 items: migration phases

The items above map to five sequential phases:

| Phase | Items | What happens |
|-------|-------|-------------|
| **1. Scope** | 8, 9 | Assess pricing impact, confirm regional availability, set expectations |
| **2. Infrastructure** | 1, 2, 3, 6 | Apply mandatory code changes |
| **3. Error handling** | 4, 5, 7 | Handle new stop reasons, adjust for new rate limits |
| **4. Prompts** | 10, 11, 12, 13 | Explicit prompting, Claudeisms, tool use, extended thinking |
| **5. Verify** | 14 | Evaluate and roll out |

## Customer deliverables

When delivering migration results to a customer, prepare three artifacts:

1. **Prompt Review PDF** — each change highlighted with a "why" explanation
2. **Side-by-side comparison** using `<ORIGINAL>` / `<CHANGED>` tags
3. **raw_prompt.txt** — final prompt ready for copy-paste into production

## Customer-shareable resources

- [Migration Guide](https://platform.claude.com/docs/en/about-claude/models/migration-guide) — official step-by-step with checklists
- [Prompting Best Practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices) — covers Opus 4.6, Sonnet 4.6, Haiku 4.5
- **Prompt Improver** in Console — auto-refactors prompts, free, 1-2 min