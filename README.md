# Claude Migration Agent

A CLI that migrates **your application's code and prompts** from an older Claude model to a newer one.

It does three things end-to-end:
1. **Scans** your codebase and prompt files for everything that needs to change when upgrading (model IDs, deprecated parameters, tool versions, and — most importantly — prompt patterns that behave differently on the new model).
2. **Patches** the code and prompts in place, keeping `_prev` backups of every file it touches.
3. **Evaluates** the migrated result by running your test cases on both the old and new models and grading them with an LLM-as-Judge.

In short: point it at your project, tell it which Claude version you're moving to, and get back a migrated codebase plus a pass/fail verdict backed by a report you can review.

## Supported Targets

| `--target` | Source models |
|---|---|
| `haiku-4.5` | Haiku 3, 3.5 |
| `sonnet-4.5` | Sonnet 4, 3.7 |
| `sonnet-4.6` | Sonnet 4.5, 4 |
| `opus-4.6` | Opus 4.5, 4.1 |

---

## 1. Prepare

Before running, you need:

1. **The project to migrate** — a local directory with Claude API calls (inline prompts or separate files both work).
2. **`eval_cases.json`** — your test suite placed in that directory (see §3). Required for `eval` and `autopilot`.
   - Must include at least one `"type": "regression"` case. Regression cases anchor behaviors that **must not break** (language, format, required phrases). Without them, the tool cannot verify the migration is safe.
3. **Credentials** — an Anthropic API key, **or** a GCP project with Vertex AI access and `gcloud` authenticated.

---

## 2. Install

**Requirements:** macOS or Linux. Python 3.12 and `uv` are installed automatically by the setup script — you do not need them beforehand.

```bash
git clone <repo-url>
cd claude-migration-agent
cd setup && ./create-uv-env.sh claude-migration-agent && cd ..
cp .env.example .env
```

Edit `.env`:

```
# "api" or "vertex"
BACKEND=api

# Required when BACKEND=api
ANTHROPIC_API_KEY=sk-ant-...

# Required when BACKEND=vertex (leave blank otherwise)
ANTHROPIC_VERTEX_PROJECT_ID=
CLOUD_ML_REGION=us-east5

AGENT_MODEL=claude-sonnet-4-6
EVAL_MODEL=claude-sonnet-4-6
MAX_EVAL_ITERATIONS=3
```

**What each `.env` variable does:**

| Variable | Purpose |
|---|---|
| `BACKEND` | `api` for Anthropic API, `vertex` for Google Vertex AI. |
| `ANTHROPIC_API_KEY` | Your Anthropic API key. Required when `BACKEND=api`; ignored when `BACKEND=vertex`. |
| `AGENT_MODEL` | Model that **runs this tool** — reads code, writes the report, applies fixes. |
| `EVAL_MODEL` | Model used as **LLM-as-Judge** to grade eval outputs. |
| `MAX_EVAL_ITERATIONS` | Maximum scan → fix → eval loops in `autopilot` before it gives up. |

### Using Vertex AI

Change `BACKEND=vertex` in `.env`, run `gcloud auth application-default login`, and fill in these two variables:

| Variable | Purpose |
|---|---|
| `ANTHROPIC_VERTEX_PROJECT_ID` | Your GCP project ID. |
| `CLOUD_ML_REGION` | Vertex region where your Claude models are enabled (e.g. `us-east5`, `europe-west1`, `asia-southeast1`). |

