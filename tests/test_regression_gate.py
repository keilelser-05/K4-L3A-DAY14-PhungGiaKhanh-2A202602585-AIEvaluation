"""The offline gate must reject regressions and incomparable baseline cases."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_gate(baseline: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts/regression_gate.py"), "--baseline", str(baseline)],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )


def test_gate_blocks_a_measured_average_drop(tmp_path):
    baseline = json.loads((ROOT / "artifacts/benchmark_results.json").read_text(encoding="utf-8"))
    for record in baseline["results"]:
        record["faithfulness"] = 1.0
    path = tmp_path / "higher_baseline.json"
    path.write_text(json.dumps(baseline), encoding="utf-8")
    outcome = run_gate(path)
    assert outcome.returncode == 1
    assert json.loads(outcome.stdout)["regressions"] == ["faithfulness"]


def test_gate_rejects_baseline_question_mismatch(tmp_path):
    baseline = json.loads((ROOT / "artifacts/benchmark_results.json").read_text(encoding="utf-8"))
    baseline["results"][0]["question"] = "A different question"
    path = tmp_path / "mismatched_baseline.json"
    path.write_text(json.dumps(baseline), encoding="utf-8")
    outcome = run_gate(path)
    assert outcome.returncode == 2
    assert "IDs/questions do not match" in outcome.stdout


def test_gate_rejects_nonfinite_baseline_score(tmp_path):
    baseline = json.loads((ROOT / "artifacts/benchmark_results.json").read_text(encoding="utf-8"))
    baseline["results"][0]["faithfulness"] = float("nan")
    path = tmp_path / "invalid_baseline.json"
    path.write_text(json.dumps(baseline), encoding="utf-8")
    outcome = run_gate(path)
    assert outcome.returncode == 2
    assert "Invalid baseline score" in outcome.stdout
