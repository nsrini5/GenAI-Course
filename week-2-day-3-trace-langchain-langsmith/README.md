# Week 2 Day 3 - Trace a LangChain App with LangSmith

A small LangChain app instrumented with LangSmith tracing.

## Setup

1. Install dependencies with: pip install -r requirements.txt
2. Copy .env.example to .env and fill in local credentials. Never commit .env.
3. Run with: python traced_app.py

## LangSmith checks

- Confirm the run appears in the configured LangSmith project.
- Confirm the trace includes the week-2-day-3-langchain-app root run.
- Inspect the prompt, model call, and response.

## Variables

OPENAI_API_KEY and LANGSMITH_API_KEY are required. LANGSMITH_TRACING enables tracing. LANGSMITH_PROJECT selects the project. OPENAI_MODEL is optional and defaults to gpt-4o-mini.
