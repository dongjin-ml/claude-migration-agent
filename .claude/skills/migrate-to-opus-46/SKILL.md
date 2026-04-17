---
name: migrate-to-opus-46
description: Guide migration to Claude Opus 4.6. Use when migrating from Opus 4.5 or Opus 4.1 to Opus 4.6. Covers prefill removal, adaptive thinking, tool triggering sensitivity, subagent delegation, and prompt migration.
target-model: claude-opus-4-6
source-models:
  - claude-opus-4-5-20251101
  - claude-opus-4-1-20250805
---

# Claude Opus 4.6 Migration

A skill for guiding customers through migration to Claude Opus 4.6.

Opus 4.6 is internally described as "dangerously agentic." It introduces 4.6-generation breaking changes shared with Sonnet 4.6, plus Opus-specific behavioral differences around tool triggering, subagent delegation, exploration depth, and overengineering. Customers coming from Opus 4.1 face additional breaking changes from the 4+ and 4.5+ generations.

Prompt migration is the highest-friction part of any model upgrade. The same prompt technique can yield +24 points on one model and -25 points on another. Prompts must be adapted to the TARGET model's specific behavior.

## Migration items

Migrating to Opus 4.6 requires reviewing **26 items**. Each item is tagged by:
- **Severity:** [Required] (code breaks without it) | [Operational] (impacts cost, limits, or availability) | [Quality] (improves output) | [Verification] (confirms readiness)
- **Scope:** `API` = code/infrastructure change | `Prompt` = prompt/behavior change | both when applicable
- **Applies to:** Which source models are affected

---

### Item 1: Model ID [Required] `API` | All sources

Update the model identifier in all API calls.

```python
model = "claude-opus-4-5-20251101"   # Before (from Opus 4.5)
model = "claude-opus-4-1-20250805"   # Before (from Opus 4.1)
model = "claude-opus-4-6"            # After
```

On Vertex AI or Bedrock the alias does not apply — use the dated snapshot (e.g. `claude-opus-4-6@<YYYYMMDD>` on Vertex). See `references/platform-ids.md` for the correct ID per backend, and never change the client class.

---

### Item 2: Prefill Removal [Required] `API` `Prompt` | All sources

Prefilling assistant messages returns a **400 error** on Opus 4.6.

```python
# Before -- this will ERROR on Opus 4.6
response = client.messages.create(
    model="claude-opus-4-6",
    messages=[
        {"role": "user", "content": "Analyze this data"},
        {"role": "assistant", "content": "{\"analysis\":"}  # WILL FAIL
    ],
)

# After -- use structured outputs instead
response = client.messages.create(
    model="claude-opus-4-6",
    messages=[{"role": "user", "content": "Analyze this data"}],
    output_config={"format": {"type": "json_schema", "schema": my_schema}},
)
```

**Five migration patterns for prefills:**

| Use case | Before (prefill) | After (Opus 4.6) |
|----------|-------------------|-------------------|
| Force JSON output | `{"role": "assistant", "content": "{"}` | Use `output_config.format` with JSON schema |
| Skip preamble | `{"role": "assistant", "content": "Here is..."}` | System prompt: "Respond directly without preamble" |
| Avoid bad refusal | Prefill to bypass refusal | Model handles refusals better now; prompt clearly |
| Continue response | Prefill with partial text | User turn: "Your previous response ended with [X]. Continue." |
| Context hydration | Prefill with role context | Inject reminders into user turns instead |

---

### Item 3: Tool Parameter JSON Escaping [Required] `API` | All sources

Tool parameter JSON escaping may differ in Opus 4.6. Always use standard JSON parsers (`json.loads()`, `JSON.parse()`) which handle this automatically.

---

### Item 4: Sampling Parameters [Required] `API` | From Opus 4.1 only

Use only `temperature` **OR** `top_p`, not both. Using both returns an error on Claude 4+ models.

```python
# Before -- this will ERROR
response = client.messages.create(
    model="claude-opus-4-1-20250805",
    temperature=0.7,
    top_p=0.9,  # Cannot use both on 4+
    ...
)

# After
response = client.messages.create(
    model="claude-opus-4-6",
    temperature=0.7,  # Use one or the other
    ...
)
```

---

### Item 5: Tool Versions [Required] `API` | From Opus 4.1 only

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

### Item 6: `refusal` Stop Reason [Required] `API` | From Opus 4.1 only

Claude 4+ models return `stop_reason: "refusal"` when declining a request. Handle this in application logic.

```python
if response.stop_reason == "refusal":
    # New in Claude 4+ -- handle gracefully
    pass
```

---

### Item 7: `model_context_window_exceeded` Stop Reason [Required] `API` | From Opus 4.1 only

Claude 4.5+ models return `model_context_window_exceeded` when the context window is full. Distinct from `max_tokens`.

---

### Item 8: Trailing Newlines [Required] `API` | From Opus 4.1 only

