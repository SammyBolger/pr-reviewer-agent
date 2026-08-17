"""
MCP server that exposes pr-reviewer-agent data to any MCP client (Claude Desktop, Cursor, etc.).

Run with:
    python -m app.mcp_server

Then add to Claude Desktop's config as an MCP server.
"""

from mcp.server.mcpserver import MCPServer
from sqlalchemy import desc, func, select

from app.db.models import ReviewRecord
from app.db.session import SessionLocal, init_db

server = MCPServer(
    name="pr-reviewer-agent",
    description="Query the pr-reviewer-agent's review history, cost, and stats.",
)


@server.tool(description="List the most recent PR reviews the agent has posted.")
async def list_recent_reviews(limit: int = 10) -> list[dict]:
    async with SessionLocal() as session:
        rows = (
            await session.execute(
                select(ReviewRecord).order_by(desc(ReviewRecord.created_at)).limit(limit)
            )
        ).scalars().all()

    return [
        {
            "repo": r.repo,
            "pr_number": r.pr_number,
            "model": r.model,
            "tokens_in": r.tokens_in,
            "tokens_out": r.tokens_out,
            "cost_usd": round(r.cost_usd, 6),
            "confidence": round(r.confidence, 2),
            "num_concerns": r.num_concerns,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


@server.tool(description="Aggregate stats across every review the agent has ever produced.")
async def get_review_stats() -> dict:
    async with SessionLocal() as session:
        row = (
            await session.execute(
                select(
                    func.count(ReviewRecord.id),
                    func.sum(ReviewRecord.tokens_in),
                    func.sum(ReviewRecord.tokens_out),
                    func.sum(ReviewRecord.cost_usd),
                    func.avg(ReviewRecord.confidence),
                )
            )
        ).one()
    total, ti, to, cost, avg_conf = row
    return {
        "total_reviews": total or 0,
        "total_tokens_in": ti or 0,
        "total_tokens_out": to or 0,
        "total_cost_usd": round(cost or 0.0, 4),
        "avg_confidence": round(avg_conf or 0.0, 2),
    }


@server.tool(description="Per-repo breakdown of reviews and cost.")
async def get_repo_stats() -> list[dict]:
    async with SessionLocal() as session:
        rows = (
            await session.execute(
                select(
                    ReviewRecord.repo,
                    func.count(ReviewRecord.id),
                    func.sum(ReviewRecord.cost_usd),
                    func.avg(ReviewRecord.confidence),
                ).group_by(ReviewRecord.repo)
            )
        ).all()

    return [
        {
            "repo": repo,
            "reviews": n,
            "cost_usd": round(cost or 0.0, 4),
            "avg_confidence": round(avg_conf or 0.0, 2),
        }
        for repo, n, cost, avg_conf in rows
    ]


def main() -> None:
    import asyncio
    asyncio.run(init_db())
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
