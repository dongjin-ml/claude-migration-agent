# Prompting Tips for Opus 4.6 Migration

Opus 4.6 is internally described as "dangerously agentic." Every prompt adjustment below is motivated by a specific Opus 4.6 behavioral characteristic.

## Critical principle

Prompts must be adapted to the TARGET model's behavior. The same prompt technique can yield +24 points on one model and -25 points on another. Prompt migration is not optionalu2014it is the highest-friction part of any model upgrade.

---

## 1. Anti-laziness / thoroughness removal

**Why:** Opus 4.6 does significantly more upfront exploration than any previous model. Anti-laziness prompts cause runaway thinking and token exhaustion.

```
# REMOVE (causes runaway exploration on 4.6):
"Be extremely thorough. Check every file."
"Never skip any details."
"Think step by step through every aspect."
"Do not be lazy."
"Leave no stone unturned."

# KEEP (balanced for 4.6):
"Focus on the most relevant files."
"Investigate further only if initial findings are inconclusive."
```

---

## 2. Tool-use language softening

**Why:** Opus 4.6 is far more responsive to system prompts than 4.5. Aggressive tool language causes overtriggeringu2014e.g., triggering a docx tool to draft an email.

```
# Before (Opus 4.5):
"CRITICAL: You MUST use this tool for every task."
"If in doubt, use the search tool before responding."
"Always check the database before answering any question."

# After (Opus 4.6):
"Use this tool when it would provide concrete value."
"Use the search tool when the question requires specific data."
"Check the database for questions that require stored information."
```

Key: replace blanket defaults with targeted instructions.

---

## 3. Subagent delegation guardrails

**Why:** Opus 4.6 proactively spawns 30+ subagents at once for tasks that should be sequential.

```
Use subagents when tasks can run in parallel, require isolated context,
or involve independent workstreams. For simple tasks, sequential operations,
single-file edits, or tasks where you need to maintain context across steps,
work directly rather than delegating.
```

---

## 4. Anti-overthinking

**Why:** At higher effort levels, Opus 4.6 can oscillate between two approaches until output tokens are exhausted.

```
When you're deciding how to approach a problem, choose an approach and commit
to it. Avoid revisiting decisions unless you encounter new information that
directly contradicts your reasoning. If you're weighing two approaches, pick
one and see it through.
```

---

## 5. Anti-overengineering

**Why:** Opus 4.6 tends to create extra files, add unnecessary abstractions, and overengineer simple tasks (e.g., a one-function change becomes a multi-file refactor).

```
Avoid over-engineering. Only make changes that are directly requested
or clearly necessary. Keep solutions simple and focused:
- Scope: Don't add features, refactor code, or make "improvements" beyond what was asked.
- Documentation: Don't add docstrings, comments, or type annotations to code you didn't change.
- Defensive coding: Don't add error handling, fallbacks, or validation for scenarios that can't happen.
- Abstractions: Don't create helpers, utilities, or abstractions for one-time operations.
```

---

## 6. LaTeX prevention

**Why:** Opus 4.6 defaults to LaTeX for mathematical expressions. Customers expecting plain text will see broken formatting.

```
Format your response in plain text only. Do not use LaTeX, MathJax,
or any markup notation such as \( \), $, or \frac{}{}.
Write all math expressions using standard text characters.
```

---

## 7. Git operation guardrails

**Why:** Opus 4.6 is aggressive with gitu2014may force push, amend published commits, or delete branches without confirmation.

```
Always ask before committing, pushing, or performing destructive git operations.
Never force push or amend published commits.
Prefer creating new commits over amending existing ones.
```

---

## 8. Autonomy / safety guardrails

**Why:** Opus 4.6's high agency means it may take destructive actions (deleting files, dropping tables) autonomously.

```
Consider the reversibility and potential impact of your actions.
For destructive operations (deleting files, dropping tables, modifying
shared infrastructure), always confirm before proceeding.
```

---

## 9. Context awareness for compaction

**Why:** Self-compaction works less reliably on Opus 4.6 (reported by Gitpod/Ona). Long-running tasks may lose important state.

```
Your context window will be automatically compacted as it approaches its limit,
allowing you to continue working from where you left off. Write important state
to files rather than relying on conversation memory for long-running tasks.
```

---

## 10. Prefill migration patterns

Assistant-turn prefills return 400 on Opus 4.6. Migrate each use case:

### Forcing JSON output
```python
# Before (prefill):
messages=[..., {"role": "assistant", "content": "{"}]

# After (structured outputs):
output_config={"format": {"type": "json_schema", "schema": my_schema}}
```

### Skipping preamble
```python
# Before:
messages=[..., {"role": "assistant", "content": "Here is the analysis:"}]

# After:
system="Respond directly with the analysis. Do not include any preamble or introductory phrases."
```

### Continuations
```python
# Before:
messages=[..., {"role": "assistant", "content": "partial response text..."}]

# After:
messages=[..., {"role": "user", "content": "Your previous response ended with: 'partial response text...'. Continue from where you left off."}]
```

### Context hydration
```python
# Before:
messages=[..., {"role": "assistant", "content": "I understand I am a medical assistant..."}]

# After:
messages=[..., {"role": "user", "content": "Reminder: You are acting as a medical assistant. Continue the conversation."}]
```

---

## 11. Adaptive thinking migration

**Why:** Extended thinking with `budget_tokens` is deprecated on Opus 4.6. Adaptive thinking lets the model decide when and how much to think.

```python
# Before (Opus 4.5 u2014 extended thinking):
response = client.messages.create(
    model="claude-opus-4-5-20251101",
    max_tokens=64000,
    thinking={"type": "enabled", "budget_tokens": 32000},
    messages=[...]
)

# After (Opus 4.6 u2014 adaptive thinking):
response = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=64000,
    thinking={"type": "adaptive"},
    output_config={"effort": "high"},
    messages=[...]
)
```

Note: Manual thinking mode (`budget_tokens`) does NOT support interleaved thinking on Opus 4.6. Use adaptive mode if thinking interleaved with tool calls is needed.

---

## 12. Effort parameter guidance

| Workload | Recommended effort |
|----------|--------------------|
| Most complex reasoning (Opus only) | `max` |
| Autonomous multi-step agents | `high` |
| Coding / agentic tasks | `medium` to `high` |
| Chat / non-coding | `low` to `medium` |
| Latency-sensitive | `low` |

**Warning:** `max` effort can cause overthinkingu2014the model oscillates between approaches until tokens are exhausted. Use only when thoroughness is more important than efficiency.

---

## Real-world migration observations

- **Opus 4.5u21924.6 (Gitpod/Ona):** Same pass rate (~90.5%), 13% faster, 8% fewer tokens, 11% fewer iterations. But "4.6 needs more encouragement to use their tools" and compaction is less reliable.
- **Tool encouragement vs. overtriggering:** Some specific tools need MORE encouragement while general tool-use language needs LESS. Test per-tool behavior individually.
- **Eval approach from production:** "80% vibes, 20% evals" u2014 use both LLM-as-judge assertions and manual review.

## Prompt Improver

Anthropic Console includes a free Prompt Improver tool (1-2 minutes). Use as a starting point, then apply the Opus 4.6-specific adjustments above. Note: the Prompt Improver is "effectively deprecated for sophisticated API customers" per AAI teamu2014manual tuning with the patterns above is more effective.
