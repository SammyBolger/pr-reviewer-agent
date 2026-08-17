from app.review.chunking import aggregate_reviews, chunk_file_diffs, split_diff_by_file
from app.review.schemas import Concern, Review


TWO_FILE_DIFF = """diff --git a/a.py b/a.py
--- a/a.py
+++ b/a.py
@@ -1 +1 @@
-x
+y
diff --git a/b.py b/b.py
--- a/b.py
+++ b/b.py
@@ -1 +1 @@
-x
+y
"""


def test_split_diff_by_file():
    parts = split_diff_by_file(TWO_FILE_DIFF)
    assert len(parts) == 2
    assert parts[0].startswith("diff --git a/a.py")
    assert parts[1].startswith("diff --git a/b.py")


def test_split_diff_by_file_empty():
    assert split_diff_by_file("") == []


def test_chunk_file_diffs_groups_under_max():
    files = ["a" * 40, "b" * 40, "c" * 40]
    chunks = chunk_file_diffs(files, max_chars=100)
    # 40 + 40 = 80 fits; adding 40 more would be 120 > 100, so third goes in a new chunk
    assert len(chunks) == 2
    assert len(chunks[0]) == 80
    assert len(chunks[1]) == 40


def test_chunk_file_diffs_single_file_over_max_stays_in_own_chunk():
    files = ["x" * 500]
    chunks = chunk_file_diffs(files, max_chars=100)
    assert chunks == ["x" * 500]


def test_aggregate_reviews_concats_and_takes_min_confidence():
    r1 = Review(summary="first chunk", changes=["a"], strengths=["s1"], confidence=0.9)
    r2 = Review(
        summary="second chunk", changes=["b"], strengths=["s2"], confidence=0.7,
        concerns=[Concern(severity="low", category="bug", file="x.py", description="x")],
    )
    merged = aggregate_reviews([r1, r2])
    assert merged.confidence == 0.7
    assert merged.changes == ["a", "b"]
    assert merged.strengths == ["s1", "s2"]
    assert len(merged.concerns) == 1
    assert "aggregated across 2" in merged.summary


def test_aggregate_reviews_passes_through_single():
    r = Review(summary="only one", changes=["a"], confidence=0.8)
    assert aggregate_reviews([r]) is r
