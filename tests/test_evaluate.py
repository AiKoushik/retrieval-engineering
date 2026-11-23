import math

import pytest

from rx.evaluate import (Question, hit_rate_at_k, mrr_at_k, ndcg_at_k,
                         precision_at_k, recall_at_k, run_eval)
from rx.store import Hit

RANKED = ["a", "b", "a", "c"]     # doc_ids of retrieved chunks
GOLD = {"a", "c"}


def test_recall_precision_hit():
    assert recall_at_k(RANKED, GOLD, 2) == 0.5
    assert recall_at_k(RANKED, GOLD, 4) == 1.0
    assert precision_at_k(RANKED, GOLD, 4) == 0.75
    assert precision_at_k(RANKED, GOLD, 10) == 0.3   # k slots, not hits
    assert hit_rate_at_k(["x", "a"], GOLD, 1) == 0.0
    assert hit_rate_at_k(["x", "a"], GOLD, 2) == 1.0


def test_mrr():
    assert mrr_at_k(RANKED, GOLD, 10) == 1.0
    assert mrr_at_k(["x", "y", "c"], GOLD, 10) == pytest.approx(1 / 3)
    assert mrr_at_k(["x", "y", "c"], GOLD, 2) == 0.0


def test_ndcg_counts_each_document_once():
    dcg = 1 / math.log2(2) + 1 / math.log2(5)       # a at 1, c at 4
    idcg = 1 / math.log2(2) + 1 / math.log2(3)
    assert ndcg_at_k(RANKED, GOLD, 4) == pytest.approx(dcg / idcg)
    assert ndcg_at_k(["a", "c"], GOLD, 10) == pytest.approx(1.0)


def test_ndcg_graded():
    grades = {"a": 3.0, "c": 1.0}
    ideal = ndcg_at_k(["a", "c"], grades, 2)
    swapped = ndcg_at_k(["c", "a"], grades, 2)
    assert ideal == pytest.approx(1.0) and swapped < ideal


def test_empty_gold_rewards_an_empty_result():
    for metric in (recall_at_k, precision_at_k, mrr_at_k, ndcg_at_k,
                   hit_rate_at_k):
        assert metric([], [], 10) == 1.0
        assert metric(["a"], [], 10) == 0.0


def test_run_eval_groups_and_latency():
    questions = [Question("q1", "find a", "exact_code", ("a",), "x"),
                 Question("q2", "find c", "thread", ("c",), "y"),
                 Question("q3", "nothing", "abstain", (), "")]
    index = {"find a": ["a", "b"], "find c": ["b", "b"], "nothing": []}

    def fake(question, k):
        return [Hit(f"{d}#0", d, 1.0, "") for d in index[question][:k]]
    report = run_eval(fake, questions, ks=(1, 2))
    groups = report.groups
    assert list(groups) == ["all", "answerable", "abstain",
                            "exact_code", "thread"]
    assert groups["all"]["n"] == 3
    assert groups["answerable"]["recall@2"] == 0.5
    assert groups["abstain"]["recall@2"] == 1.0
    assert groups["all"]["p95_ms"] >= groups["all"]["p50_ms"] >= 0
    assert report.rows[0]["ranked"] == ["a", "b"]
