"""Audit the actual BM25 retriever without generating or fabricating answers."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from domain_assistant import BM25Retriever, load_corpus
from template import RAGASEvaluator, rerank_by_overlap
from validate_golden_dataset import build_contract, validate_dataset


def main() -> int:
    dataset = json.loads((ROOT / "golden_dataset.json").read_text(encoding="utf-8"))
    errors, _ = validate_dataset(dataset, build_contract(ROOT / "data/technology_store"))
    if errors:
        raise ValueError("Invalid dataset: " + "; ".join(errors))
    corpus_id, chunks = load_corpus(ROOT / "data/technology_store")
    retriever = BM25Retriever(chunks)
    evaluator = RAGASEvaluator()
    rows = []
    for pair in dataset["qa_pairs"]:
        retrieved = retriever.retrieve(pair["question"], top_k=5)
        texts = [chunk.text for chunk in retrieved]
        # Rerank by the user question, never by the expected answer.
        reordered = rerank_by_overlap(texts, pair["question"])
        expected = pair["expected_answer"]
        rows.append({
            "id": pair["id"], "question": pair["question"],
            "context_recall": evaluator.evaluate_context_recall(texts, expected),
            "context_precision": evaluator.evaluate_context_precision(texts, expected),
            "recall_after": evaluator.evaluate_context_recall(reordered, expected),
            "precision_after": evaluator.evaluate_context_precision(reordered, expected),
            "retrieved_contexts": [{"source_doc": chunk.source_doc,
                                    "chunk_id": chunk.chunk_id, "text": chunk.text,
                                    "score": chunk.score} for chunk in retrieved],
        })
    artifact = {"scope": "retrieval_only_no_generated_answers", "corpus_id": corpus_id,
                "top_k": 5, "rerank_query": "question", "results": rows}
    output = ROOT / "artifacts/retrieval_audit.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Retrieval only: no answer-side scores or pass rate were measured.")
    print("| ID | Recall | Precision | Recall after | Precision after |")
    print("|---|---:|---:|---:|---:|")
    for row in rows:
        print(f"| {row['id']} | {row['context_recall']:.3f} | {row['context_precision']:.3f} "
              f"| {row['recall_after']:.3f} | {row['precision_after']:.3f} |")
    print(f"Saved: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
