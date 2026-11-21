"""Answer generation (and LLM-based triple extraction). Works with no LLM at all (extractive mode)."""
from __future__ import annotations

import httpx

from app import config

SYSTEM = (
    "You are a solutions architect answering questions about a Spotify-like web app architecture "
    "document. Use the knowledge-graph facts for structure (which service owns/uses what) and the "
    "numbered passages for detail. Answer ONLY from this context and cite passages like [1], [2]. "
    "If the context does not contain the answer, say so plainly."
)


def build_prompt(question: str, hits: list[dict], facts: list[dict]) -> str:
    fx = "\n".join(f"- {f['subject']} -[{f['relation']}]-> {f['object']}" for f in facts) or "- (none)"
    ctx = "\n\n".join(f"[{i}] ({h['section']}, p.{h['page']})\n{h['text']}" for i, h in enumerate(hits, 1))
    return f"Knowledge-graph facts:\n{fx}\n\nPassages:\n{ctx}\n\nQuestion: {question}\nAnswer:"


def complete(prompt: str, system: str = SYSTEM) -> str:
    p = config.LLM_PROVIDER.lower()
    with httpx.Client(timeout=90) as c:
        if p == "anthropic":
            r = c.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": config.ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01"},
                json={"model": config.LLM_MODEL or "claude-haiku-5-5", "max_tokens": config.LLM_MAX_TOKENS,
                      "system": system, "messages": [{"role": "user", "content": prompt}]},
            )
            r.raise_for_status()
            return "".join(b.get("text", "") for b in r.json()["content"])

        base = config.LLM_BASE_URL or ("http://ollama:11434/v1" if p == "ollama" else "https://api.openai.com/v1")
        headers = {"Authorization": f"Bearer {config.OPENAI_API_KEY}"} if config.OPENAI_API_KEY else {}
        r = c.post(
            f"{base.rstrip('/')}/chat/completions", headers=headers,
            json={"model": config.LLM_MODEL or ("llama3.2:3b" if p == "ollama" else "gpt-4o-mini"),
                  "max_tokens": config.LLM_MAX_TOKENS,
                  "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]},
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


def generate(question: str, hits: list[dict], facts: list[dict]) -> str:
    if config.LLM_PROVIDER.lower() == "none" or not hits:
        if not hits:
            return "No relevant passages found in the indexed documents."
        fx = "\n".join(f"• {f['subject']} → {f['relation']} → {f['object']}" for f in facts[:6])
        ps = "\n\n".join(f"[{i}] {h['section']}: " + " ".join(h["text"].splitlines()[1:])[:350] for i, h in enumerate(hits[:3], 1))
        return ("No LLM configured (LLM_PROVIDER=none).\n\n" + (f"Graph facts:\n{fx}\n\n" if fx else "") + f"Top passages:\n{ps}")
    return complete(build_prompt(question, hits, facts))
