# Prompting Tips for Sonnet 4.5 Migration

This guide covers prompt changes specifically needed for Sonnet 4.5's behavioral characteristics. Every recommendation here is motivated by how Sonnet 4.5 behaves differently from Sonnet 4 and Sonnet 3.7.

## Sonnet 4.5 behavioral changes that require prompt updates

### 1. More terse u2014 skips summaries after tool calls

Sonnet 4.5 jumps directly to the next action without verbal summaries. If the customer needs visibility into what the model did:
```
After completing a task that involves tool use, provide a quick summary of the work you've done.
```

### 2. More human-like tone

Sonnet 4.5 is more fluent, colloquial, and grounded. It avoids the "excessively positive AI assistant" tone of older models. Customers expecting formal or structured output should add explicit format instructions:
```
Respond in a professional, structured format. Use headings and bullet points for clarity.
```

### 3. Literal instruction following

Sonnet 4.5 follows instructions literally. "Can you suggest changes" = it will only suggest. This is a significant shift from older models that would infer intent.

**Before (Sonnet 4 / 3.7):**
```
Can you suggest improvements to this code?
```
u2192 Model might actually make the changes

**After (Sonnet 4.5):**
```
Implement improvements to this code. Make the actual edits, don't just suggest them.
```
u2192 Model will implement the changes

### 4. Excellent parallel tool calling

Sonnet 4.5 fires off multiple speculative searches simultaneously. Add this snippet to maximize throughput:
```xml
<use_parallel_tool_calls>
If you intend to call multiple tools and there are no dependencies between the tool calls, make all of the independent tool calls in parallel. Prioritize calling tools simultaneously whenever the actions can be done in parallel rather than sequentially.
</use_parallel_tool_calls>
```

### 5. May undertrigger tools

Sonnet 4.5 may abstain from using tools unless explicitly directed. If tools are being underused, add:
```xml
<default_to_action>
By default, implement changes rather than only suggesting them. If the user's intent is unclear, infer the most useful likely action and proceed, using tools to discover any missing details instead of guessing.
</default_to_action>
```

Conversely, if the model should be conservative:
```xml
<do_not_act_before_instructions>
Do not jump into implementation or change files unless clearly instructed to make changes. When the user's intent is ambiguous, default to providing information, doing research, and providing recommendations rather than taking action.
</do_not_act_before_instructions>
```

### 6. Chain-of-thought prompting not needed

Sonnet 4.5 naturally uses chain-of-thought in its internal thinking process. Remove explicit CoT instructions:

**Before (Sonnet 3.7):**
```
Think step by step. First analyze the problem, then consider possible solutions, then implement the best one.
```

**After (Sonnet 4.5):**
```
Analyze and fix this issue.
```
u2192 Model handles reasoning internally. Explicit CoT wastes tokens without improving quality.

### 7. Claudeisms

Sonnet 4.5 may exhibit first-person defaults, sycophancy, and unnecessary clarifying questions. Add to system prompt if problematic:
```
Do not use first-person language unless the task requires a persona.
Do not apologize or use sycophantic language.
Do not ask clarifying questions unless absolutely necessary u2014 work with the information provided.
```

### 8. Overengineering tendency

Sonnet 4.5 may create extra files, add unnecessary abstractions, or over-scope solutions. Add:
```
Avoid over-engineering. Only make changes that are directly requested or clearly necessary. Keep solutions simple and focused:
- Don't add features, refactor code, or make "improvements" beyond what was asked.
- Don't add docstrings, comments, or type annotations to code you didn't change.
- Don't create helpers, utilities, or abstractions for one-time operations.
```

## Reducing hallucinations

Sonnet 4.5 benefits from explicit instructions to investigate before answering:
```xml
<investigate_before_answering>
Never speculate about code you have not opened. If the user references a specific file, you MUST read the file before answering. Make sure to investigate and read relevant files BEFORE answering questions about the codebase. Never make any claims about code before investigating unless you are certain of the correct answer.
</investigate_before_answering>
```

## Controlling output format

Sonnet 4.5's natural output can be heavy on markdown and bullet points. To get flowing prose:
```xml
<avoid_excessive_markdown_and_bullet_points>
When writing reports, documents, technical explanations, analyses, or any long-form content, write in clear, flowing prose using complete paragraphs and sentences. Use standard paragraph breaks for organization and reserve markdown primarily for inline code, code blocks, and simple headings. DO NOT use ordered lists or unordered lists unless presenting truly discrete items.
</avoid_excessive_markdown_and_bullet_points>
```

## Preventing test-specific solutions (anti-reward-hacking)

Sonnet 4.5 may hard-code solutions to pass specific tests rather than solving the general problem:
```
Do not hard-code solutions or special-case logic that only works for specific test inputs. Solutions must be general-purpose and handle all valid inputs correctly, not just the examples provided in tests.
```

## Cleaning up temporary files

Sonnet 4.5 may create scratch pad files during work. Instruct cleanup:
```
If you create any temporary new files, scripts, or helper files for iteration, clean up these files by removing them at the end of the task.
```

## Extended thinking

For complex reasoning tasks, enable extended thinking:
```python
response = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=16384,
    thinking={"type": "enabled", "budget_tokens": 16384},
    messages=[...]
)
```

Note: Extended thinking is deprecated in Claude 4.6+. If the customer plans further upgrades, mention adaptive thinking as the future direction.

## Prompt optimization across versions

The same prompting technique can produce significantly different results across model versions u2014 what works well on one may hurt performance on another. For example, adding negative examples yielded +24 points for Opus but -25 points for Gemini in one customer evaluation.

Prompts need to be optimized per-model version. The "fair" way to compare models is by hill-climbing each prompt per-model.

## Templatization

Recommend customers templatize prompts with f-strings or equivalent variable interpolation. This makes model-specific adjustments isolated and easy to change.

## Migration approach

1. Run existing prompts through the **Prompt Improver** in Anthropic Console (free, 1-2 minutes) as a starting point
2. Test with minimal prompt first, then add constraints based on observed behavior
3. Use XML tags to structure complex prompts
4. Templatize for easy per-model tuning

## Known issues from recent migrations

- **Sonnet 4 u2192 4.5**: Tool usage patterns change; may undertrigger or overtrigger depending on prompt language
- **Sonnet 3.7 u2192 4.5**: Significant behavioral shift; thorough prompt review needed. Cross-generation jumps are the hardest.
- **General**: Models may create extra files as scratch pads u2014 instruct cleanup if undesired
