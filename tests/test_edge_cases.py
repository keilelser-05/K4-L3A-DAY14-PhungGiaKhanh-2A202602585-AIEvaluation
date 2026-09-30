"""Boundary checks that the starter suite does not cover."""

import pytest

from template import BenchmarkRunner, EvalResult, FailureAnalyzer, LLMJudge, QAPair, RAGASEvaluator


def test_empty_tokens_and_empty_retrieval_have_explicit_semantics():
    evaluator = RAGASEvaluator()
    assert evaluator.evaluate_faithfulness("the", "") == 1.0
    assert evaluator.evaluate_relevance("", "the") == 1.0
    assert evaluator.evaluate_completeness("", "") == 1.0
    assert evaluator.evaluate_context_recall([], "") == 1.0
    assert evaluator.evaluate_context_recall([], "evidence") == 0.0
    assert evaluator.evaluate_context_precision([], "") == 1.0
    result = evaluator.run_full_eval("", "question", "", "expected", contexts=[])
    assert not result.passed
    assert result.context_recall == result.context_precision == 0.0
    assert result.failure_type == "irrelevant"


def test_failure_priority_and_preservation_of_metadata():
    evaluator = RAGASEvaluator()
    pair = QAPair("question", "expected", "evidence", {"id": "A01"})
    result = BenchmarkRunner().run([pair], lambda _: "unrelated", evaluator)[0]
    assert result.qa_pair is pair
    assert result.failure_type == "hallucination"


@pytest.mark.parametrize("raw, expected", [
    ('```json\n{"scores": {"accuracy": 0.8}}\n```', 0.8),
    ('{"accuracy": 2}', 1.0),
    ('{"accuracy": -1}', 0.0),
    ('{"accuracy": true}', 0.5),
    ('{"accuracy": NaN}', 0.5),
    ('{"accuracy": "excellent"}', 0.5),
    ('[]', 0.5),
    ('not json', 0.5),
])
def test_judge_validates_scores_and_preserves_raw_reasoning(raw, expected):
    result = LLMJudge(lambda _: raw).score_response("question", "answer", {"accuracy": "correct"})
    assert result["scores"] == {"accuracy": expected}
    assert result["reasoning"] == raw


def test_regression_threshold_is_strict_and_handles_floating_point():
    pair = QAPair("q", "a")
    baseline = [EvalResult(pair, "a", 0.9, 0.9, 0.9, True)]
    runner = BenchmarkRunner()
    at_boundary = [EvalResult(pair, "a", 0.85, 0.85, 0.85, True)]
    assert runner.run_regression(at_boundary, baseline)["passed"]
    below_boundary = [EvalResult(pair, "a", 0.849, 0.85, 0.85, True)]
    assert runner.run_regression(below_boundary, baseline)["regressions"] == ["faithfulness"]


def test_empty_reports_and_bias_batches_do_not_claim_measurements():
    report = BenchmarkRunner().generate_report([])
    assert report["total"] == 0
    assert report["avg_context_recall"] is None
    assert LLMJudge(lambda _: "{}").detect_bias([]) == {
        "positional_bias": False, "leniency_bias": False, "severity_bias": False,
    }
    assert FailureAnalyzer().generate_improvement_suggestions([]) == []


def test_root_cause_ties_and_markdown_escape():
    failure = EvalResult(QAPair("q", "a"), "a", 0.2, 0.2, 0.2, False, "incomplete")
    analyzer = FailureAnalyzer()
    assert analyzer.find_root_cause(failure) == "Multiple issues detected — review full pipeline"
    log = analyzer.generate_improvement_log([failure], ["Check A|B\nthen rerun"])
    assert "Check A\\|B then rerun" in log
