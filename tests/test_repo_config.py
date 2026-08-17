from app.config_repo import RepoConfig, all_paths_skipped, diff_line_count


def test_all_paths_skipped_when_every_file_matches():
    files = ["docs/a.md", "docs/nested/b.md", "README.md"]
    patterns = ["docs/**", "*.md"]
    assert all_paths_skipped(files, patterns) is True


def test_all_paths_skipped_returns_false_when_one_file_does_not_match():
    files = ["docs/a.md", "app/foo.py"]
    patterns = ["docs/**"]
    assert all_paths_skipped(files, patterns) is False


def test_all_paths_skipped_returns_false_with_no_patterns():
    assert all_paths_skipped(["a.py"], []) is False


def test_all_paths_skipped_returns_false_with_no_files():
    assert all_paths_skipped([], ["*.md"]) is False


def test_diff_line_count_counts_added_and_removed():
    diff = """diff --git a/x b/x
--- a/x
+++ b/x
@@ -1,2 +1,3 @@
 kept
-removed
+added one
+added two
"""
    assert diff_line_count(diff) == 3


def test_repo_config_defaults():
    cfg = RepoConfig()
    assert cfg.skip_paths == []
    assert cfg.min_diff_lines == 0
    assert cfg.extra_instructions is None
