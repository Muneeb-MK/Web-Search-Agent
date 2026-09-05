# Clarify-Then-Search Research Agent

A Streamlit web application that acts as a research assistant. It takes a user's initial question, asks **exactly 3 clarifying questions** to narrow intent and scope, performs live web searches using DuckDuckGo (`ddgs`), and synthesizes grounded answers with inline citations powered by Groq's LLM (`llama-3.3-70b-versatile`).

## 🌟 Features

- **3-Question Clarification Step**: Asks targeted questions (aspect, depth/format, constraints) before searching to ensure accurate results. Blank/skipped answers are allowed.
- **Live DuckDuckGo Web Search**: Abstracted search provider (`core/search.py`) retrieving up to 8 live web results.
- **Grounded Citations**: Synthesizes responses with numerical inline citations `[1]`, `[2]` strictly mapped to retrieved sources.
- **Collapsible Sources**: Expander section under each assistant answer detailing source title, URL, and snippet.
- **Smart Topic Classification & Branching**: Automatically detects if follow-up questions introduce a new topic, offering options to start a new chat or continue in the current thread.
- **SQLite Persistence**: Chat threads and message history persist across app reloads in `data/app.db`.
- **Zero Paid Dependencies**: Built entirely with open-source Python libraries and free-tier APIs (Groq & DuckDuckGo).

---

## 🛠️ Tech Stack

- **Language**: Python 3.11+
- **UI Framework**: Streamlit
- **LLM**: Groq API (`groq` package, default model: `llama-3.3-70b-versatile`)
- **Web Search**: DuckDuckGo Search (`ddgs` package)
- **Database**: SQLite (`sqlite3` built-in) stored at `data/app.db`

---

## ⚙️ Environment Variables

Create a `.env` file in the root directory (or configure secrets in Streamlit Cloud):

```env
# Required: Get a free key at https://console.groq.com
GROQ_API_KEY=your_groq_api_key_here

# Optional: Groq model (defaults to llama-3.3-70b-versatile)
GROQ_MODEL=llama-3.3-70b-versatile

# Optional: Search provider (defaults to ddgs)
SEARCH_PROVIDER=ddgs
```

---

## 🚀 Local Setup & Running

1. **Clone or navigate to the project directory**:
   ```bash
   cd "Web Search Agent"
   ```

2. **Create and activate a virtual environment (optional but recommended)**:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure your API Key**:
   Copy `.env.example` to `.env` and insert your `GROQ_API_KEY`:
   ```bash
   cp .env.example .env
   ```

5. **Run the Streamlit application**:
   ```bash
   streamlit run app.py
   ```

---

## ☁️ Deployment on Streamlit Community Cloud

1. Push your repository to GitHub (ensure `data/app.db` and `.env` are excluded via `.gitignore`).
2. Go to [share.streamlit.io](https://share.streamlit.io) and connect your GitHub repository.
3. Set `app.py` as the main entrypoint.
4. Under **Advanced Settings** -> **Secrets**, paste your secrets:
   ```toml
   GROQ_API_KEY = "your_groq_api_key_here"
   GROQ_MODEL = "llama-3.3-70b-versatile"
   SEARCH_PROVIDER = "ddgs"
   ```
5. Click **Deploy**!

---

## 📂 Project Structure

```
Web Search Agent/
├── app.py                  # Streamlit entrypoint
├── requirements.txt        # Python package dependencies
├── .env.example            # Environment template
├── .gitignore              # Git ignore configuration
├── .streamlit/
│   └── secrets.toml.example# Streamlit Cloud secrets template
├── core/
│   ├── __init__.py
│   ├── db.py               # SQLite schema & CRUD operations
│   ├── search.py           # DuckDuckGo search provider abstraction
│   ├── llm.py              # Groq LLM service wrapper
│   └── agent.py            # Workflow orchestrator
└── README.md               # Documentation
```
