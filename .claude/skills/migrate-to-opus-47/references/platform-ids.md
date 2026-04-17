# Platform-specific model IDs and backend notes — Opus 4.7

The migration agent must preserve whichever backend the customer project already uses.
Only the model ID string changes; the client class, auth, and env vars stay as-is.

| Backend | Client class | Target model ID | Auth | Preserve untouched |
|---|---|---|---|---|
| Anthropic API | `Anthropic()` | `claude-opus-4-7` (alias) or dated snapshot | `ANTHROPIC_API_KEY` | — |
| Google Vertex AI | `AnthropicVertex(project_id, region)` | `claude-opus-4-7@<YYYYMMDD>` — dated snapshot required; verify the exact ID enabled in the customer's Vertex Model Garden | ADC / service account (`GOOGLE_APPLICATION_CREDENTIALS`) | `ANTHROPIC_VERTEX_BASE_URL`, `ANTHROPIC_VERTEX_PROJECT_ID`, `CLOUD_ML_REGION`, `CLAUDE_CODE_USE_VERTEX` |
| AWS Bedrock | `AnthropicBedrock()` | `anthropic.claude-opus-4-7-<YYYYMMDD>-v1:0` (or the inference-profile ARN); verify the exact ID in the customer's Bedrock console | AWS credentials | `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `CLAUDE_CODE_USE_BEDROCK` |

> **Note:** The Anthropic API accepts the `claude-opus-4-7` alias. Vertex AI and Bedrock
> generally require the dated snapshot form. Do not auto-apply the alias to a Vertex/Bedrock
> project — confirm the snapshot ID with the customer. Opus 4.7 was released 2026-04-17;
> third-party platform availability may lag the direct API.

## Source model IDs (for detection)

| Backend | Opus 4.6 | Opus 4.5 |
|---|---|---|
| Anthropic API | `claude-opus-4-6` | `claude-opus-4-5-20251101` |
| Vertex AI | `claude-opus-4-6@<YYYYMMDD>` | `claude-opus-4-5@20251101` |
| Bedrock | `anthropic.claude-opus-4-6-<YYYYMMDD>-v1:0` | `anthropic.claude-opus-4-5-20251101-v1:0` |

## Why `ANTHROPIC_VERTEX_BASE_URL` / `base_url` must be preserved

FSI customers often route Vertex traffic through an internal proxy for compliance.
This is configured either via the `ANTHROPIC_VERTEX_BASE_URL` env var or by passing
`base_url=` directly to `AnthropicVertex(...)`. Removing or rewriting either form
breaks their network path even if the model ID is correct.

## Feature-parity caveats

Opus 4.7 launched on the direct API on 2026-04-17. Vertex/Bedrock availability and
feature parity (task budgets, high-resolution images) may lag. If a migration item
recommends one of these, **flag it in the report for manual verification** instead
of auto-applying on Vertex/Bedrock projects.

## Regional availability

Vertex and Bedrock model availability is per-region. Before migrating, confirm the target
model is enabled in the customer's pinned region.
