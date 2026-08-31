# Incident Resolver

An agentic system that diagnoses production incidents and proposes a
human-approved remediation — built to demonstrate engineering judgment on
a small, verifiable problem rather than feature breadth.

## The bottleneck this addresses

On-call engineers waste the first several minutes of every incident doing
the same manual triage: reading logs, checking recent deploys, correlating
metrics, forming a hypothesis. That triage is slow, inconsistent between
engineers, and error-prone under pressure — exactly the kind of bounded,
evidence-grounded reasoning task an agent can do reliably *if* it's forced
to show its work and a human stays in the loop for anything risky.

## Two solutions, benchmarked against each other

| | Baseline | Advanced |
|---|---|---|
| Input handling | full incident dumped into one prompt | deterministic tools extract structured evidence first |
| Diagnosis | single LLM call, no grounding | LLM diagnosis constrained to cited evidence indices |
| Verification | none | second LLM pass audits the diagnosis against the evidence |
| Safety | none | deterministic keyword-based veto/escalation for destructive actions |
| Approval | implied | explicit `requires_human_approval` gate, simulated action only |

```
BASELINE                          ADVANCED
Incident                          Incident
   |                                 |
   v                                 v
 LLM (one shot)              Deterministic tools
   |                        (logs/metrics/config/history)
   v                                 |
Diagnosis                            v
                              Evidence Collector
                                      |
                                      v
                            LLM Diagnosis (grounded)
                                      |
                                      v
                              LLM Verification Pass
                                      |
                                      v
                              Safety / Risk Gate
                                      |
                                      v
                              Human Approval (simulated)
```

## Quickstart

```bash
pip install -e .
export LLM_PROVIDER=openrouter          # or "openai"
export OPENROUTER_API_KEY=...           # or OPENAI_API_KEY
export LLM_MODEL=anthropic/claude-3.5-sonnet   # pin a specific model for reproducibility

# single incident, one agent each
python baseline.py dataset/incidents/incident_001.json
python advanced.py dataset/incidents/incident_001.json

# full benchmark over the dataset
python evaluate.py

# render a markdown before/after table from the results (for the video/README)
python make_report_table.py
```

### Docker

```bash
docker build -t incident-resolver .
docker run -e OPENROUTER_API_KEY=... -e LLM_MODEL=... incident-resolver evaluate.py
```

### Tests

The tool layer and scoring logic are fully deterministic and require no
API key:

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## Dataset

`dataset/incidents/*.json` + matching `dataset/ground_truth/*.json` — 20
synthetic incidents: connection-pool exhaustion, downed cache, bad secret
rotation, CPU saturation from a feature flag, stuck circuit breaker, OOM
kill, memory leak from an unbounded cache, internal DNS failure, disk
full, an overly aggressive rate limit, an expired TLS cert, slow
downstream dependency, a missing distributed lock on a scaled cron job, a
blocking schema migration, a misconfigured load-balancer health check, a
poison message stalling a queue, NTP clock skew, a single-partner webhook
flood, an autoscaler capacity ceiling, and a missing cache invalidation
step. Each has a known root cause and a set of actions that would be
unsafe to auto-execute.

Note from validating the evidence pipeline: `incident_013` (duplicate
cron execution) only surfaces 1 deterministic evidence item, because its
symptoms show up as INFO/WARN log lines and the log analyzer only flags
ERROR/CRITICAL/FATAL by design. That's a real limitation of the current
tool set, not a bug — worth mentioning as a known gap or a candidate for
a follow-up tool if time allows.

## Evaluation results

Run `python evaluate.py` to regenerate. Numbers below are a placeholder
until the full benchmark run — see `evaluation_report.json` after running.

```
Baseline
  Accuracy        TBD%
  Unsafe actions  TBD
  Avg latency     TBDs

Advanced
  Accuracy        TBD%
  Unsafe actions  TBD
  Avg latency     TBDs

Improvement       TBDpp accuracy
```

## Improvement changelog

Each entry ties a change to the evidence that motivated it.

1. **Baseline established** — single-prompt diagnosis, no tools, no
   verification, no safety gate. Establishes the control group.
2. **(next)** — run `evaluate.py`, record baseline failure modes here.
3. **(next)** — advanced pipeline added: deterministic evidence
   collection + grounded diagnosis + verification pass + safety gate.
   Record the accuracy delta and *why* each stage moved the number.
4. **(next)** — record any experiment that was tried and reverted
   (the challenge explicitly asks for this — e.g. an attempted
   optimization that didn't pay off), with the evidence for removing it.

## Agent trajectories

`trajectories/<incident_id>_baseline.json` and
`trajectories/<incident_id>_advanced.json` are written by `evaluate.py`
for every incident/agent pair — full prompts, raw LLM responses, tool
outputs, the verification checkpoint, and any safety-gate escalation.

## Disclosure

Built with Claude (Anthropic) as a coding agent for scaffolding,
implementation, and iteration. Diagnosis/verification at runtime uses an
LLM via OpenRouter (or OpenAI) as configured above — model name and
provider are logged in each trajectory file for reproducibility.
