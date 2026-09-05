# Build spec: clarify-then-search research agent

Build a Streamlit web app that acts as a research assistant. It takes a user's
question, asks exactly 3 clarifying questions to narrow the request, performs
a live web search based on the refined query, and returns a synthesized,
cited answer. The user can keep chatting on the same topic in the same
thread. If a new message looks like a different topic, the app does **not**
auto-switch — it asks the user whether to start a new chat or continue in
the current one.

Use only free-tier services and open-source libraries. No paid API keys, no
local model / no Ollama — this must run entirely on Streamlit Community
Cloud making outbound API calls only, no local inference, no GPU.

## Tech stack

- Language: Python 3.11+
- UI: Streamlit (`streamlit`)
- LLM: Groq API (`groq` Python package). Default model
  `llama-3.3-70b-versatile`, configurable via env var `GROQ_MODEL`.
- Web search: `ddgs` package (DuckDuckGo Search). IMPORTANT: the package was
  renamed from `duckduckgo_search` to `ddgs` — use `pip install ddgs` and
  `from ddgs import DDGS`. Write the search call behind an interface
  (`core/search.py`) so a different provider (e.g. Tavily via
  `tavily-python`) could be swapped in later without touching the rest of
  the app.
- Storage: SQLite via the built-in `sqlite3` module — a file `data/app.db`
  that persists across Streamlit reruns and browser refreshes. Do not rely
  on `st.session_state` alone for thread/message history.

## Environment variables (never hardcode secrets)

- `GROQ_API_KEY` — required
- `GROQ_MODEL` — optional, default `llama-3.3-70b-versatile`
- `SEARCH_PROVIDER` — optional, default `ddgs`

Read these with `os.environ.get(...)`, and also support `st.secrets` as a
fallback so the same code works locally (via a `.env`) and on Streamlit
Community Cloud (via its Secrets panel).

## Project structure

```
project/
  app.py                  # Streamlit entrypoint
  requirements.txt
  .env.example
  .gitignore               # must exclude data/app.db and .env
  .streamlit/
    secrets.toml.example
  core/
    __init__.py
    llm.py                 # Groq wrapper: clarifying questions, refined query,
                            # answer synthesis, topic classification
    search.py              # search provider abstraction, ddgs by default
    db.py                  # SQLite schema + CRUD for threads/messages
    agent.py               # orchestrates the full clarify -> search ->
                            # synthesize -> branch flow
  README.md
```

## Data model (SQLite)

**threads**
- `id` (TEXT, UUID, primary key)
- `title` (TEXT) — the first user question, truncated for display
- `created_at` (TIMESTAMP)
- `status` (TEXT) — `clarifying` | `active`

**messages**
- `id` (INTEGER, primary key, autoincrement)
- `thread_id` (TEXT, foreign key -> threads.id)
- `role` (TEXT) — `user` | `assistant` | `system`
- `content` (TEXT)
- `created_at` (TIMESTAMP)

**pending_clarifications**
- `thread_id` (TEXT, primary key)
- `original_question` (TEXT)
- `questions` (JSON array of exactly 3 strings)
- `answers` (JSON array, filled in as the user responds; blank entries allowed)

## Core flow to implement

1. **New question intake.** If no thread is selected, or the user clicks
   "+ New chat" and types a message, treat it as a fresh question and go to
   step 2.

