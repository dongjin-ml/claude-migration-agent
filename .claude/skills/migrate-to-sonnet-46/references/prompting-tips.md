# Prompting Tips for Sonnet 4.6 Migration

Prompt migration is the highest-friction part of moving to Sonnet 4.6. The same prompting technique can produce dramatically different results across model versions -- what works well on Sonnet 4.5 may hurt performance on 4.6. Prompts must be adapted specifically for Sonnet 4.6's behavioral characteristics.

## Sonnet 4.6 behavioral profile

Sonnet 4.6 is the most agentic Sonnet to date. Key behavioral shifts from 4.5:
- **More proactive by default** -- anti-laziness prompts cause runaway thinking
- **Simpler prompts work better** -- complex rule-heavy system prompts degrade instruction following
- **More sensitive to tool language** -- aggressive tool-use instructions cause overtriggering
- **Prefills removed** -- assistant message prefilling returns 400 error
- **Effort parameter controls depth** -- defaults to `high` (4.5 had no default)
- **More Claudeisms** -- first-person defaults, sycophancy, unnecessary clarifying questions

## 1. Prefill migration patterns

Sonnet 4.6 does not support prefilling assistant messages. Five patterns to replace common prefill use cases:

### 1a. Output formatting (JSON/YAML)
```python
# Before: prefill to force JSON
messages = [
    {"role": "user", "content": "Classify this text"},
    {"role": "assistant", "content": "{\"category\": "},
]

# After: use structured outputs
response = client.messages.create(
    model="claude-sonnet-4-6",
    messages=[{"role": "user", "content": "Classify this text"}],
    output_config={"format": {"type": "json_schema", "schema": classification_schema}},
)
```

### 1b. Eliminating preambles
```
# Before: prefill to skip "Here is the summary..."
messages = [{"role": "assistant", "content": "Summary:"}]

# After: direct instruction
system = "Respond directly without preamble. Do not start with phrases like 'Here is...', 'Based on...', or 'Sure, I can help with that.'."
```

### 1c. Avoiding bad refusals
Claude 4.6 is much better at appropriate refusals. Clear prompting without prefill is sufficient. If refusals persist, refine the system prompt to clarify the intended use case.

### 1d. Continuations
```python
# Before: prefill with partial response
messages = [{"role": "assistant", "content": partial_response}]

# After: user-turn continuation
messages = [{
    "role": "user",
    "content": f"Your previous response was interrupted and ended with: '{partial_response[-200:]}'. Continue from where you left off."
}]
```

### 1e. Context hydration / role consistency
```python
# Before: prefill to set role
messages = [{"role": "assistant", "content": "I understand I am a financial analyst."}]

# After: system prompt
system = "You are a financial analyst. Maintain this role throughout the conversation."
```

## 2. Anti-laziness prompt removal

This is the single biggest source of Sonnet 4.6 migration regressions. Sonnet 4.6 is naturally thorough -- adding thoroughness prompts causes it to overthink, go back and forth between options, and waste tokens.

**Remove these patterns entirely:**
```
# REMOVE all of these from your prompts:
"Be thorough and comprehensive"
"Never skip any details"
"Think step by step through every aspect"
"Make sure to check everything"
"Do not be lazy"
"Complete the entire task without shortcuts"
"CRITICAL: You MUST..."
"Use the think tool to plan your approach"
```

**Replace with minimal direction:**
```
# Before (Sonnet 4.5)
You MUST be thorough and comprehensive. Never skip any details.
Think step by step. Check everything before responding.
Do not be lazy or take shortcuts.

# After (Sonnet 4.6)
Analyze the problem and provide your findings.
```

## 3. System prompt simplification

Complex rule-heavy prompts cause Sonnet 4.6 to degrade on instruction following. Asana reported a 5-7% gap vs Sonnet 4.5 baseline with complex prompts; simplified prompts recovered ~2%.

**Principles:**
- Start with minimal prompt, add constraints only when needed
- Use positive framing ("write in third person") not prohibitions ("NEVER use first person")
- Combine related rules into single intent statements
- Remove redundant or contradictory rules

**Before:**
```
Rules:
1. NEVER use first person
2. NEVER apologize
3. ALWAYS respond in 3 paragraphs
4. DO NOT use bullet points
5. DO NOT speculate
6. NEVER mention you are an AI
7. ALWAYS cite sources
```

**After:**
```
Write in third person using flowing prose paragraphs. Be direct, cite sources when available.
```

## 4. Tool language softening

