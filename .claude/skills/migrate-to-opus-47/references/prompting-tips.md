# Opus 4.7 prompt-migration snippets

Copy-paste snippets for the prompt-migration items in SKILL.md.

## Item 18 — remove forced progress scaffolding

Delete patterns like:
```
After every N tool calls, summarize progress.
Provide a status update every 30 seconds.
```
Only re-add if the new default is mis-calibrated:
```
Provide a progress update only when you complete a major phase.
```

## Item 19 — subagent guidance (direction reverses from 4.6)

Delete 4.6-era limiters:
```
For simple tasks, work directly rather than delegating to subagents.
```
Add only if more parallelism is wanted:
```
For independent research questions, spawn parallel subagents to investigate
each one concurrently.
```

## Item 20 — effort calibration instead of prompting

If shallow reasoning at `low`/`medium`: raise `output_config.effort` first.
If `low` must stay for latency:
```
This task involves multi-step reasoning. Think carefully through the
problem before responding.
```

## Item 21 — tool-call guidance (direction reverses from 4.6)

Delete 4.6-era softeners:
```
Use this tool only when it would provide concrete value.
```
Add only if under-triggering is observed:
```
For any question about current data, use the search tool before answering.
```

## Item 16 — literal instruction following

State scope explicitly; do not rely on the model generalizing:
```
Fix the bug in auth.py. Also check whether the same pattern appears in the
other handlers and fix those too.
```
