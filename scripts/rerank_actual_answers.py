"""Reproduce the bonus reranking experiment from saved real answer traces."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evaluate_answers import load_evaluation_inputs
from template import RAGASEvaluator, rerank_by_overlap


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--actual", type=Path, default=ROOT / "artifacts/actual_answers.json")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/reranking_results.json")
    args = parser.parse_args()
    pairs, _ = load_evaluation_inputs(ROOT / "golden_dataset.json", args.actual)
    if not pairs:
        raise ValueError("Reranking requires a non-empty evaluation dataset")
    evaluator = RAGASEvaluator()
    rows = []
    for pair in pairs:
        before = pair.retrieved_contexts
        after = rerank_by_overlap(before, pair.question)
        rows.append({
            "id": pair.metadata["id"],
            "recall_before": evaluator.evaluate_context_recall(before, pair.expected_answer),
            "recall_after": evaluator.evaluate_context_recall(after, pair.expected_answer),
            "precision_before": evaluator.evaluate_context_precision(before, pair.expected_answer),
            "precision_after": evaluator.evaluate_context_precision(after, pair.expected_answer),
        })
    source = args.actual.resolve()
    source_label = source.relative_to(ROOT).as_posix() if source.is_relative_to(ROOT) else source.name
    artifact = {"source": source_label, "query": "question", "same_chunks": True, "results": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for metric in ("recall_before", "recall_after", "precision_before", "precision_after"):
        print(f"{metric}: {sum(row[metric] for row in rows) / len(rows):.6f}")
    print(f"Saved {len(rows)} reranking cases: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