2. **Clarification step.** Call the LLM with a system prompt instructing it
   to return **exactly 3** clarifying questions as a JSON array of strings.
   The questions should aim to narrow: (a) the specific angle or aspect of
   the topic, (b) the depth or format wanted (quick answer vs. thorough
   explanation), and (c) any relevant constraints (timeframe, location,
   comparison targets, etc. — let the model choose what's actually useful
   for that question, don't force all three categories rigidly). Render the
   3 questions as a small form in the UI. Do not run the search until the
   user submits answers. Allow leaving any answer blank/skipped without
   breaking the flow.

3. **Refined query construction.** Once answers are submitted, call the LLM
   again to combine the original question and the 3 Q&A pairs into one
   concise, well-formed search query string.

4. **Web search.** Pass the refined query to `core/search.py`, which calls
   `DDGS().text(query, max_results=8)` (or the configured provider) and
   returns a list of `{title, url, snippet}` dicts.

5. **Synthesis.** Call the LLM with the original question, the clarification
   answers, and the search results. Instruct it to write a clear answer
   with inline citation markers (e.g. `[1]`, `[2]`) matched to a reference
   list of URLs at the end. The prompt must explicitly forbid citing
   anything not present in the provided search results.

6. **Save & display.** Persist the full exchange (original question,
   clarification Q&A, refined query, search results, final answer) to the
   `messages` table under the current thread. Render it in the chat UI with
   a collapsible "Sources" section listing the URLs actually used.

7. **Follow-up handling.** For any later message in an already-active
   thread, first call an LLM classifier with a prompt along the lines of:
   "Current conversation topic: {thread title/summary}. New message:
   {message}. Answer only `same_topic` or `new_topic`."
   - **`same_topic`** → treat as a normal conversational follow-up: append
     to the thread's history and answer directly (the LLM may decide to run
     another search if it needs fresher information, but no new
     clarification round is triggered).
   - **`new_topic`** → do **not** switch automatically. Show two buttons:
     **"Start new chat with this"** and **"Continue in this chat anyway"**.
     - *Start new chat with this* → create a new thread row, seed it with
       this message as the original question, and re-enter the
       clarification step (step 2) for the new thread. Switch the active
       thread to it.
     - *Continue in this chat anyway* → treat the message as a normal
       follow-up in the current thread instead.

## UI requirements (Streamlit)

- **Sidebar**: list of threads (title = first question, truncated to ~40
  chars, plus created date), newest first. A **"+ New chat"** button at the
  top starts a blank thread. Clicking a thread loads its full history into
  the main panel.
- **Main panel**: standard chat UI using `st.chat_message` and
  `st.chat_input`. During the clarification step, render the 3 questions as
  a form (e.g. `st.form` with three `st.text_input` fields plus a submit
  button) instead of a normal chat bubble.
- Show `st.spinner` during LLM and search calls so the UI doesn't look
  frozen.
- Each assistant answer has a collapsible "Sources" expander listing the
  search results actually cited.

## Error handling

- Zero search results → tell the user plainly and offer to answer from
  general knowledge with a clear "not web-grounded" disclaimer, rather than
  silently returning a bad answer.
- Groq API failures (rate limit, network error) → show a clear inline error
  and a retry option; never crash the app or lose what the user typed.
- Missing `GROQ_API_KEY` at startup → show a clear setup-instructions screen
  instead of a raw stack trace.

## Deployment requirements (Streamlit Community Cloud)

- Single `app.py` entrypoint; `requirements.txt` pinning `streamlit`,
  `groq`, `ddgs`, and anything else used.
- `data/app.db` and `.env` must be gitignored. Include `.env.example` and
  `.streamlit/secrets.toml.example` showing the required variable names
  with placeholder values only.
- `README.md` covering: local setup (`pip install -r requirements.txt`,
  `streamlit run app.py`) and deployment (push to a public GitHub repo,
  deploy via share.streamlit.io, add `GROQ_API_KEY` under the app's Secrets
  in the dashboard).

## Acceptance criteria

- [ ] A new question always produces exactly 3 clarifying questions before
      any search happens.
- [ ] Skipping a clarifying question is allowed and doesn't break the flow.
- [ ] The final answer includes inline citations that match a listed set of
      sources actually returned by the search step — no fabricated sources.
- [ ] A follow-up on the same topic continues in the same thread without
      re-triggering clarification.
- [ ] A message on a clearly different topic shows the "start new chat?"
      prompt instead of switching automatically.
- [ ] Refreshing the browser preserves all threads and messages (backed by
      SQLite, not just `st.session_state`).
- [ ] The app has no dependency on any paid API key or local model —
      everything runs on free tiers.