Also change every model ID in `.env` and `eval_cases.json` to the `@` form — replace the hyphen before the date with `@`. Example: `claude-sonnet-4-6-20251015` → `claude-sonnet-4-6@20251015`. Use the exact snapshot date listed for the model on the [Anthropic docs](https://platform.claude.com/docs/en/about-claude/models). No code changes needed.

---

## 3. `eval_cases.json`

A complete working example is included at [`customer-project/eval_cases.json`](customer-project/eval_cases.json) — copy it into your own project directory as a starting point and adjust the cases.

**Location:** place the file in the directory you pass as `--project-path` when running `eval` or `autopilot`.

```
your-project/
├── eval_cases.json     ← here
├── app.py
└── prompts/
```

**Fields:**

| Field | Required | Purpose |
|---|---|---|
| `source_model` | yes | The customer's current production model ID. |
| `target_model` | yes | The new model ID being migrated to. |
| `system_prompt` | no | System prompt applied to both source and target calls. |
| `cases[].id` | yes | Unique case identifier. |
| `cases[].name` | yes | Short description (shown in console output). |
| `cases[].type` | recommended | `regression` (must not break) or `improvement` (should improve). Autopilot requires at least one regression case. |
| `cases[].input` | yes | The user message sent to both models. |
| `cases[].expected_output` | yes | Reference answer used by the judge for keyword and quality scoring. |
| `cases[].criteria` | no | Extra grading instructions for the judge. |

Aim for 3–5 regression cases covering your load-bearing behaviors (language, output format, required phrases).

**How the judge uses these fields:**

For each case, `EVAL_MODEL` (the LLM-as-Judge) produces four scores:

1. **Keyword check** — does the target output contain key terms/patterns from `expected_output`? (pass/fail)
2. **Quality score** — target output rated 1–5 against `expected_output` (5 = perfect or better).
3. **Comparison** — target output vs. source output: better / equal / worse.
4. **Notes** — brief justification.

`criteria` (if provided) is passed to the judge as additional grading instructions for that case.

**Autopilot PASS condition:**

Autopilot exits as soon as the judge emits `VERDICT: PASS` on its final line. The judge is instructed that **every case with `"type": "regression"` must pass** — a single regression failure blocks PASS. `improvement` cases do not block PASS. If verdict is FAIL, autopilot runs another scan → fix → eval iteration, up to `MAX_EVAL_ITERATIONS`.

**Customizing the evaluation criteria:**

If you need stricter or more permissive pass/fail rules (e.g. require quality score ≥ 4, reject any regression case that scored worse than source, only care about keyword check), edit [`src/prompts/evaluator.md`](src/prompts/evaluator.md). The judge follows this prompt for every case — change the grading instructions there to shift the criteria. For example:

```
A case is considered "pass" only when:
  - keyword_check = pass
  - quality_score >= 4
  - comparison is "better" or "equal"

Output `VERDICT: PASS` only if every regression case passes by this rule.
```

The final-line `VERDICT: PASS` / `VERDICT: FAIL` marker is how `main.py` decides whether to stop — do not change that marker unless you also update `main.py`.

---

## 4. Run

> In every example below, replace `./customer-project` with the path to your own project directory. A sample project is included at `./customer-project/` for quick testing.

### Scan + apply fixes (interactive)

```bash
uv run python main.py scan --target haiku-4.5 --project-path ./customer-project
```

Scans the project, writes a report, then prompts `Apply fixes? (y/n)`. On `y`, files are backed up as `*_prev.*` and patched in place.

### Run evaluation only

```bash
uv run python main.py eval --target haiku-4.5 --project-path ./customer-project
```

Calls source and target models on each case, then has `EVAL_MODEL` grade them.

### End-to-end (scan → fix → eval, loop until PASS)

```bash
uv run python main.py autopilot --target haiku-4.5 --project-path ./customer-project
# or override the iteration cap for this run:
uv run python main.py autopilot --target haiku-4.5 --project-path ./customer-project --max-iterations 5
```

Exits as soon as eval returns `VERDICT: PASS`, or after `MAX_EVAL_ITERATIONS` iterations.

---

## 5. Outputs

**Reports** — `report/<mode>_<target>_<timestamp>.md`
- Scan: per-item findings with severity, file:line, current code, recommended fix, overall verdict
- Eval: per-case keyword check, quality score 1–5, source-vs-target comparison, readiness assessment
- Autopilot: both, one pair per iteration

**Backups** — the original of every modified file is kept with a `_prev` suffix (e.g. `app.py` → `app_prev.py`). Use `diff` to review or `mv` to roll back.

**Per-mode output:**

After `scan` (with fixes applied):
```
report/
  scan_haiku-45_20260414_104650.md
customer-project/
  app.py           # migrated
  app_prev.py      # original
```

After `eval` (read-only — no code changes):
```
report/
  eval_haiku-45_20260414_104650.md
```

After `autopilot` (one report pair per iteration until PASS):
```
report/
  autopilot_scan_iter1_haiku-45_20260414_104650.md
  autopilot_eval_iter1_haiku-45_20260414_105042.md
customer-project/
  app.py           # migrated
  app_prev.py      # original
```

---

## 6. Troubleshooting

| Symptom | Fix |
|---|---|
| `BACKEND=api requires ANTHROPIC_API_KEY` | Set the key in `.env`. |
| `BACKEND=vertex requires: ...` | Fill in `ANTHROPIC_VERTEX_PROJECT_ID` and `CLOUD_ML_REGION`, then `gcloud auth application-default login`. |
| `'<target>' is not a supported migration target` | Use one of: `haiku-4.5`, `sonnet-4.5`, `sonnet-4.6`, `opus-4.6`. |
| `eval_cases.json not found` | Place the file in the directory you pass as `--project-path`. |
| `No regression test cases found` | Add at least one case with `"type": "regression"` — required for a safe verdict. |
| Invalid model ID on Vertex | Use the `@` format in `.env` and `eval_cases.json` (e.g. `claude-sonnet-4-6@20251015`). Get the exact date from the [Anthropic models docs](https://platform.claude.com/docs/en/about-claude/models). |
| Output looks frozen | The `⠋ Working...` spinner runs while the agent uses tools. Large scans take several minutes per phase. |
