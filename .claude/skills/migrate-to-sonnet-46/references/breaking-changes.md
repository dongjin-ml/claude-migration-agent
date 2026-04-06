# Breaking Changes Reference

## Sonnet 4.5 / Sonnet 4 u2192 Sonnet 4.6

### Universal breaking changes (all source models)

#### 1. Model ID
```python
model = "claude-sonnet-4-5-20250929"   # Before (from 4.5)
model = "claude-sonnet-4-20250514"     # Before (from 4)
model = "claude-sonnet-4-6"            # After
```

#### 2. Prefill Removal
Prefilling assistant messages returns a **400 error** on Sonnet 4.6. Migration patterns:
- Output formatting u2192 structured outputs via `output_config.format`
- Eliminating preambles u2192 direct instructions in system prompt
- Avoiding bad refusals u2192 rephrase request or system prompt guidance
- Continuations u2192 user-turn continuations

#### 3. Tool Parameter JSON Escaping
JSON escaping may differ. Always use `json.loads()` / `JSON.parse()` u2014 never exact string matching on JSON.

### Additional breaking changes (from Sonnet 4 only)

#### 4. Sampling Parameters
Use only `temperature` **OR** `top_p`, not both. Error on Claude 4+.

#### 5. Tool Versions
- Text editor: `text_editor_20250124` u2192 `text_editor_20250728` with `str_replace_based_edit_tool`
- Code execution: upgrade to `code_execution_20250825`
- Remove any `undo_edit` command usage

#### 6. `refusal` Stop Reason (applies to ALL sources)
Claude 4+ returns `stop_reason: "refusal"` when declining a request. Even Sonnet 4.5 users should verify their application handles this stop reason.

#### 7. `model_context_window_exceeded` Stop Reason
Claude 4.5+ returns `model_context_window_exceeded` when context window is full. Distinct from `max_tokens`.

#### 8. Trailing Newlines
Claude 4.5+ preserves trailing newlines in tool call string parameters.

## Official Migration Checklist

From [Anthropic docs](https://platform.claude.com/docs/en/about-claude/models/migration-guide):

- [ ] Update model ID to `claude-sonnet-4-6`
- [ ] Remove all assistant message prefills (use structured outputs or instructions)
- [ ] Use standard JSON parsers for tool parameters
- [ ] (From Sonnet 4) Use only `temperature` OR `top_p`
- [ ] (From Sonnet 4) Update tool versions
- [ ] Handle `refusal` stop reason (all sources)
- [ ] (From Sonnet 4) Handle `model_context_window_exceeded` stop reason
- [ ] (From Sonnet 4) Verify trailing newline handling
- [ ] Migrate to adaptive thinking
- [ ] Configure effort parameter (default is `high`)
- [ ] Remove anti-laziness prompts
- [ ] Simplify system prompts
- [ ] Remove legacy beta headers
- [ ] Migrate `output_format` to `output_config.format`
- [ ] Review rate limits
- [ ] Test in dev before production
