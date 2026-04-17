# Opus 4.7 breaking changes — quick reference

| Change | Symptom | Fix |
|---|---|---|
| `thinking: {type: "enabled", budget_tokens: N}` | 400 error | `thinking: {type: "adaptive"}` + `output_config.effort` |
| `temperature` / `top_p` / `top_k` (any non-default) | 400 error | Remove the parameter entirely |
| Assistant-message prefill | 400 error | `output_config.format` (JSON schema) or system-prompt instructions |
| Thinking text empty (`block.thinking == ""`) | Silent — UI looks frozen | `thinking: {type: "adaptive", display: "summarized"}` |
| Token counts increased ~1-1.35x | Higher cost, earlier `max_tokens` hits | Re-tune `max_tokens`; re-benchmark cost |
| Bounding-box coords look wrong | Coordinates off by old scale factor | Remove scale conversion — coords are now 1:1 pixels |

## Detection patterns for the scanner

Grep the customer codebase for these:

```
budget_tokens
"type": "enabled"
temperature=
temperature:
top_p
top_k
"role": "assistant".*content.*\{   # prefill heuristic
.thinking)                         # reading thinking block text
effort-2025-11-24
interleaved-thinking-2025-05-14
output_format=
```
