# Breaking Changes Reference — Opus 4.6

## From Any Source (Opus 4.5 or 4.1)

### 1. Model ID
```python
model = "claude-opus-4-5-20251101"   # Before (from Opus 4.5)
model = "claude-opus-4-1-20250805"   # Before (from Opus 4.1)
model = "claude-opus-4-6"            # After
```

### 2. Prefill Removal
Prefilling assistant messages returns **400 error**. Migration patterns:
- Output formatting: use structured outputs or `output_config.format`
- Eliminating preambles: use system prompt instructions
- Avoiding refusals: restructure prompts
- Continuations: use user-turn continuations

### 3. Tool Parameter JSON Escaping
JSON escaping may differ. Always use standard JSON parsers (`json.loads()`, `JSON.parse()`).

## From Opus 4.1 Only (additional)

### 4. Sampling Parameters
Use only `temperature` **OR** `top_p`, not both.

### 5. Tool Versions
- Text editor: `text_editor_20250124` → `text_editor_20250728` with `str_replace_based_edit_tool`
- Code execution: upgrade to `code_execution_20250825`
- Remove any `undo_edit` command usage

### 6. New `refusal` Stop Reason
Claude 4+ returns `stop_reason: "refusal"` when declining. Handle in application logic.

### 7. New `model_context_window_exceeded` Stop Reason
Claude 4.5+ returns this when context window is full. Distinct from `max_tokens`.

### 8. Trailing Newlines in Tool Parameters
Claude 4.5+ preserves trailing newlines. Verify exact string matching logic.

## Official Migration Checklist

From [Anthropic docs](https://platform.claude.com/docs/en/about-claude/models/migration-guide):

- [ ] Update model ID to `claude-opus-4-6`
- [ ] Remove assistant message prefills (use structured outputs)
- [ ] Ensure JSON parsing uses standard parsers
- [ ] (From 4.1) Use only `temperature` OR `top_p`
- [ ] (From 4.1) Update tool versions
- [ ] (From 4.1) Handle `refusal` stop reason
- [ ] (From 4.1) Handle `model_context_window_exceeded` stop reason
- [ ] (From 4.1) Verify trailing newline handling
- [ ] Migrate to adaptive thinking
- [ ] Remove legacy beta headers
- [ ] Review tool triggering prompts
- [ ] Review subagent delegation prompts
- [ ] Test and roll out
