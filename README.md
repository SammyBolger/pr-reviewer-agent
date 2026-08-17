# pr-reviewer-agent

A GitHub App that reviews pull requests with an LLM agent.

When a PR is opened or updated, the agent fetches the diff, retrieves related context from the repo (past PRs, related files, coding conventions) via a Chroma-backed RAG index, runs a LangGraph review workflow with tool use, and posts a structured Markdown comment on the PR.

## Status

Early build. Working toward the MVP:

- [ ] Webhook signature verification
- [ ] GitHub App auth (JWT + installation tokens)
- [ ] Fetch PR diff
- [ ] LLM review with structured output
- [ ] Post review comment
- [ ] RAG over repo context
- [ ] LangGraph orchestration
- [ ] LLM-as-judge eval harness
- [ ] Fly.io deploy

## Running locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# fill in .env
uvicorn app.main:app --reload --port 8000
```

## Stack

Python, FastAPI, LangGraph, Anthropic Claude, Chroma, PostgreSQL, deployed on Fly.io.

<!-- trigger a review -->