Claude 4.5+ preserves trailing newlines in tool call string parameters. Verify exact string matching logic.

---

### Item 9: Adaptive Thinking [Quality] `API` `Prompt` | All sources

Migrate from extended thinking (`budget_tokens`) to adaptive thinking. Extended thinking is deprecated in 4.6+.

```python
# Before (Opus 4.5)
response = client.messages.create(
    model="claude-opus-4-5-20251101",
    thinking={"type": "enabled", "budget_tokens": 16384},
    ...
)

# After (Opus 4.6)
response = client.messages.create(
    model="claude-opus-4-6",
    thinking={"type": "adaptive"},
    output_config={"effort": "high"},
    ...
)
```

**Note:** Manual thinking mode (`thinking.type: "enabled"` with `budget_tokens`) does NOT support interleaved thinking on Opus 4.6. Use adaptive mode if thinking interleaved with tool calls is needed.

---

### Item 10: Effort Parameter [Quality] `API` | All sources

The effort beta header is now GA. Remove the beta header and use the parameter directly.

```python
# Before (beta)
response = client.messages.create(
    model="claude-opus-4-5-20251101",
    extra_headers={"anthropic-beta": "effort-2025-11-24"},
    ...
)

# After (GA)
response = client.messages.create(
    model="claude-opus-4-6",
    output_config={"effort": "high"},  # max/high/medium/low
    ...
)
```

**`max` effort is exclusive to Opus 4.6.** Other models return an error when `max` is requested. Use `max` only for the most complex reasoning tasks. Warning: `max` can cause overthinking where the model oscillates between approaches until tokens are exhausted.

| Workload | Recommended effort |
|----------|---------|
| Most complex reasoning (Opus only) | `max` |
| Autonomous multi-step agents | `high` |
| Coding / agentic tasks | `medium` to `high` |
| Chat / non-coding | `low` to `medium` |
| Latency-sensitive | `low` |

---

### Item 11: Output Capacity [Quality] `API` | All sources

Opus 4.6 supports **128k max output tokens** (up from previous limits). For batch processing via the Message Batches API, up to **300k output tokens** are available using the `output-300k-2026-03-24` beta header.

---

### Item 12: Legacy Beta Headers Removal [Quality] `API` | All sources

Remove deprecated beta headers:
- `token-efficient-tools-2025-02-19` -- now default behavior
- `output-128k-2025-02-19` -- now default behavior
- `fine-grained-tool-streaming-2025-05-14` -- now GA
- `interleaved-thinking-2025-05-14` -- no longer needed

---

### Item 13: Migrate `output_format` to `output_config.format` [Quality] `API` | From Opus 4.5

```python
# Before
response = client.messages.create(
    output_format={"type": "json_schema", "schema": my_schema},
    ...
)

# After
response = client.messages.create(
    output_config={"format": {"type": "json_schema", "schema": my_schema}},
    ...
)
```

---

### Item 14: Anti-Laziness Prompt Removal [Required] `Prompt` | All sources

Opus 4.6 does significantly more upfront exploration than any previous model. Anti-laziness prompts that were necessary on 4.5 cause **runaway thinking and token exhaustion** on 4.6.

```
# Before (Opus 4.5) -- causes runaway exploration on 4.6
You must be extremely thorough. Check every file. Leave no stone unturned.
Never skip any details. Think step by step through every aspect.
Do not be lazy.

# After (Opus 4.6)
Focus on the most relevant files. Investigate further only if initial
findings are inconclusive.
```

---

### Item 15: Tool-Use Language Softening [Required] `Prompt` | All sources

Opus 4.6 is far more responsive to system prompts than previous versions. Aggressive tool language causes **overtriggering** -- e.g., triggering a docx tool just to draft an email.

```
# Before (Opus 4.5) -- overtriggers on 4.6
CRITICAL: You MUST use this tool for every task.
If in doubt, use the search tool before responding.
Always check the database before answering any question.

# After (Opus 4.6)
Use this tool when it would provide concrete value for the task.
Use the search tool when the question requires specific data.
Check the database for questions that require stored information.
```

Key: replace blanket defaults with targeted instructions.

Note: some specific tools may need MORE encouragement while general tool language needs LESS. Test per-tool behavior individually.

---

### Item 16: Subagent Delegation Guardrails [Required] `Prompt` | All sources

Opus 4.6 proactively spawns subagents -- sometimes 30+ at once. Without guidance, it over-delegates simple sequential tasks.

```
# Add to system prompt:
Use subagents when tasks can run in parallel, require isolated context,
or involve independent workstreams. For simple tasks, sequential operations,
single-file edits, or tasks where you need to maintain context across steps,
work directly rather than delegating.
```

---

### Item 17: Anti-Overthinking Prompt [Quality] `Prompt` | All sources

Opus 4.6 at higher effort levels can oscillate between two approaches until output tokens are exhausted.