Sonnet 4.6 is more responsive to tool-use instructions. Language designed to overcome Sonnet 4.5's conservatism now causes overtriggering.

**Before (Sonnet 4.5):**
```
CRITICAL: You MUST use the search tool before answering ANY question.
ALWAYS search first. If in doubt, search again.
Never answer without searching.
```

**After (Sonnet 4.6):**
```
Use the search tool when you need context about specific topics
or when the user's question requires current information.
```

**For proactive tool use:**
```xml
<default_to_action>
By default, implement changes rather than only suggesting them.
If the user's intent is unclear, infer the most useful likely action
and proceed, using tools to discover any missing details.
</default_to_action>
```

**For conservative tool use:**
```xml
<do_not_act_before_instructions>
Do not jump into implementation unless clearly instructed.
Default to providing information and recommendations
rather than taking action.
</do_not_act_before_instructions>
```

## 5. Claudeisms mitigation

Sonnet 4.6 exhibits more "Claudeisms" than 4.5: first-person defaults, sycophantic responses ("Great question!"), unnecessary clarifying questions, and excessive apologies. This was a significant friction point in real migrations (e.g., OpenEvidence delayed their migration due to this).

**Add to system prompt if these behaviors appear:**
```
Do not default to first-person responses unless the task requires it.
Do not apologize or use sycophantic phrases.
Do not ask clarifying questions unless truly essential.
Be direct and professional.
```

## 6. Effort parameter interaction with prompting

The effort parameter is a primary control lever on Sonnet 4.6. It affects how deeply the model thinks, which interacts with prompt style.

| Workload | Effort | Notes |
|----------|--------|-------|
| Not using thinking (from 4.5) | `low` | Similar performance to Sonnet 4.5 |
| Coding / agentic | `medium` | Balance of quality and speed |
| Chat / non-coding | `low` | Fast, direct responses |
| Latency-sensitive | `low` | Minimize response time |
| Autonomous agents | `high` | Default -- dial down if token waste |
| `max` | **ERROR** | Opus 4.6 only -- do not use on Sonnet |

**Higher effort + thoroughness prompts = worst case:** The combination of `high` effort and anti-laziness prompts causes the most severe runaway thinking.

**Higher effort + tools = camelCase risk:** At higher effort levels, tool parameter names may switch to camelCase. Lower effort for tool-heavy workflows.

## 7. Anti-overengineering prompt

Sonnet 4.6 may overengineer solutions. Add this snippet if the model adds unnecessary complexity:

```
Avoid over-engineering. Only make changes that are directly requested
or clearly necessary. Keep solutions simple and focused:
- Don't add features, refactor code, or make "improvements" beyond what was asked
- Don't add docstrings, comments, or type annotations to code you didn't change
- Don't add error handling or validation for scenarios that can't happen
- Don't create helpers, utilities, or abstractions for one-time operations
```

## 8. Useful prompt snippets for Sonnet 4.6

**Parallel tool calling:**
```xml
<use_parallel_tool_calls>
If you intend to call multiple tools and there are no dependencies
between the calls, make all independent calls in parallel.
</use_parallel_tool_calls>
```

**Anti-hallucination:**
```xml
<investigate_before_answering>
Never speculate about code you have not opened. Read relevant files
BEFORE answering questions. Never make claims about code before investigating.
</investigate_before_answering>
```

**Prose formatting:**
```xml
<avoid_excessive_markdown_and_bullet_points>
Write in clear, flowing prose using complete paragraphs.
Reserve markdown for code blocks and simple headings.
Do not use ordered or unordered lists unless presenting truly discrete items.
</avoid_excessive_markdown_and_bullet_points>
```

**Summary after tool use (if needed):**
```
After completing a task that involves tool use, provide a quick summary of the work you've done.
```

**Cleanup temp files:**
```
If you create any temporary files or scripts for iteration, clean them up by removing them at the end of the task.
```

## Known migration issues

- **Claudeisms worse on 4.6 than 4.5** -- first-person defaults, sycophancy. OpenEvidence delayed migration because of this.
- **Anti-laziness prompts cause the most regressions** -- this is the #1 issue in 4.5 to 4.6 migrations.
- **Instruction following degrades with complex system prompts** -- Asana saw 5-7% gap vs 4.5 baseline.
- **Tool parameter names may switch to camelCase** at higher effort levels.
- **Extended thinking still fixes mistakes that adaptive mode makes** -- some customers (Notion, Asana) report better results keeping extended thinking with budget_tokens during transition.
- **`max` effort returns an error on Sonnet 4.6** -- it is Opus 4.6 only.
