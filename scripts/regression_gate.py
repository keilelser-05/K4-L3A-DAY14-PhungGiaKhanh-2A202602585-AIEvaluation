"""Replay frozen RAG answers and block evaluation-metric regressions > 0.05.

This checks evaluation-code changes offline, without requesting fresh LLM answers.
For prompt/model/retriever changes, generate a separate candidate answer artifact.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evaluate_answers import load_evaluation_inputs
from template import BenchmarkRunner, EvalResult, RAGASEvaluator
from validate_golden_dataset import build_contract, validate_dataset


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--actual", type=Path, default=ROOT / "artifacts/actual_answers.json")
    parser.add_argument("--baseline", type=Path, default=ROOT / "artifacts/benchmark_results.json")
    args = parser.parse_args()
    try:
        golden = ROOT / "golden_dataset.json"
        dataset = json.loads(golden.read_text(encoding="utf-8"))
        errors, _ = validate_dataset(dataset, build_contract(ROOT / "data/technology_store"))
        if errors:
            raise ValueError("Dataset validation failed: " + "; ".join(errors))
        pairs, answers = load_evaluation_inputs(golden, args.actual)
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))["results"]
        if not pairs or len(pairs) != len(baseline):
            raise ValueError("Candidate and baseline must have the same non-empty case count")
        baseline_results = []
        for pair, record in zip(pairs, baseline):
            if record["id"] != pair.metadata["id"] or record["question"] != pair.question:
                raise ValueError("Candidate and baseline case IDs/questions do not match")
            for metric in ("faithfulness", "relevance", "completeness"):
                value = record[metric]
                if (not isinstance(value, (int, float)) or isinstance(value, bool)
                        or not math.isfinite(value) or not 0.0 <= value <= 1.0):
                    raise ValueError(f"Invalid baseline score: {record['id']}.{metric}")
            baseline_results.append(EvalResult(
                pair, record["actual_answer"], record["faithfulness"],
                record["relevance"], record["completeness"], record["passed"],
                record["failure_type"], record.get("context_precision"), record.get("context_recall"),
            ))
        runner = BenchmarkRunner()
        results = runner.run(pairs, answers.__getitem__, RAGASEvaluator())
        report = runner.run_regression(results, baseline_results)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print("ERROR:", exc)
        return 2
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
