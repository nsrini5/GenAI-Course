# TN Government Schemes – RAG Chatbot (macOS + VS Code)

Pipeline: **Scrape → Chunk & Embed (local, free) → Chroma vector DB → Streamlit chat with an OpenAI LLM**

```
tn-schemes-rag/
├── 1_scrape.py         # fetches the scheme list + every scheme detail page
├── 2_build_index.py    # chunks, embeds, stores in ./chroma_db
├── 3_app.py            # Streamlit chat UI
├── data/manual/        # drop hand-saved HTML/PDF/TXT pages here (fallback)
├── requirements.txt
└── .env.example
```

## Step 1 – Open the project in VS Code
Unzip the folder, then in VS Code: **File → Open Folder… → tn-schemes-rag**.
Open the terminal with **Ctrl + `**.

## Step 2 – Create a virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```
In VS Code press **Cmd+Shift+P → "Python: Select Interpreter"** and pick `.venv`.
(Need Python? `brew install python@3.11`)

## Step 3 – Add your API key
```bash
cp .env.example .env
open -e .env        # paste your OPENAI_API_KEY, save
```

## Step 4 – Collect the scheme content
```bash
python 1_scrape.py
```
The script checks tn.gov.in's `robots.txt` first. **If the site disallows automated
fetching, the script stops** — in that case use the manual route:
1. Open the scheme list page in Safari/Chrome.
2. Open each scheme and save it with **Cmd+S** (Format: *Web Page, Complete* / *Page Source*)
   or **File → Export as PDF**, into `data/manual/`.
3. Continue to Step 5 — the indexer reads `data/manual/` automatically.

## Step 5 – Build the vector index
```bash
python 2_build_index.py
```
First run downloads the embedding model (~470 MB, once). Re-run this any time you add pages.

## Step 6 – Start the chatbot
```bash
streamlit run 3_app.py
```
Browser opens at http://localhost:8501. Try:
- "Which schemes are available for women entrepreneurs?"
- "What is the eligibility for <scheme name>?"
- "How do I apply and whom do I contact?"

## Tuning knobs
| Setting | File | Default | When to change |
|---|---|---|---|
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | 2_build_index.py | 1000 / 150 | Smaller if answers mix up schemes |
| `TOP_K` | 3_app.py | 5 | Higher for "list all schemes" type questions |
| `OPENAI_MODEL` | .env | gpt-4o-mini | Any chat model on your account |
| `EMBED_MODEL` | both 2 & 3 | multilingual MiniLM | Keep identical in both files |

## Troubleshooting
- **"Found 0 scheme links"** – the page's link pattern differs. Right-click a scheme link →
  *Inspect*, note the href pattern, and edit the `if "scheme" in low` line in `find_scheme_links()`.
- **SSL error on Mac** – run `/Applications/Python\ 3.11/Install\ Certificates.command`.
- **Collection not found** – run `2_build_index.py` before `3_app.py`.
