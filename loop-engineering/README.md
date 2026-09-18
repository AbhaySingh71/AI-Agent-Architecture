# Loop Agent: Multi-Aspect Jury & Web Search Edition

An advanced open-source self-correcting multi-agent system built with **FastAPI**, **LangGraph**, **LangChain**, **Groq**, and **DuckDuckGo Web Search**.

The system runs a **Web Search → Writer → Jury Panel (3 Evaluators) → Consensus Judge → Reviser** workflow to produce factually grounded, beginner-friendly explanations with automated self-correction loops.

---

## 🌟 Key Features

- **Live DuckDuckGo Web Search**: Grounds initial drafts and fact checks in real-time web search results.
- **Multi-Aspect Evaluator Jury Panel**:
  - 🔍 **Fact-Checker Evaluator**: Verifies claims against DuckDuckGo search context.
  - 💡 **Pedagogy & Clarity Evaluator**: Ensures simple language and everyday analogy quality.
  - 📐 **Structural Evaluator**: Enforces word count budgets (120–170 words), focus, and concrete examples.
- **Chief Consensus Judge (Aggregator Node)**: Synthesizes jury feedback into a unified Action Plan for the Reviser.
- **FastAPI Modern Web UI**: Interactive visualization of search context, jury verdicts, action plans, and execution trace.

---

## 📁 Contents

- [`backend.py`](file:///C:/Users/abhay/Desktop/advanced-ai-systems/loop-engineering/backend.py) — DuckDuckGo tool & 7-node LangGraph workflow logic
- [`app.py`](file:///C:/Users/abhay/Desktop/advanced-ai-systems/loop-engineering/app.py) — FastAPI web application server
- [`templates/index.html`](file:///C:/Users/abhay/Desktop/advanced-ai-systems/loop-engineering/templates/index.html) — Dynamic web UI template
- [`static/app.js`](file:///C:/Users/abhay/Desktop/advanced-ai-systems/loop-engineering/static/app.js) — Jury trace & event rendering logic
- [`static/style.css`](file:///C:/Users/abhay/Desktop/advanced-ai-systems/loop-engineering/static/style.css) — Custom visual styling tokens

---

## 🚀 Installation & Running

### Using `uv` (Recommended)

```bash
uv sync
uv run python app.py
```

### Or using `pip`

```bash
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:8000` in your browser.

