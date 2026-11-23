"""Retrieval metrics and the evaluation loop behind the scoreboard.

Relevance is judged per document: a retrieved chunk is relevant when
its doc_id is one of the question's gold documents. Metrics take the
ranked list of doc_ids of the retrieved chunks, best first.

Questions with no gold documents (type "abstain") have nothing to
find. For them every metric is 1.0 if the retriever returned nothing
and 0.0 otherwise: an honest "not found" is the only right result.
"""
from __future__ import annotations

import json
import math
import time
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from rx import config

Gold = Collection[str] | Mapping[str, float]


# region: question-dataclass
@dataclass(frozen=True)
class Question:
    qid: str
    question: str
    qtype: str                         # <1>
    gold_doc_ids: tuple[str, ...]      # <2>
    answer: str                        # <3>


def load_golden(path: Path | None = None) -> list[Question]:
    """Read golden.jsonl into Question objects."""
    with Path(path or config.GOLDEN_PATH).open(encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    return [Question(r["qid"], r["question"], r["qtype"],
                     tuple(r["gold_doc_ids"]), r["answer"])
            for r in rows]
# endregion: question-dataclass


# region: recall-precision
def recall_at_k(ranked: Sequence[str], gold: Gold, k: int) -> float:
    """Share of the gold documents that appear in the top k."""
    if not gold:
        return float(not ranked[:k])                    # <1>
    return len(set(ranked[:k]) & set(gold)) / len(gold)  # <2>


def precision_at_k(ranked: Sequence[str], gold: Gold,
                   k: int) -> float:
    """Share of the k result slots that hold a gold document."""
    if not gold:
        return float(not ranked[:k])
    return sum(doc in gold for doc in ranked[:k]) / k    # <3>


def hit_rate_at_k(ranked: Sequence[str], gold: Gold,
                  k: int) -> float:
    """1.0 if any gold document is in the top k, else 0.0."""
    if not gold:
        return float(not ranked[:k])
    return float(any(doc in gold for doc in ranked[:k]))  # <4>
# endregion: recall-precision


# region: mrr
def mrr_at_k(ranked: Sequence[str], gold: Gold, k: int) -> float:
    """1 / rank of the first gold document in the top k, else 0."""
    if not gold:
        return float(not ranked[:k])
    for rank, doc in enumerate(ranked[:k], start=1):   # <1>
        if doc in gold:
            return 1.0 / rank                          # <2>
    return 0.0                                         # <3>
# endregion: mrr


# region: ndcg
def ndcg_at_k(ranked: Sequence[str], gold: Gold, k: int) -> float:
    """Normalised discounted cumulative gain with linear gains.

    `gold` may map doc_id -> grade (graded relevance) or simply list
    doc_ids (every grade 1). A document earns its gain only the
    first time it appears, so repeated chunks are not rewarded.
    """
    if not gold:
        return float(not ranked[:k])
    grades = (dict(gold) if isinstance(gold, Mapping)
              else dict.fromkeys(gold, 1.0))           # <1>
    dcg, seen = 0.0, set()
    for i, doc in enumerate(ranked[:k]):
        if doc in grades and doc not in seen:          # <2>
            seen.add(doc)
            dcg += grades[doc] / math.log2(i + 2)      # <3>
    ideal = sorted(grades.values(), reverse=True)[:k]  # <4>
    idcg = sum(g / math.log2(i + 2) for i, g in enumerate(ideal))
    return dcg / idcg if idcg else 0.0
# endregion: ndcg


METRICS = {"recall": recall_at_k, "precision": precision_at_k,
           "mrr": mrr_at_k, "ndcg": ndcg_at_k, "hit": hit_rate_at_k}


# region: run-eval
RetrieveFn = Callable[[str, int], Sequence]   # returns Hits


@dataclass
class EvalReport:
    rows: list[dict]               # one per question
    groups: dict[str, dict]        # "all", "answerable", each qtype


def score_question(ranked: Sequence[str], gold: Gold,
                   ks: Sequence[int]) -> dict[str, float]:
    return {f"{name}@{k}": fn(ranked, gold, k)
            for name, fn in METRICS.items() for k in ks}


def run_eval(retrieve_fn: RetrieveFn, questions: Sequence[Question],
             ks: Sequence[int] = (5, 10, 20)) -> EvalReport:
    """Retrieve once per question at max(ks); score every cutoff."""
    depth = max(ks)                                    # <1>
    rows = []
    for q in questions:
        started = time.perf_counter()
        hits = retrieve_fn(q.question, depth)
        latency_ms = (time.perf_counter() - started) * 1000  # <2>
        ranked = [hit.doc_id for hit in hits]          # <3>
        rows.append({"qid": q.qid, "qtype": q.qtype,
                     "latency_ms": latency_ms, "ranked": ranked,  # <4>
                     **score_question(ranked, q.gold_doc_ids, ks)})
    return EvalReport(rows, aggregate(rows))
# endregion: run-eval


# region: aggregate
def summarize(rows: list[dict]) -> dict[str, float]:
    """Mean of every metric, plus latency percentiles."""
    names = [key for key in rows[0] if "@" in key]
    latency = [row["latency_ms"] for row in rows]
    summary = {"n": len(rows)}
    summary |= {name: float(np.mean([r[name] for r in rows]))  # <1>
                for name in names}
    summary["p50_ms"] = float(np.percentile(latency, 50))
    summary["p95_ms"] = float(np.percentile(latency, 95))      # <2>
    return summary


def aggregate(rows: list[dict]) -> dict[str, dict]:
    """Group rows: all questions, answerable ones, each qtype."""
    groups = {"all": rows,
              "answerable": [r for r in rows if r["qtype"] != "abstain"]}
    for qtype in sorted({r["qtype"] for r in rows}):    # <3>
        groups[qtype] = [r for r in rows if r["qtype"] == qtype]
    return {name: summarize(group)
            for name, group in groups.items() if group}
# endregion: aggregate
