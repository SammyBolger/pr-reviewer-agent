from app.main import _is_slash_command


def _make_payload(body: str, on_pr: bool = True) -> dict:
    issue = {"number": 1}
    if on_pr:
        issue["pull_request"] = {"url": "https://api.github.com/..."}
    return {
        "issue": issue,
        "comment": {"body": body},
    }


def test_slash_command_recognises_review_again():
    assert _is_slash_command(_make_payload("/review-again")) is True


def test_slash_command_recognises_review():
    assert _is_slash_command(_make_payload("/review please")) is True


def test_slash_command_ignores_regular_comments():
    assert _is_slash_command(_make_payload("looks good to me")) is False


def test_slash_command_ignores_comments_on_plain_issues():
    assert _is_slash_command(_make_payload("/review-again", on_pr=False)) is False


def test_slash_command_case_insensitive():
    assert _is_slash_command(_make_payload("/Review-Again")) is True


def test_slash_command_handles_whitespace():
    assert _is_slash_command(_make_payload("   /review-again  ")) is True
