# Platform-specific model IDs and backend notes — Sonnet 4.6

The migration agent must preserve whichever backend the customer project already uses.
Only the model ID string changes; the client class, auth, and env vars stay as-is.

| Backend | Client class | Target model ID | Auth | Preserve untouched |
|---|---|---|---|---|
| Anthropic API | `Anthropic()` | `claude-sonnet-4-6` (alias) or dated snapshot | `ANTHROPIC_API_KEY` | — |
| Google Vertex AI | `AnthropicVertex(project_id, region)` | `claude-sonnet-4-6@<YYYYMMDD>` — dated snapshot required (e.g. `claude-sonnet-4-6@20251015`); verify the exact ID enabled in the customer's Vertex Model Garden | ADC / service account (`GOOGLE_APPLICATION_CREDENTIALS`) | `ANTHROPIC_VERTEX_BASE_URL`, `ANTHROPIC_VERTEX_PROJECT_ID`, `CLOUD_ML_REGION`, `CLAUDE_CODE_USE_VERTEX` |
| AWS Bedrock | `AnthropicBedrock()` | `anthropic.claude-sonnet-4-6-<YYYYMMDD>-v1:0` (or the inference-profile ARN); verify the exact ID in the customer's Bedrock console | AWS credentials | `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `CLAUDE_CODE_USE_BEDROCK` |

> **Note:** The Anthropic API accepts the `claude-sonnet-4-6` alias. Vertex AI and Bedrock
> generally require the dated snapshot form. Do not auto-apply the alias to a Vertex/Bedrock
> project — confirm the snapshot ID with the customer.

## Source model IDs (for detection)

| Backend | Sonnet 4.5 | Sonnet 4 |
|---|---|---|
| Anthropic API | `claude-sonnet-4-5-20250929` | `claude-sonnet-4-20250514` |
| Vertex AI | `claude-sonnet-4-5@20250929` | `claude-sonnet-4@20250514` |
| Bedrock | `anthropic.claude-sonnet-4-5-20250929-v1:0` | `anthropic.claude-sonnet-4-20250514-v1:0` |

## Why `ANTHROPIC_VERTEX_BASE_URL` / `base_url` must be preserved

FSI customers often route Vertex traffic through an internal proxy for compliance.
This is configured either via the `ANTHROPIC_VERTEX_BASE_URL` env var or by passing
`base_url=` directly to `AnthropicVertex(...)`. Removing or rewriting either form
breaks their network path even if the model ID is correct.

## Feature-parity caveats

Some features may lag on Vertex/Bedrock vs the direct API (Files API, certain beta headers,
newest tool versions). If a migration item recommends one of these, **flag it in the report
for manual verification** instead of auto-applying.

## Regional availability

Vertex and Bedrock model availability is per-region. Before migrating, confirm the target
model is enabled in the customer's pinned region.
