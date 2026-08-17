# pr-reviewer-agent

An agentic GitHub App that reviews pull requests using an LLM. On PR open or update, it fetches the diff, retrieves related context from the repo (RAG over the docs), runs the review through a LangGraph state machine, and posts a structured Markdown comment on the PR.

## What it does

- **Webhook**: FastAPI endpoint with HMAC signature verification for GitHub App webhooks
- **Auth**: full GitHub App auth flow (JWT signing, installation tokens)
- **RAG**: fetches the repo's docs on first review, embeds them with Chroma + a local sentence-transformer, caches the collection per repo
- **Agent**: LangGraph state machine with nodes for `extract`, `authenticate`, `fetch`, `retrieve`, `review`, `post`
- **Structured output**: Claude tool use returns a Pydantic-validated `Review` schema with summary, changes, concerns (severity + category + file + line), strengths, and self-reported confidence
- **Evals**: an LLM-as-judge harness scores reviews on detection, false-positive rate, usefulness, and calibration against a labeled dataset

## Stack

Python 3.11, FastAPI, LangGraph, Anthropic Claude (Haiku 4.5 for review, Sonnet 4.6 for the judge), Chroma (local embeddings via all-MiniLM-L6-v2), Pydantic v2.

## Running locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# fill in GITHUB_APP_ID, GITHUB_WEBHOOK_SECRET, ANTHROPIC_API_KEY, and put
# your GitHub App private key at ./secrets/github-app.pem
uvicorn app.main:app --reload --port 8000
```

For local webhook testing, tunnel your port to a public URL (`ngrok http 8000`) and use that URL in the GitHub App settings.

## Running the evals

```bash
python -m app.evals.run
```

Runs the review flow against three labeled cases (trivial docs change, hardcoded credential, off-by-one bug), scores each via Claude Sonnet as judge, and prints an aggregate scorecard.

## Layout

```
app/
├── main.py              # FastAPI, /webhook, /health, HMAC verify
├── config.py            # env-driven settings
├── github/
│   ├── auth.py          # App JWT + installation tokens
│   └── client.py        # fetch diff, post comment
├── agent/
│   ├── graph.py         # LangGraph StateGraph + node functions
│   └── state.py         # ReviewState TypedDict
├── retrieval/
│   ├── indexer.py       # fetch repo docs, chunk them
│   └── store.py         # Chroma client + per-repo collection cache
├── llm/
│   ├── client.py        # Claude call, tool-use structured output
│   └── prompts.py       # system + user templates
├── review/
│   ├── schemas.py       # Review, Concern Pydantic models
│   ├── formatter.py     # JSON review -> Markdown comment
│   └── runner.py        # invokes the graph
└── evals/
    ├── dataset.py       # labeled TestCases
    ├── judge.py         # LLM-as-judge
    ├── schemas.py       # Judgement schema
    └── run.py           # runs the full eval + prints scorecard
```