```
# Add to system prompt:
When you're deciding how to approach a problem, choose an approach and commit
to it. Avoid revisiting decisions unless you encounter new information that
directly contradicts your reasoning. If you're weighing two approaches, pick
one and see it through.
```

---

### Item 18: Anti-Overengineering Prompt [Quality] `Prompt` | All sources

Opus 4.6 tends to create extra files, add unnecessary abstractions, and overengineer simple tasks (e.g., a one-function change becomes a multi-file refactor).

```
# Add to system prompt:
Avoid over-engineering. Only make changes that are directly requested
or clearly necessary. Keep solutions simple and focused:
- Scope: Don't add features, refactor code, or make "improvements" beyond what was asked.
- Documentation: Don't add docstrings, comments, or type annotations to code you didn't change.
- Defensive coding: Don't add error handling, fallbacks, or validation for scenarios that can't happen.
- Abstractions: Don't create helpers, utilities, or abstractions for one-time operations.
```

---

### Item 19: LaTeX Prevention [Quality] `Prompt` | All sources

Opus 4.6 defaults to LaTeX formatting for mathematical expressions. If plain text is preferred:

```
# Add to system prompt:
Format your response in plain text only. Do not use LaTeX, MathJax,
or any markup notation such as \( \), $, or \frac{}{}.
Write all math expressions using standard text characters.
```

---

### Item 20: Git Operation Guardrails [Quality] `Prompt` | All sources

Opus 4.6 is aggressive with git -- may force push, amend published commits, or delete branches without asking.

```
# Add to system prompt:
Always ask before committing, pushing, or performing destructive git operations.
Never force push or amend published commits.
Prefer creating new commits over amending existing ones.
```

---

### Item 21: Autonomy / Safety Guardrails [Quality] `Prompt` | All sources

Opus 4.6's high agency means it may take destructive actions autonomously.

```
# Add to system prompt:
Consider the reversibility and potential impact of your actions.
For destructive operations (deleting files, dropping tables, modifying
shared infrastructure), always confirm before proceeding.
```

---

### Item 22: Context Awareness for Compaction [Quality] `Prompt` | All sources

Self-compaction works less reliably on Opus 4.6 (reported by Gitpod/Ona). Long-running tasks may lose important state.

```
# Add to system prompt:
Your context window will be automatically compacted as it approaches its limit,
allowing you to continue working from where you left off. Write important state
to files rather than relying on conversation memory for long-running tasks.
```

---

### Item 23: Claudeisms Mitigation [Quality] `Prompt` | All sources

Opus 4.6 may exhibit "Claudeisms": defaulting to first-person voice, sycophantic responses, unnecessary clarifying questions, and excessive apologies.

```
# Add to system prompt if these behaviors are problematic:
Do not default to first-person responses unless the context requires it.
Avoid sycophantic language. Do not ask unnecessary clarifying questions
when you can reasonably infer the answer. Be direct and concise.
```

---

### Item 24: Rate Limits [Operational] `API` | All sources

Opus 4.6 has **separate** rate limits from Opus 4.5 and 4.1. Review limits and adjust throttling.

---

### Item 25: Pricing [Operational] `API` | All sources

Review pricing impact. Opus 4.6 pricing:

| Model | Input (per M tokens) | Output (per M tokens) |
|---|---|---|
| Opus 4.6 | $5.00 | $25.00 |

---

### Item 26: Evaluation & Rollout [Verification] `API` `Prompt`

**Evaluate:**
1. Capture baseline results on the source model
2. Run the same evaluation suite on Opus 4.6 with updated prompts
3. Compare on: accuracy, latency, cost, format adherence
4. Pay special attention to tool triggering rates and subagent behavior

**Roll out:**
1. Start with canary deployment
2. Monitor for tool overtriggering and subagent proliferation
3. Gradually increase traffic
4. Keep source model as fallback

---

## Migration phases

| Phase | Items | What happens |
|-------|-------|--------------|
| **1. Scope** | 24, 25 | Review rate limits and pricing impact |
| **2. Breaking changes** | 1, 2, 3, 4*, 5*, 6*, 7*, 8* | Apply mandatory code changes (*from 4.1 only) |
| **3. API updates** | 9, 10, 11, 12, 13 | Adaptive thinking, effort, output capacity, remove beta headers |
| **4. Prompt migration** | 14-23 | Anti-laziness removal, tool softening, subagent guardrails, overthinking/overengineering prevention, LaTeX, git guardrails, safety, compaction, Claudeisms |
| **5. Verify** | 26 | Evaluate and roll out |

## Customer-shareable resources

- [Migration Guide](https://platform.claude.com/docs/en/about-claude/models/migration-guide) -- official step-by-step with checklists
- [Prompting Best Practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices) -- covers Opus 4.6, Sonnet 4.6, Haiku 4.5
- **Prompt Improver** in Console -- use as a starting point, then apply Opus 4.6-specific adjustments from Items 14-23
