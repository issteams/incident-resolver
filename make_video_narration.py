#!/usr/bin/env python
"""python make_video_narration.py

Reads evaluation_report.json + trajectories/*.json and writes
video_narration.md — a read-on-camera script structured to match what the
challenge asks the video to show: baseline -> realistic execution ->
final comparison -> changelog (most impactful change + an experiment
that was removed).

Run this AFTER evaluate.py has produced evaluation_report.json and
trajectories/. Safe to re-run any time you get fresh numbers.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPORT_PATH = ROOT / "evaluation_report.json"
TRAJ_DIR = ROOT / "trajectories"
OUT_PATH = ROOT / "video_narration.md"


def load_report() -> dict:
    if not REPORT_PATH.exists():
        raise SystemExit("evaluation_report.json not found — run `python evaluate.py` first.")
    return json.loads(REPORT_PATH.read_text())


def load_trajectory(incident_id: str, agent: str) -> list[dict] | None:
    path = TRAJ_DIR / f"{incident_id}_{agent}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return data.get("raw_trajectory", [])


def pick_hero_incident(report: dict) -> str | None:
    """Pick the incident where baseline got it wrong and advanced got it
    right — the clearest possible demonstration of the improvement."""
    b_by_id = {r["incident_id"]: r for r in report["baseline_per_incident"]}
    a_by_id = {r["incident_id"]: r for r in report["advanced_per_incident"]}
    candidates = [
        iid for iid in b_by_id
        if not b_by_id[iid]["correct"] and a_by_id.get(iid, {}).get("correct")
    ]
    if not candidates:
        # fall back to any incident both got right, or just the first one
        candidates = list(b_by_id.keys())
    # prefer one where advanced's confidence is high (clean demo)
    candidates.sort(key=lambda iid: a_by_id[iid].get("confidence", 0), reverse=True)
    return candidates[0] if candidates else None


def pick_unsafe_incident(report: dict) -> str | None:
    """Pick an incident where baseline recommended something the safety
    gate would have blocked, if one exists — great for the safety beat."""
    b_by_id = {r["incident_id"]: r for r in report["baseline_per_incident"]}
    for iid, r in b_by_id.items():
        if r.get("unsafe"):
            return iid
    return None


def find_verification_revision(incident_id: str) -> dict | None:
    """Look for a case where the verifier revised the confidence — good
    evidence of the 'feedback and retries' the trajectories should show."""
    traj = load_trajectory(incident_id, "advanced")
    if not traj:
        return None
    for step in traj:
        if step.get("step") == "verification_verdict":
            return step["content"]
    return None


def find_safety_escalation(incident_id: str) -> str | None:
    traj = load_trajectory(incident_id, "advanced")
    if not traj:
        return None
    for step in traj:
        if step.get("role") == "safety_gate":
            return step["content"]
    return None


def render(report: dict) -> str:
    b, a = report["baseline"], report["advanced"]
    delta = a["accuracy_pct"] - b["accuracy_pct"]

    hero_id = pick_hero_incident(report)
    unsafe_id = pick_unsafe_incident(report)
    b_by_id = {r["incident_id"]: r for r in report["baseline_per_incident"]}
    a_by_id = {r["incident_id"]: r for r in report["advanced_per_incident"]}

    lines: list[str] = []
    lines.append("# Video narration script — Incident Resolver")
    lines.append("")
    lines.append("Read this roughly as written; segments map to what the challenge asks the")
    lines.append("video to show. Target ~5 minutes total. Timings are suggestions.")
    lines.append("")

    # --- Segment 1: the bottleneck ---
    lines.append("## 1. The bottleneck (0:00–0:30)")
    lines.append("")
    lines.append(
        '"On-call engineers spend the first several minutes of every incident doing '
        'the same manual triage — reading logs, checking recent deploys, correlating '
        'metrics. It\'s slow, inconsistent, and error-prone under pressure. I built '
        'Incident Resolver to see whether an agent could do that first pass reliably, '
        'as long as it shows its work and a human stays in the loop for anything risky."'
    )
    lines.append("")

    # --- Segment 2: baseline demo ---
    lines.append("## 2. Baseline — the naive version (0:30–1:30)")
    lines.append("")
    if hero_id and hero_id in b_by_id:
        br = b_by_id[hero_id]
        verdict_phrase = "which happens to be right" if br["correct"] else "which is wrong"
        wrong_note = "" if br["correct"] else f"The actual cause was `{br['true_root_cause']}`. "
        lines.append(
            f'"Here\'s the baseline: one LLM call, the whole incident dumped into a '
            f'single prompt, no tools, no verification. On `{hero_id}` it diagnoses the '
            f'root cause as `{br["predicted_root_cause"]}` — '
            f'{verdict_phrase}. {wrong_note}'
            f'Confidence: {br["confidence"]:.0%}. No evidence shown, no way to check its work."'
        )
    else:
        lines.append(
            '"Here\'s the baseline: one LLM call, the whole incident dumped into a '
            'single prompt, no tools, no verification, no evidence trail."'
        )
    lines.append("")
    lines.append(f"[Screen: run `python baseline.py dataset/incidents/{hero_id}.json`, show output]")
    lines.append("")

    # --- Segment 3: realistic execution (advanced) ---
    lines.append("## 3. Realistic execution — the advanced pipeline (1:30–3:00)")
    lines.append("")
    if hero_id and hero_id in a_by_id:
        ar = a_by_id[hero_id]
        lines.append(
            f'"Now the advanced agent on the same incident, `{hero_id}`. First, four '
            f'deterministic tools run — log analyzer, metrics analyzer, config checker, '
            f'deployment-history checker — and produce a structured evidence list. No '
            f'LLM call yet, so this part is fast and 100% reproducible."'
        )
        lines.append("")
        lines.append("[Screen: show the evidence_collection trajectory step — the list of Evidence items]")
        lines.append("")
        lines.append(
            '"That evidence gets handed to the LLM, which has to cite which evidence '
            'indices support its diagnosis — it can\'t just assert a root cause out of thin air."'
        )
        lines.append("")

        verdict = find_verification_revision(hero_id)
        if verdict:
            lines.append(
                f'"Then a second LLM pass — a skeptical reviewer — audits that diagnosis '
                f'against the evidence. On this incident it returned: '
                f'\\"{verdict.get("verdict", "?")}\\", reason: \\"{verdict.get("reason", "")}\\". '
                f'That\'s the feedback-and-retry loop the challenge asks for — the agent '
                f'isn\'t just trusting its first guess."'
            )
        else:
            lines.append(
                '"Then a second LLM pass — a skeptical reviewer — audits that diagnosis '
                'against the evidence before it\'s finalized."'
            )
        lines.append("")
        lines.append(
            f'"Result: root cause `{ar["predicted_root_cause"]}`, confidence '
            f'{ar["confidence"]:.0%}'
            f'{", correctly matching ground truth" if ar["correct"] else ""}."'
        )
    lines.append("")

    if unsafe_id:
        esc = find_safety_escalation(unsafe_id)
        lines.append(
            f'"One more piece: on `{unsafe_id}`, the baseline recommended an action our '
            f'safety gate would flag as destructive. The advanced agent\'s deterministic '
            f'safety gate '
            f'{"escalated the risk level and forced human approval" if esc else "forces human approval on anything medium-risk or above"}'
            f' — this can\'t be talked out of it by the LLM, it\'s a hard rule."'
        )
        lines.append("")
        lines.append(f"[Screen: run `python advanced.py dataset/incidents/{unsafe_id}.json`, show the [HUMAN APPROVAL REQUIRED] block]")
    else:
        lines.append(
            '"[If you have an incident where baseline\'s recommended action would be '
            'destructive — drop table, rm -rf, etc. — show it here. None triggered in '
            'this run, which is worth saying honestly rather than manufacturing one.]"'
        )
    lines.append("")

    # --- Segment 4: final comparison ---
    lines.append("## 4. Final comparison (3:00–4:00)")
    lines.append("")
    lines.append("[Screen: the table below, or run `python make_report_table.py`]")
    lines.append("")
    lines.append("| Metric | Baseline | Advanced | Delta |")
    lines.append("|---|---|---|---|")
    lines.append(
        f"| Accuracy | {b['accuracy_pct']}% ({b['correct_root_cause']}/{b['total']}) "
        f"| {a['accuracy_pct']}% ({a['correct_root_cause']}/{a['total']}) | {delta:+.1f}pp |"
    )
    lines.append(f"| Unsafe actions | {b['unsafe_actions']} | {a['unsafe_actions']} | {a['unsafe_actions'] - b['unsafe_actions']:+d} |")
    lines.append(f"| Avg latency | {b['avg_latency_seconds']}s | {a['avg_latency_seconds']}s | {a['avg_latency_seconds'] - b['avg_latency_seconds']:+.2f}s |")
    lines.append("")
    unsafe_note = (
        f", and eliminated {b['unsafe_actions']} unsafe recommendations"
        if b["unsafe_actions"] else ""
    )
    lines.append(
        f'"Across {b["total"]} synthetic incidents, the advanced pipeline improved '
        f'accuracy by {delta:+.1f} percentage points{unsafe_note}. That cost us '
        f'{a["avg_latency_seconds"] - b["avg_latency_seconds"]:+.2f} seconds of latency '
        f'per incident — two extra LLM calls for evidence-grounding and verification. '
        f'For an on-call triage tool, I\'d take that trade every time."'
    )
    lines.append("")

    # --- Segment 5: changelog ---
    lines.append("## 5. Improvement changelog (4:00–4:45)")
    lines.append("")
    lines.append(
        '"**Most impactful change:** grounding the LLM\'s diagnosis in the deterministic '
        'evidence list instead of letting it reason freely over raw logs. [Fill in with '
        'your actual before/after numbers for this specific change if you A/B\'d it.]"'
    )
    lines.append("")
    lines.append(
        '"**An experiment I tried and removed:** [describe the one thing you tried that '
        'didn\'t help — e.g. \\"I tried adding a response cache keyed on incident '
        'summary text to cut latency. It didn\'t change accuracy but meant near-duplicate '
        'incidents with different root causes got the same stale diagnosis, so I '
        'reverted it.\\" Use whatever you actually tried — this is the part judges '
        'specifically want to see and it\'s easy to fake badly, so keep it real.]"'
    )
    lines.append("")

    # --- Segment 6: close ---
    lines.append("## 6. Close (4:45–5:00)")
    lines.append("")
    lines.append(
        '"Full trajectories for every incident and both agents are in the repo under '
        '`trajectories/` — prompts, tool outputs, the verification checkpoint, and any '
        'safety escalations, so this is fully reproducible from the README."'
    )
    lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    report = load_report()
    script = render(report)
    OUT_PATH.write_text(script)
    print(f"Wrote {OUT_PATH}")
    print("\n--- preview ---\n")
    print(script[:2000])
