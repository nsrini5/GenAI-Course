"""
Translation helper for the Streamlit app.
Every English string shown in the app (labels, filter options, scheme details) is translated once
per language with the LLM and saved in data/i18n/<Language>.json. Later runs load it instantly.
You can open that JSON in VS Code and correct any translation by hand.
"""
import json
from pathlib import Path

CACHE_DIR = Path("data/i18n")
BATCH_CHARS = 5000  # text sent per translation call

INSTRUCTIONS = """Translate each English string in the JSON list into {lang} for farmers in Tamil Nadu.
Rules:
- Return JSON: {{"t": [ ...translations in the SAME order and SAME count... ]}}
- Simple, everyday words a farmer understands. Keep it short like the original.
- Keep numbers, ₹ / Rs amounts, %, dates, phone numbers, web addresses and emojis exactly as they are.
- Well-known scheme names: translate the meaning but you may keep an English acronym in brackets (e.g. PMKSY).
- If a string is already in {lang} or cannot be translated, return it unchanged."""


class Translator:
    def __init__(self, lang: str):
        self.lang = lang
        self.path = CACHE_DIR / f"{lang}.json"
        self.cache: dict[str, str] = {}
        if lang != "English" and self.path.exists():
            self.cache = json.loads(self.path.read_text(encoding="utf-8"))

    def t(self, s: str) -> str:
        if self.lang == "English" or not s:
            return s
        return self.cache.get(s, s)

    def missing(self, strings) -> list[str]:
        if self.lang == "English":
            return []
        return sorted({s for s in strings if s and isinstance(s, str) and s.strip() and s not in self.cache})

    def ensure(self, strings, llm, model: str, progress=None):
        """Translate any strings not yet in the cache, then save the cache."""
        todo = self.missing(strings)
        if not todo:
            return
        batches, cur, size = [], [], 0
        for s in todo:
            if cur and size + len(s) > BATCH_CHARS:
                batches.append(cur)
                cur, size = [], 0
            cur.append(s)
            size += len(s)
        if cur:
            batches.append(cur)

        for i, batch in enumerate(batches, 1):
            try:
                resp = llm.chat.completions.create(
                    model=model, temperature=0, response_format={"type": "json_object"},
                    messages=[{"role": "system", "content": INSTRUCTIONS.format(lang=self.lang)},
                              {"role": "user", "content": json.dumps(batch, ensure_ascii=False)}])
                out = json.loads(resp.choices[0].message.content).get("t", [])
                if len(out) == len(batch):
                    self.cache.update({src: str(dst) for src, dst in zip(batch, out)})
            except Exception as e:  # keep English for this batch, try again next run
                print(f"[i18n] batch {i} failed: {e}")
            if progress:
                progress(i / len(batches))

        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.cache, ensure_ascii=False, indent=1), encoding="utf-8")
