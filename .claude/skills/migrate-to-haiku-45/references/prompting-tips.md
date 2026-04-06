# Prompting Tips for Haiku 4.5 Migration

This guide covers prompt changes **specifically required for Haiku 4.5**. Every recommendation here is motivated by Haiku 4.5's behavioral characteristics, not generic prompt improvement.

## Why prompt migration matters for Haiku 4.5

Haiku 3 to Haiku 4.5 is a cross-generation jump. The model's behavior changes significantly:
- More concise and direct by default
- Requires more explicit instructions than Sonnet in the same generation
- New capabilities (extended thinking, 64K output) change what's possible
- Prompt techniques that worked on Haiku 3 may actively hurt performance on Haiku 4.5

The same prompting technique can produce +24 points on one model and -25 points on another. Prompts must be optimized for the target model.

## Haiku 4.5-specific behavioral changes

### 1. More concise and direct
Haiku 4.5 provides fact-based progress reports rather than self-celebratory updates. It may skip verbal summaries after tool calls, jumping directly to the next action.

**If the customer needs post-action visibility, add this:**
```
After completing a task that involves tool use, provide a quick summary of the work you've done.
```

### 2. Haiku needs explicit prompting
Haiku 4.5 requires more explicit instructions than Sonnet 4.5 in the same generation. Don't assume implicit understanding. Be specific about desired output format, level of detail, and constraints.

**Before (Haiku 3 -- vague):**
```
You are a document analyzer. Summarize the key points.
```

**After (Haiku 4.5 -- explicit):**
```
You are a document analyzer.
Summarize the key points in detail, using bullet points.
Do not skip any major section.
Return your full analysis without abbreviation.
Do not ask clarifying questions -- work with the document as provided.
```

### 3. Claudeisms
Haiku 4.5 may exhibit these behaviors more than Haiku 3:
- Defaulting to first-person responses when not instructed to
- Sycophancy (excessive agreement or praise)
- Unnecessary clarifying questions instead of proceeding
- Apologizing unnecessarily

**Add to system prompt if these are problematic:**
```
Respond in third person unless the user requests otherwise.
Do not apologize unnecessarily.
Do not ask clarifying questions unless the request is truly ambiguous -- proceed with the most reasonable interpretation.
Be direct and factual. Avoid filler phrases.
```

### 4. Tool usage patterns
Haiku 4.5 may need more encouragement to use tools than Haiku 3, or may over-trigger depending on prompt wording.

**If under-triggering (model suggests instead of acting):**
```xml
<default_to_action>
By default, implement changes rather than only suggesting them. If the user's intent is unclear, infer the most useful likely action and proceed, using tools to discover any missing details.
</default_to_action>
```

**If over-triggering (model acts when it should wait):**
```xml
<do_not_act_before_instructions>
Do not jump into implementation or change files unless clearly instructed to make changes. When the user's intent is ambiguous, default to providing information, doing research, and providing recommendations rather than taking action.
</do_not_act_before_instructions>
```

### 5. Overengineering tendency
Haiku 4.5 may overengineer solutions, creating extra files, adding unnecessary abstractions, or over-scoping changes.

**Add if the customer sees this:**
```
Avoid over-engineering. Only make changes that are directly requested or clearly necessary. Keep solutions simple and focused:
- Don't add features, refactor code, or make improvements beyond what was asked.
- Don't add docstrings, comments, or type annotations to code you didn't change.
- Don't add error handling or validation for scenarios that can't happen.
- Don't create helpers or abstractions for one-time operations.
```

### 6. Output capacity change
Haiku 4.5 supports **64K token output** (up from 4K in Haiku 3). Prompts that artificially constrained output length (e.g., "keep your response under 500 words") can be relaxed if the customer now wants more detailed output.

## Ready-to-use prompt snippets for Haiku 4.5

These XML-tagged snippets address specific Haiku 4.5 behaviors. Add them to the system prompt as needed.

### Parallel tool calling
Haiku 4.5 supports parallel tool calls. Add this to maximize throughput:
```xml
<use_parallel_tool_calls>
If you intend to call multiple tools and there are no dependencies between the tool calls, make all of the independent tool calls in parallel. Prioritize calling tools simultaneously whenever the actions can be done in parallel rather than sequentially.
</use_parallel_tool_calls>
```

### Reducing hallucinations
Haiku 4.5 benefits from explicit investigation instructions:
```xml
<investigate_before_answering>
Never speculate about code you have not opened. If the user references a specific file, you MUST read the file before answering. Make sure to investigate and read relevant files BEFORE answering questions about the codebase. Never make any claims about code before investigating unless you are certain of the correct answer.
</investigate_before_answering>
```

### Cleaning up temporary files
Haiku 4.5 may create scratch pad files during complex tasks:
```
If you create any temporary new files, scripts, or helper files for iteration, clean up these files by removing them at the end of the task.
```

## Extended thinking

Haiku 4.5 now supports extended thinking for significant improvements on coding and reasoning tasks:
```python
response = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=16384,
    thinking={"type": "enabled", "budget_tokens": 16384},
    messages=[...]
)
```

Note: Extended thinking is deprecated in Claude 4.6+. Use adaptive thinking instead. Mention this if the customer plans further upgrades.

## Prompt optimization approach

1. **Start with Prompt Improver** -- free tool in Anthropic Console, takes 1-2 minutes. Use as a starting point, not final output.
2. **Apply Haiku 4.5-specific adjustments** -- explicit formatting, anti-Claudeisms, tool-use language calibration.
3. **Templatize** -- use f-strings or variable interpolation so model-specific adjustments are isolated and easy to change.
4. **Test and iterate** -- run representative inputs, compare output quality, adjust until parity or improvement.

## Customer deliverables format

When delivering prompt migration results:
1. **Prompt Review PDF** -- each change highlighted with a "why" explanation
2. **Side-by-side comparison** -- use `<ORIGINAL>` / `<CHANGED>` tags
3. **raw_prompt.txt** -- final prompt ready for copy-paste into production
