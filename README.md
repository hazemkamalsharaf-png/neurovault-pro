# NeuroVault Pro

A local, AI-powered knowledge base and code snippet manager with a modern dark-themed GUI. Save code snippets, get automatic summaries & tags from your local LLM, and chat with your entire knowledge base using RAG (Retrieval-Augmented Generation).

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## Features

- **Save & Organize** — Store code snippets and notes with title, language, and content
- **AI-Powered Analysis** — Automatic summarization and tag generation via your local LLM (runs 100% offline)
- **The Vault** — Browse, search, and inspect all saved snippets with a detail panel
- **Local RAG Chat** — Ask questions about your saved snippets; the AI retrieves relevant context from your database before answering
- **Fully Offline** — No cloud dependencies. Everything runs locally via LM Studio

## Architecture

```
neurovault_pro/
├── main.py          # Entry point — wires DB, AI worker, settings, and UI together
├── db_manager.py    # SQLite database layer with search & tag management
├── ai_worker.py     # Thread-safe background AI worker (queue + daemon thread)
├── gui.py           # CustomTkinter UI with 4 navigable frames
├── settings.py      # AppSettings dataclass + SettingsManager (JSON persistence)
└── requirements.txt # Dependencies
```

| Module | Responsibility |
|---|---|
| `db_manager.py` | SQLite CRUD, keyword search, tag management, chat history persistence |
| `ai_worker.py` | Thread-safe background queue for summarization, auto-tagging, and RAG chat |
| `gui.py` | Dark-themed CustomTkinter UI — Dashboard, Vault (with file import), AI Chat, Settings |
| `settings.py` | JSON-based settings persistence with change listeners |
| `main.py` | Bootstrap: DB init, worker thread start, settings load, app launch |

## Prerequisites

- **Python 3.10+**
- **[LM Studio](https://lmstudio.ai/)** running with a model loaded on `http://127.0.0.1:1234/v1`

> The app works fine without LM Studio for saving and searching snippets — the AI features will show a "LLM offline" warning instead of crashing.

## Installation

```bash
# Clone or download this project
cd neurovault_pro

# Install dependencies
pip install -r requirements.txt

# Run
python main.py
```

## Usage

1. **Start LM Studio** and load any model (the app connects to `http://127.0.0.1:1234/v1`)
2. **Launch NeuroVault Pro**: `python main.py`
3. **Dashboard** — Enter a title, select language, paste content, click "Save & Analyze" for AI summary + auto-tags
4. **The Vault** — Browse all snippets, search by keyword, double-click for details; import `.txt`, `.md`, `.pdf`, or `.docx` files
5. **AI Chat** — Ask questions about your saved code; the AI retrieves relevant context automatically (RAG)
6. **Settings** — Configure LLM endpoint URL, temperature, max tokens, timeout, and chat history limit

## Tech Stack

- **GUI**: CustomTkinter (dark theme)
- **Database**: SQLite3 (WAL mode, foreign keys)
- **AI**: OpenAI-compatible API via `requests` (LM Studio endpoint)
- **Concurrency**: `threading` + `queue.Queue` for non-blocking AI tasks

## License

MIT License — feel free to use, modify, and distribute.
