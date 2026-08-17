import httpx
import pytest
import respx

from app.github.client import fetch_diff, post_comment


@pytest.mark.asyncio
async def test_fetch_diff_returns_raw_text():
    fake_diff = "diff --git a/x b/x\n+ hello\n"
    with respx.mock(base_url="https://api.github.com") as router:
        route = router.get("/repos/foo/bar/pulls/7").mock(
            return_value=httpx.Response(200, text=fake_diff)
        )
        result = await fetch_diff("foo/bar", 7, token="fake-token")

    assert route.called
    assert result == fake_diff
    sent = route.calls[0].request
    assert sent.headers["authorization"] == "token fake-token"
    assert sent.headers["accept"] == "application/vnd.github.v3.diff"


@pytest.mark.asyncio
async def test_post_comment_posts_body():
    with respx.mock(base_url="https://api.github.com") as router:
        route = router.post("/repos/foo/bar/issues/7/comments").mock(
            return_value=httpx.Response(201, json={"id": 999})
        )
        await post_comment("foo/bar", 7, "hello from bot", token="fake-token")

    assert route.called
    sent_body = route.calls[0].request.content.decode()
    assert "hello from bot" in sent_body


@pytest.mark.asyncio
async def test_fetch_diff_raises_on_non_200():
    with respx.mock(base_url="https://api.github.com") as router:
        router.get("/repos/foo/bar/pulls/7").mock(
            return_value=httpx.Response(404, text="not found")
        )
        with pytest.raises(httpx.HTTPStatusError):
            await fetch_diff("foo/bar", 7, token="fake-token")
