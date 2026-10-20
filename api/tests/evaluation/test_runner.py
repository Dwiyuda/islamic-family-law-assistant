import hashlib

from app.evaluation.gold import GoldItem
from app.evaluation.runner import evaluate, markdown_table, run_configuration_section
from app.retrieval.retriever import METHODS

GOLD = [
    GoldItem(qid="cerai-001", question="alasan perceraian taklik talak", topic="perceraian",
             relevant_chunk_ids=["khi-1991:pasal-116"]),
    GoldItem(qid="waris-001", question="bagian anak perempuan seorang", topic="kewarisan",
             relevant_chunk_ids=["khi-1991:pasal-176"]),
    GoldItem(qid="luar-001", question="hukuman pencurian motor", topic="luar_domain",
             relevant_chunk_ids=[]),
]


def test_evaluate_shapes_and_values(retriever):  # `retriever` fixture: api/tests/conftest.py
    results = evaluate(retriever, GOLD)
    assert set(results["methods"]) == set(METHODS)
    bm25 = results["methods"]["bm25"]
    assert bm25["n"] == 2 and bm25["recall@5"] == 1.0 and bm25["mrr@10"] == 1.0
    assert len(bm25["per_question"]) == 2
    for row in bm25["per_question"]:
        assert isinstance(row["top10"], list) and "top5" not in row
    assert [r["qid"] for r in results["rerank_top"]] == ["cerai-001", "waris-001", "luar-001"]
    assert results["rerank_top"][2]["in_domain"] is False


def test_markdown_table(retriever):
    table = markdown_table(evaluate(retriever, GOLD, methods=("bm25",)))
    assert table.splitlines()[0] == "| Method | Recall@5 | MRR@10 | nDCG@10 |"
    assert "| bm25 | 1.000 | 1.000 | 1.000 |" in table


def test_hybrid_rerank_searches_in_domain_questions_once_per_method(retriever):
    # Controller ruling: rerank_top must reuse the hybrid_rerank per-question search
    # for in-domain questions instead of re-searching. With 4 METHODS x 2 in-domain
    # questions, plus one extra top_k=1 search for the single out-of-domain question,
    # total search calls == 4*2 + 1 == 9.
    calls = 0
    original_search = retriever.search

    def counting_search(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original_search(*args, **kwargs)

    retriever.search = counting_search
    evaluate(retriever, GOLD)
    assert calls == 4 * 2 + 1


def test_run_configuration_section_reports_facts(tmp_path):
    chunks_path = tmp_path / "chunks.jsonl"
    chunks_path.write_bytes(b'{"chunk_id": "a"}\n')
    digest = hashlib.sha256(chunks_path.read_bytes()).hexdigest()
    fake_versions = {"FlagEmbedding": "1.4.2", "torch": "2.6.0+cu124",
                     "qdrant-client": "1.19.1", "rank-bm25": "0.2.2"}

    section = run_configuration_section("cpu", 8, chunks_path, reranker_max_length=512,
                                        versions=fake_versions, today="2026-09-28")

    assert section.startswith("## Run configuration")
    assert "device: `cpu`, threads: 8" in section
    assert "reranker max_length: 512" in section
    assert "RERANK_CANDIDATES: 30, TOP_K: 8" in section
    assert "FlagEmbedding 1.4.2" in section and "torch 2.6.0+cu124" in section
    assert digest in section
    assert "date: 2026-09-28" in section
