import httpx

API = "https://api.github.com"


async def fetch_diff(repo_full_name: str, pr_number: int, token: str) -> str:
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{API}/repos/{repo_full_name}/pulls/{pr_number}",
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3.diff",
            },
        )
        r.raise_for_status()
        return r.text


async def post_comment(repo_full_name: str, pr_number: int, body: str, token: str) -> None:
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{API}/repos/{repo_full_name}/issues/{pr_number}/comments",
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github+json",
            },
            json={"body": body},
        )
        r.raise_for_status()
