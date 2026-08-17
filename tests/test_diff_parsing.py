from app.agent.graph import _build_query, _changed_files


def test_changed_files_from_multi_file_diff():
    diff = """diff --git a/app/foo.py b/app/foo.py
index 111..222 100644
+++ b/app/foo.py
@@ -1 +1 @@
-x
+y
diff --git a/README.md b/README.md
+++ b/README.md
+hello
"""
    assert _changed_files(diff) == ["app/foo.py", "README.md"]


def test_changed_files_deduplicates_preserves_order():
    diff = """diff --git a/a b/a
diff --git a/b b/b
diff --git a/a b/a
"""
    assert _changed_files(diff) == ["a", "b"]


def test_build_query_includes_title_and_files():
    diff = "diff --git a/app/x.py b/app/x.py\n"
    q = _build_query("cool refactor", diff)
    assert "cool refactor" in q
    assert "app/x.py" in q


def test_build_query_falls_back_to_title_when_no_files():
    q = _build_query("only title", "malformed diff without header")
    assert q == "only title"
