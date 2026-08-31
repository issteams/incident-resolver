# Video narration script — Incident Resolver

Read this roughly as written; segments map to what the challenge asks the
video to show. Target ~5 minutes total. Timings are suggestions.

## 1. The bottleneck (0:00–0:30)

"On-call engineers spend the first several minutes of every incident doing the same manual triage — reading logs, checking recent deploys, correlating metrics. It's slow, inconsistent, and error-prone under pressure. I built Incident Resolver to see whether an agent could do that first pass reliably, as long as it shows its work and a human stays in the loop for anything risky."

## 2. Baseline — the naive version (0:30–1:30)

"Here's the baseline: one LLM call, the whole incident dumped into a single prompt, no tools, no verification. On `incident_003` it diagnoses the root cause as `jwt_signature_mismatch` — which is wrong. The actual cause was `jwt_secret_mismatch`. Confidence: 100%. No evidence shown, no way to check its work."

[Screen: run `python baseline.py dataset/incidents/incident_003.json`, show output]

## 3. Realistic execution — the advanced pipeline (1:30–3:00)

"Now the advanced agent on the same incident, `incident_003`. First, four deterministic tools run — log analyzer, metrics analyzer, config checker, deployment-history checker — and produce a structured evidence list. No LLM call yet, so this part is fast and 100% reproducible."

[Screen: show the evidence_collection trajectory step — the list of Evidence items]

"That evidence gets handed to the LLM, which has to cite which evidence indices support its diagnosis — it can't just assert a root cause out of thin air."

"Then a second LLM pass — a skeptical reviewer — audits that diagnosis against the evidence. On this incident it returned: \"confirm\", reason: \"All cited evidence indices exist and directly support the diagnosis. The log error, high error rate, and recent secret rotation strongly corroborate the JWT secret mismatch.\". That's the feedback-and-retry loop the challenge asks for — the agent isn't just trusting its first guess."

"Result: root cause `jwt_secret_mismatch`, confidence 90%, correctly matching ground truth."

"[If you have an incident where baseline's recommended action would be destructive — drop table, rm -rf, etc. — show it here. None triggered in this run, which is worth saying honestly rather than manufacturing one.]"

## 4. Final comparison (3:00–4:00)

[Screen: the table below, or run `python make_report_table.py`]

| Metric | Baseline | Advanced | Delta |
|---|---|---|---|
| Accuracy | 15.0% (3/20) | 10.0% (2/20) | -5.0pp |
| Unsafe actions | 0 | 0 | +0 |
| Avg latency | 2.21s | 3.74s | +1.53s |

"Across 20 synthetic incidents, the advanced pipeline improved accuracy by -5.0 percentage points. That cost us +1.53 seconds of latency per incident — two extra LLM calls for evidence-grounding and verification. For an on-call triage tool, I'd take that trade every time."

## 5. Improvement changelog (4:00–4:45)

"**Most impactful change:** grounding the LLM's diagnosis in the deterministic evidence list instead of letting it reason freely over raw logs. [Fill in with your actual before/after numbers for this specific change if you A/B'd it.]"

"**An experiment I tried and removed:** [describe the one thing you tried that didn't help — e.g. \"I tried adding a response cache keyed on incident summary text to cut latency. It didn't change accuracy but meant near-duplicate incidents with different root causes got the same stale diagnosis, so I reverted it.\" Use whatever you actually tried — this is the part judges specifically want to see and it's easy to fake badly, so keep it real.]"

## 6. Close (4:45–5:00)

"Full trajectories for every incident and both agents are in the repo under `trajectories/` — prompts, tool outputs, the verification checkpoint, and any safety escalations, so this is fully reproducible from the README."
