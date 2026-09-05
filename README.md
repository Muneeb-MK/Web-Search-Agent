# Clarify-Then-Search Research Agent

A Streamlit web application that acts as an intelligent research assistant. It takes a user's initial question, asks **exactly 3 clarifying questions** to narrow intent and scope, performs live web searches using DuckDuckGo (`ddgs`), and synthesizes grounded answers with inline citations powered by your choice of LLM: **Google Gemini API** (e.g. `gemini-flash-lite-latest`, `gemini-3.6-flash`) or **Groq API** (`groq/compound`).

---

## 🌟 Features

- **3-Question Clarification Step**: Asks targeted questions (aspect, depth/format, constraints) before searching to ensure high-accuracy results. Blank/skipped answers are supported.
- **Multi-Provider LLM Support**: Seamlessly switch between **Google Gemini** (recommended) and **Groq** via environment variables.
- **Automatic Model Fallback**: Built-in resilience that automatically routes to active models (`gemini-flash-lite-latest`, `gemini-3.6-flash`, `groq/compound`) to prevent 404 or deprecation errors.
- **Live DuckDuckGo Web Search**: Abstracted search provider (`core/search.py`) retrieving up to 8 live web results without paid search API keys.
- **Grounded Citations**: Synthesizes responses with numerical inline citations `[1]`, `[2]` strictly mapped to retrieved sources.
- **Collapsible Sources**: Interactive expander section under each assistant answer detailing source title, URL, and snippet.
- **Smart Topic Classification & Branching**: Detects if follow-up messages introduce a new topic, offering options to start a new chat or continue in the current thread.
- **SQLite Persistence**: Chat threads and message history persist across app reloads in `data/app.db`.
- **100% Free-Tier Compatible**: Runs with free API keys on Streamlit Community Cloud without GPUs or local inference.

---

## 🛠️ Tech Stack

- **Language**: Python 3.11+
- **UI Framework**: Streamlit
- **LLMs**:
  - **Google Gemini API**: `google-genai` package (default: `gemini-flash-lite-latest`, `gemini-3.6-flash`)
  - **Groq API**: `groq` package (default: `groq/compound`)
- **Web Search**: DuckDuckGo Search (`ddgs` package)
- **Database**: SQLite (`sqlite3` built-in) stored at `data/app.db`

---

## ⚙️ Environment Variables

Create a `.env` file in the root directory:

```env
# Choose LLM Provider: "gemini" or "groq"
LLM_PROVIDER=gemini

# Option 1: Google Gemini API (Recommended - Free key at https://aistudio.google.com)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-flash-lite-latest

# Option 2: Groq API (Free key at https://console.groq.com)
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=groq/compound

# Web Search Provider (Optional - defaults to ddgs)
SEARCH_PROVIDER=ddgs
```

---

## 🚀 Local Setup & Running

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Muneeb-MK/Web-Search-Agent.git
   cd Web-Search-Agent
   ```

2. **Create and activate a virtual environment**:
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
   Copy `.env.example` to `.env` and insert your API key:
   ```bash
   cp .env.example .env
   ```

5. **Run the Streamlit application**:
   ```bash
   streamlit run app.py
   ```

---

## ☁️ Deployment on Streamlit Community Cloud

1. Push your repository to GitHub (ensure `.env` and `data/` are gitignored).
2. Go to [share.streamlit.io](https://share.streamlit.io) and click **Create app**.
3. Select your repository:
   - **Repository**: `Muneeb-MK/Web-Search-Agent`
   - **Branch**: `main`
   - **Main file path**: `app.py`
4. Under **Advanced Settings** -> **Secrets**, paste your configuration in TOML format:

   **For Google Gemini (Recommended):**
   ```toml
   LLM_PROVIDER = "gemini"
   GEMINI_API_KEY = "your_actual_gemini_api_key"
   GEMINI_MODEL = "gemini-flash-lite-latest"
   SEARCH_PROVIDER = "ddgs"
   ```

   **For Groq:**
   ```toml
   LLM_PROVIDER = "groq"
   GROQ_API_KEY = "your_actual_groq_api_key"
   GROQ_MODEL = "groq/compound"
   SEARCH_PROVIDER = "ddgs"
   ```

5. Click **Deploy!**

---

## 📂 Project Structure

```
Web-Search-Agent/
├── app.py                  # Streamlit entrypoint & chat interface
├── requirements.txt        # Python package dependencies
├── .env.example            # Template for environment variables
├── .gitignore              # Git ignore rules (excludes data/ and .env)
├── .streamlit/
│   └── secrets.toml.example# Streamlit Cloud secrets template
├── core/
│   ├── __init__.py
│   ├── db.py               # SQLite schema & CRUD operations (threads & messages)
│   ├── search.py           # DuckDuckGo search provider abstraction
│   ├── llm.py              # Multi-provider LLM wrapper (Gemini & Groq with fallback)
│   └── agent.py            # Clarify -> Search -> Synthesize -> Branch workflow
└── README.md               # Project documentation
```
