import os
# pyrefly: ignore [missing-import]
import streamlit as st
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

# Load environment variables from .env file if available
load_dotenv()

from core import db, agent, llm

# Page setup
st.set_page_config(
    page_title="Clarify-Then-Search Research Agent",
    page_icon="🔍",
    layout="wide"
)

# Initialize database
db.init_db()

# --- Custom Styling ---
st.markdown("""
<style>
    .main-header {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 0.95rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .clarification-box {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .divergence-card {
        background-color: #FEF3C7;
        border: 1px solid #F59E0B;
        border-radius: 8px;
        padding: 1.2rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Check API Key configuration (Gemini or Groq)
provider = llm.get_llm_provider()
has_gemini = bool(llm.get_gemini_api_key())
has_groq = bool(llm.get_groq_api_key())

if not (has_gemini or has_groq):
    st.warning("⚠️ **LLM API Key is missing!**")
    st.info("""
    To use this research agent, please provide an API key for **Google Gemini** or **Groq**.
    
    **Option 1: Google Gemini API (Recommended - Free)**
    1. Get a key at [aistudio.google.com](https://aistudio.google.com).
    2. Add to `.env`:
       ```env
       GEMINI_API_KEY=your_gemini_api_key_here
       LLM_PROVIDER=gemini
       ```
    
    **Option 2: Groq API (Free)**
    1. Get a key at [console.groq.com](https://console.groq.com).
    2. Add to `.env`:
       ```env
       GROQ_API_KEY=your_groq_api_key_here
       LLM_PROVIDER=groq
       ```
    """)
    st.stop()

# Initialize session state variables
if "active_thread_id" not in st.session_state:
    st.session_state.active_thread_id = None

if "pending_divergence" not in st.session_state:
    st.session_state.pending_divergence = None

# --- SIDEBAR: Thread History ---
with st.sidebar:
    st.title("🔍 Research Assistant")
    
    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        st.session_state.active_thread_id = None
        st.session_state.pending_divergence = None
        st.rerun()
        
    st.divider()
    st.subheader("Recent Chats")
    
    threads = db.get_all_threads()
    
    if not threads:
        st.caption("No chat history yet. Start by asking a question!")
    else:
        for t in threads:
            t_id = t["id"]
            title = t["title"]
            created = t["created_at"][:10] if t["created_at"] else ""
            status_icon = "⏳" if t["status"] == "clarifying" else "💬"
            
            is_active = (t_id == st.session_state.active_thread_id)
            
            col1, col2 = st.columns([0.85, 0.15])
            with col1:
                btn_label = f"{status_icon} {title}"
                if st.button(
                    btn_label, 
                    key=f"thread_{t_id}", 
                    use_container_width=True,
                    type="secondary" if not is_active else "primary"
                ):
                    st.session_state.active_thread_id = t_id
                    st.session_state.pending_divergence = None
                    st.rerun()
            with col2:
                if st.button("🗑️", key=f"del_{t_id}", help="Delete chat"):
                    db.delete_thread(t_id)
                    if st.session_state.active_thread_id == t_id:
                        st.session_state.active_thread_id = None
                    st.rerun()

# --- MAIN PANEL ---

st.markdown('<div class="main-header">Clarify-Then-Search Research Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Ask any complex question. I will clarify your intent, perform live web searches, and return grounded answers with citations.</div>', unsafe_allow_html=True)

# Helper function to switch thread
def set_active_thread(t_id: str):
    st.session_state.active_thread_id = t_id
    st.session_state.pending_divergence = None

# Case 1: No active thread selected (Blank screen waiting for new question)
if not st.session_state.active_thread_id:
    st.info("💡 Ask a new question below to start a research session.")
    
    user_input = st.chat_input("What would you like to research today?")
    if user_input:
        with st.spinner("Analyzing question & generating 3 clarifying questions..."):
            thread_id, questions = agent.start_new_thread(user_input)
            st.session_state.active_thread_id = thread_id
            st.rerun()

# Case 2: Active thread selected
else:
    current_thread_id = st.session_state.active_thread_id
    thread = db.get_thread(current_thread_id)
    
    if not thread:
        st.error("Thread not found.")
        st.session_state.active_thread_id = None
        st.rerun()
        
    messages = db.get_thread_messages(current_thread_id)
    pending_clarification = db.get_pending_clarifications(current_thread_id)
    
    # Display message history
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        sources = msg.get("sources")
        
        with st.chat_message(role):
            st.markdown(content)
            
            # Collapsible sources expander for assistant messages
            if role == "assistant" and sources:
                with st.expander("📚 Sources & Citations", expanded=False):
                    for idx, s in enumerate(sources, 1):
                        title = s.get("title", "Link")
                        url = s.get("url", "#")
                        snippet = s.get("snippet", "")
                        st.markdown(f"**[{idx}] [{title}]({url})**")
                        if snippet:
                            st.caption(snippet)

    # --- CLARIFICATION FORM STEP ---
    if thread["status"] == "clarifying" and pending_clarification:
        st.divider()
        st.markdown("### 📋 Clarifying Questions")
        st.write("Please answer the following 3 questions to narrow down the research scope. You may leave any field blank if you prefer.")
        
        questions = pending_clarification["questions"]
        
        with st.form(key=f"clarify_form_{current_thread_id}"):
            ans_0 = st.text_input(f"1. {questions[0]}", key="ans_0")
            ans_1 = st.text_input(f"2. {questions[1]}", key="ans_1")
            ans_2 = st.text_input(f"3. {questions[2]}", key="ans_2")
            
            submitted = st.form_submit_button("🔍 Perform Research Search", type="primary", use_container_width=True)
            
            if submitted:
                answers = [ans_0, ans_1, ans_2]
                with st.spinner("Refining search query, searching DuckDuckGo, and synthesizing grounded answer..."):
                    try:
                        agent.process_clarification_submission(current_thread_id, answers)
                        st.rerun()
                    except Exception as e:
                        st.error(f"An error occurred while processing research: {e}")

    # --- DIVERGENCE PROMPT STEP ---
    elif st.session_state.pending_divergence and st.session_state.pending_divergence.get("thread_id") == current_thread_id:
        pending_msg = st.session_state.pending_divergence["message"]
        
        st.markdown(f"""
        <div class="divergence-card">
            <h4>💡 Different Topic Detected</h4>
            <p>Your message <strong>"{pending_msg}"</strong> appears to be on a new topic compared to <strong>"{thread['title']}"</strong>.</p>
            <p>Would you like to start a new chat or continue in this current conversation?</p>
        </div>
        """, unsafe_allow_html=True)
        
        col_new, col_cont = st.columns(2)
        with col_new:
            if st.button("✨ Start new chat with this", type="primary", use_container_width=True):
                st.session_state.pending_divergence = None
                with st.spinner("Creating new chat thread..."):
                    new_thread_id, _ = agent.start_new_thread(pending_msg)
                    st.session_state.active_thread_id = new_thread_id
                    st.rerun()
        with col_cont:
            if st.button("💬 Continue in this chat anyway", type="secondary", use_container_width=True):
                st.session_state.pending_divergence = None
                with st.spinner("Searching and answering in current chat..."):
                    agent.handle_followup(current_thread_id, pending_msg)
                    st.rerun()

    # --- ACTIVE THREAD CHAT INPUT ---
    elif thread["status"] == "active":
        followup_input = st.chat_input("Ask a follow-up question...")
        if followup_input:
            with st.spinner("Checking topic alignment..."):
                result = agent.handle_followup(current_thread_id, followup_input)
                if result.get("status") == "divergence":
                    st.session_state.pending_divergence = {
                        "thread_id": current_thread_id,
                        "message": followup_input
                    }
                st.rerun()
