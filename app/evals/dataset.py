from dataclasses import dataclass


@dataclass
class TestCase:
    id: str
    title: str
    description: str
    diff: str
    expected_categories: list[str]
    should_be_trivial: bool = False


CASES: list[TestCase] = [
    TestCase(
        id="trivial_typo",
        title="docs: fix typo in readme",
        description="Trivial README typo fix. The reviewer should raise no real concerns.",
        expected_categories=[],
        should_be_trivial=True,
        diff="""diff --git a/README.md b/README.md
index abc..def 100644
--- a/README.md
+++ b/README.md
@@ -1,5 +1,5 @@
 # my-app
-Welcom to the projct.
+Welcome to the project.

 ## Setup
""",
    ),
    TestCase(
        id="hardcoded_secret",
        title="feat: add prod db client",
        description="A hardcoded database credential in source. The reviewer must flag this as a security issue.",
        expected_categories=["security"],
        diff="""diff --git a/app/db/client.py b/app/db/client.py
new file mode 100644
index 0000000..abc1234
--- /dev/null
+++ b/app/db/client.py
@@ -0,0 +1,14 @@
+import psycopg2
+
+DB_HOST = "prod-primary.internal"
+DB_USER = "admin"
+DB_PASSWORD = "ProdMaster9!examplePlaceholder"
+
+
+def connect():
+    return psycopg2.connect(
+        host=DB_HOST,
+        user=DB_USER,
+        password=DB_PASSWORD,
+        dbname="app",
+    )
""",
    ),
    TestCase(
        id="off_by_one_bug",
        title="feat: pagination helper",
        description="An off-by-one indexing bug in a pagination helper. The reviewer should catch it as a bug or clarity issue.",
        expected_categories=["bug"],
        diff="""diff --git a/app/util/pagination.py b/app/util/pagination.py
new file mode 100644
index 0000000..abc9876
--- /dev/null
+++ b/app/util/pagination.py
@@ -0,0 +1,12 @@
+def paginate(items: list, page: int, per_page: int) -> list:
+    # page is 1-indexed
+    start = page * per_page
+    end = start + per_page
+    return items[start:end]
+
+
+def total_pages(items: list, per_page: int) -> int:
+    n = len(items)
+    if n == 0:
+        return 0
+    return n // per_page
""",
    ),
]
