"""The worked examples printed in chapter 3, checked against the code."""
from __future__ import annotations

import pytest

from rx.evaluate import (hit_rate_at_k, mrr_at_k, ndcg_at_k,
                         precision_at_k, recall_at_k)

# The illustrative ranking of chapter 3's metrics figure: ten results,
# relevant at ranks 1, 4 and 10.
RANKED = ["TR-7731", "TR-7740", "EML-0179", "SPEC-112-C", "SPEC-112-B",
          "TR-7741", "NOTICE-2026-Q3", "EML-0174", "8D-2026-01",
          "SPEC-112-D"]
GOLD = {"TR-7731", "SPEC-112-C", "SPEC-112-D"}


def test_figure_example_at_5_and_10():
    assert precision_at_k(RANKED, GOLD, 5) == pytest.approx(0.4)
    assert recall_at_k(RANKED, GOLD, 5) == pytest.approx(2 / 3)
    assert hit_rate_at_k(RANKED, GOLD, 5) == 1.0
    assert mrr_at_k(RANKED, GOLD, 5) == 1.0
    assert ndcg_at_k(RANKED, GOLD, 5) == pytest.approx(0.671, abs=5e-4)
    assert recall_at_k(RANKED, GOLD, 10) == 1.0
    assert precision_at_k(RANKED, GOLD, 10) == pytest.approx(0.3)
    assert ndcg_at_k(RANKED, GOLD, 10) == pytest.approx(0.807, abs=5e-4)


def test_episode_example_ranks_3_and_6():
    ranked = [f"d{i}" for i in range(1, 11)]
    gold = {"d3", "d6"}
    assert recall_at_k(ranked, gold, 10) == 1.0
    assert precision_at_k(ranked, gold, 10) == pytest.approx(0.2)
    assert mrr_at_k(ranked, gold, 10) == pytest.approx(1 / 3)
    assert ndcg_at_k(ranked, gold, 10) == pytest.approx(0.525, abs=5e-4)


def test_graded_override_example():
    grades = {"NOTICE-2026-Q3": 2.0, "SPEC-112-C": 1.0}
    notice_first = ["NOTICE-2026-Q3", "SPEC-112-C", "SPEC-112-B"]
    spec_first = ["SPEC-112-C", "NOTICE-2026-Q3", "SPEC-112-B"]
    binary = set(grades)
    assert ndcg_at_k(notice_first, binary, 3) == ndcg_at_k(
        spec_first, binary, 3) == pytest.approx(1.0)
    assert ndcg_at_k(notice_first, grades, 3) == pytest.approx(1.0)
    assert ndcg_at_k(spec_first, grades, 3) == pytest.approx(
        0.860, abs=5e-4)


def test_repeated_chunks_do_not_inflate():
    ranked = ["TR-7731", "TR-7731", "TR-7731"]
    assert recall_at_k(ranked, {"TR-7731", "EML-0180"}, 3) == 0.5
    assert precision_at_k(ranked, {"TR-7731"}, 3) == 1.0
    assert ndcg_at_k(ranked, {"TR-7731", "EML-0180"}, 3) < 1.0


def test_abstain_rewards_only_silence():
    assert recall_at_k([], (), 10) == 1.0
    assert recall_at_k(["NCR-2026-002"], (), 10) == 0.0
