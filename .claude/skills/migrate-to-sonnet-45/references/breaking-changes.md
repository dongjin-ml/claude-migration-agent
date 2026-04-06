# Breaking Changes Reference

## Sonnet 4 / Sonnet 3.7 u2192 Sonnet 4.5

All changes in this section are **mandatory** u2014 code will fail without them.

### 1. Model ID
```python
model = "claude-sonnet-4-20250514"       # Before (Sonnet 4)
model = "claude-3-7-sonnet-20250219"     # Before (Sonnet 3.7)
model = "claude-sonnet-4-5-20250929"     # After
```

### 2. Sampling Parameters
Use only `temperature` **OR** `top_p`, not both. Using both returns an error on Claude 4+ models.

Note: If migrating from Sonnet 4, this restriction already applies. New for Sonnet 3.7 migrants.

### 3. Tool Versions
- Text editor: `text_editor_20250124` u2192 `text_editor_20250728` with `str_replace_based_edit_tool`
- Code execution: upgrade to `code_execution_20250825`
- Remove any `undo_edit` command usage

### 4. New `refusal` Stop Reason
Claude 4+ models return `stop_reason: "refusal"` when declining a request. Handle this in your application.

### 5. New `model_context_window_exceeded` Stop Reason
Claude 4.5+ models return `model_context_window_exceeded` when generation stops because the context window is full. This is distinct from `max_tokens`, which still fires when the user-set output limit is reached. Update application logic to handle both stop reasons.

### 6. Trailing Newlines in Tool Parameters
Claude 4.5+ preserves trailing newlines in tool call string parameters. Verify exact string matching logic.

### 7. Rate Limits
Sonnet 4.5 has **separate** rate limits from Sonnet 4 and Sonnet 3.7. Review with the customer.

### 8. Pricing
| | Input (per M tokens) | Output (per M tokens) |
|---|---|---|
| Sonnet 3.7 | $3.00 | $15.00 |
| Sonnet 4 | $3.00 | $15.00 |
| Sonnet 4.5 | $3.00 | $15.00 |

No pricing change for Sonnet migration.

## Official Migration Checklist

From [Anthropic docs](https://platform.claude.com/docs/en/about-claude/models/migration-guide):

- [ ] Update model ID to `claude-sonnet-4-5-20250929`
- [ ] Update tool versions (`text_editor_20250728`, `code_execution_20250825`)
- [ ] Remove `undo_edit` command usage
- [ ] Use only `temperature` OR `top_p`, not both
- [ ] Handle `refusal` stop reason
- [ ] Handle `model_context_window_exceeded` stop reason
- [ ] Verify tool parameter handling for trailing newlines
- [ ] Review new rate limits
- [ ] Update prompts per best practices
- [ ] Consider enabling extended thinking
- [ ] Test in dev before production
