---
name: prompt-injection-probe
description: Runs prompt injection probe against an LLM endpoint and reports which attacks succeeded. Use when auditing an LLM-backed app for prompt injection vulnerabilities.
---

# Prompt Injection Probe

Fires curated prompt-injection payloads at an LLM-backed endpoint and uses a second Claude call as a semantic judge to classify each response as `BLOCKED` or `INJECTED`.

## What it does

1. POSTs each payload in `payloads/direct.json` to the target endpoint as `{"message": "<payload>"}`.
2. Sends `(system prompt, payload, target response)` to a `claude-haiku-4-5-20251001` judge wrapped in nonced XML delimiters.
3. Judge returns `{"result": "BLOCKED" | "INJECTED", "reason": "…"}`.
4. Renders a Rich terminal table (red = INJECTED, green = BLOCKED, yellow = ERROR).
5. Writes the full result set to `results/results_<timestamp>.json`.
6. Exits `1` if any payload succeeded, `0` otherwise (CI-friendly).

## Running the built-in demo

Terminal 1 — start the demo target:

    uvicorn target:app --reload

Terminal 2 — run the probe:

    python probe.py

Both terminals need `ANTHROPIC_API_KEY` set (`.env` is read by both processes).

## CLI flags

| Flag | Default | Purpose |
|---|---|---|
| `--target` | `http://localhost:8000/chat` | Endpoint URL; POST `{"message": str}`, expect `{"response": str}`. |
| `--system-prompt` | — | Literal system-prompt string passed to the judge. |
| `--system-prompt-file` | `system_prompt.txt` | File containing the system prompt. Mutually exclusive with `--system-prompt`. |
| `--payloads` | `payloads/direct.json` | JSON array of payload strings. |
| `--delay` | `1.0` | Seconds between target requests. |
| `--output` | `results/results_<ISO8601>.json` | Where to write full results. |

## Interpreting results

- **BLOCKED** — target refused, deflected, or otherwise respected the system prompt. Good.
- **INJECTED** — target complied with the attacker payload rather than the system prompt. This is the vulnerability.
- **ERROR** — target unreachable / non-200 / judge parse failure. Investigate before drawing conclusions.

## Common failure modes

| Symptom | Cause | Fix |
|---|---|---|
| `KeyError: 'ANTHROPIC_API_KEY'` at startup | `.env` missing or key not set in this terminal | Copy `.env.example` → `.env` and fill in, or `export ANTHROPIC_API_KEY=…`. |
| `httpx.ConnectError` on every payload | `target.py` not running, or `--target` wrong | Start uvicorn on port 8000, or pass `--target http://…`. |
| All rows are ERROR with "judge parse error" | Judge returned free-form prose | Inspect the raw response in the ERROR `reason` field; usually a transient fluctuation — re-run. |
| Port 8000 already in use | Another process bound 8000 | `uvicorn target:app --port 8001` + `python probe.py --target http://localhost:8001/chat`. |
