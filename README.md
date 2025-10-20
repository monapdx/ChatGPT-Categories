# Chat Categorizer & Folders Viewer

Two Streamlit apps for organizing long chat histories with email‑style labels and browsing them like folders.

- **Chat Categorizer (`app.py`)** — import chat JSON, assign categories with checkboxes, filter/search/sort, and export back to a portable `messages.json`. Supports **round‑tripping**: re‑import the same file later and keep working (additive merge).
- **Chat Folders Viewer (`category_viewer.py`)** — read‑only viewer that treats categories as folders in a left nav and shows conversations on the right. Search, AND/OR category filters, pagination, and export of filtered subsets.

## Features
- Robust JSON normalizer
- SQLite persistence (`chat_categorizer.db`)
- Gmail‑style labeling (many‑to‑many categories)
- Round‑trip export format: `messages.json` with `schema_version` and `exported_at`

## Stack
Python 3.9+, Streamlit, SQLite, JSON

## Quickstart
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py      # editor
streamlit run category_viewer.py  # viewer
```

## Export format
See `examples/messages.sample.json`.
