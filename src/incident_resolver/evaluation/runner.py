from __future__ import annotations

import json
from pathlib import Path

from incident_resolver.agents.advanced import run_advanced
from incident_resolver.agents.baseline import run_baseline
from incident_resolver.core.llm_client import LLMClient
from incident_resolver.models import GroundTruth, Incident
from incident_resolver.evaluation.metrics import RunMetrics, score_result

DATASET_DIR = Path(__file__).resolve().parents[3] / "dataset"


def load_dataset() -> list[tuple[Incident, GroundTruth]]:
    pairs = []
    incidents_dir = DATASET_DIR / "incidents"
    truth_dir = DATASET_DIR / "ground_truth"
    for incident_path in sorted(incidents_dir.glob("*.json")):
        truth_path = truth_dir / incident_path.name
        if not truth_path.exists():
            raise FileNotFoundError(f"Missing ground truth for {incident_path.name}")
        incident = Incident.model_validate_json(incident_path.read_text())
        truth = GroundTruth.model_validate_json(truth_path.read_text())
        pairs.append((incident, truth))
    return pairs


def run_evaluation(save_trajectories: bool = True) -> dict:
    client = LLMClient()
    dataset = load_dataset()

    baseline_metrics = RunMetrics(agent_name="baseline")
    advanced_metrics = RunMetrics(agent_name="advanced")

    traj_dir = Path(__file__).resolve().parents[3] / "trajectories"
    traj_dir.mkdir(exist_ok=True)

    for incident, truth in dataset:
        b_result = run_baseline(incident, client=client)
        score_result(b_result, truth, baseline_metrics)

        a_result = run_advanced(incident, client=client)
        score_result(a_result, truth, advanced_metrics)

        if save_trajectories:
            (traj_dir / f"{incident.id}_baseline.json").write_text(
                json.dumps(b_result.model_dump(), indent=2)
            )
            (traj_dir / f"{incident.id}_advanced.json").write_text(
                json.dumps(a_result.model_dump(), indent=2)
            )

    return {"baseline": baseline_metrics, "advanced": advanced_metrics}


def print_report(results: dict[str, RunMetrics]) -> None:
    b = results["baseline"].as_dict()
    a = results["advanced"].as_dict()
    improvement = a["accuracy_pct"] - b["accuracy_pct"]

    print("=" * 44)
    print("FRONTIER ENGINEERING EVALUATION")
    print("=" * 44)
    print("\nBaseline")
    print(f"  Accuracy        {b['accuracy_pct']}%  ({b['correct_root_cause']}/{b['total']})")
    print(f"  Unsafe actions  {b['unsafe_actions']}")
    print(f"  Avg latency     {b['avg_latency_seconds']}s")
    print("\nAdvanced")
    print(f"  Accuracy        {a['accuracy_pct']}%  ({a['correct_root_cause']}/{a['total']})")
    print(f"  Unsafe actions  {a['unsafe_actions']}")
    print(f"  Avg latency     {a['avg_latency_seconds']}s")
    print(f"\nImprovement       {improvement:+.1f}pp accuracy")
    print("=" * 44)


if __name__ == "__main__":
    results = run_evaluation()
    print_report(results)

    out_path = Path(__file__).resolve().parents[3] / "evaluation_report.json"
    out_path.write_text(
        json.dumps(
            {
                "baseline": results["baseline"].as_dict(),
                "advanced": results["advanced"].as_dict(),
                "baseline_per_incident": results["baseline"].per_incident,
                "advanced_per_incident": results["advanced"].per_incident,
            },
            indent=2,
        )
    )
    print(f"\nDetailed report written to {out_path}")
