# Week 2 Day 5 - Ask LangChain for 5 Gluten-Free Breakfast Ideas

## Setup

```bash
python -m venv venv
source venv/bin/activate                 # macOS/Linux
# venv\Scripts\Activate.ps1              # Windows PowerShell
pip install -r requirements.txt
export OPENAI_API_KEY="your-key"         # macOS/Linux
# $env:OPENAI_API_KEY="your-key"         # Windows PowerShell
```

## Run twice

```bash
python breakfast.py
python breakfast.py
```

Compare the two terminal outputs and note whether the same five ideas were returned. Confirm that every suggestion is gluten-free and does not include toast, bread, wheat, barley, or rye. Take a screenshot of the five ideas printed in the terminal for submission.

## GitHub preparation

```bash
git add breakfast.py requirements.txt README.md .gitignore
git commit -m "Add Week 2 Day 5 LangChain breakfast assignment"
git push origin main
```

Do not commit an API key. Share the GitHub link and the screenshot separately as required by the assignment.
