import os
import json
import re
from typing import List, Dict, Tuple, Optional, Any

# Try importing SDKs
try:
    from google import genai
except ImportError:
    genai = None

try:
    from groq import Groq
except ImportError:
    Groq = None


def get_llm_provider() -> str:
    """Determine active LLM provider ('gemini' or 'groq')."""
    provider = os.environ.get("LLM_PROVIDER")
    if not provider:
        try:
            import streamlit as st
            if "LLM_PROVIDER" in st.secrets:
                provider = st.secrets["LLM_PROVIDER"]
        except Exception:
            pass
            
    if provider:
        return provider.lower()
        
    # Auto-detect based on configured API keys
    if get_gemini_api_key():
        return "gemini"
    if get_groq_api_key():
        return "groq"
        
    return "gemini"  # default fallback


def get_gemini_api_key() -> str:
    """Retrieve Gemini API key from environment variable or Streamlit secrets."""
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        try:
            import streamlit as st
            if "GEMINI_API_KEY" in st.secrets:
                key = st.secrets["GEMINI_API_KEY"]
            elif "GOOGLE_API_KEY" in st.secrets:
                key = st.secrets["GOOGLE_API_KEY"]
        except Exception:
            pass
    return key or ""


def get_groq_api_key() -> str:
    """Retrieve Groq API key from environment variable or Streamlit secrets."""
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        try:
            import streamlit as st
            if "GROQ_API_KEY" in st.secrets:
                key = st.secrets["GROQ_API_KEY"]
        except Exception:
            pass
    return key or ""


def get_gemini_model() -> str:
    """Retrieve Gemini model name."""
    model = os.environ.get("GEMINI_MODEL")
    if not model:
        try:
            import streamlit as st
            if "GEMINI_MODEL" in st.secrets:
                model = st.secrets["GEMINI_MODEL"]
        except Exception:
            pass
    return model or "gemini-2.5-flash"


def get_groq_model() -> str:
    """Retrieve Groq model name."""
    model = os.environ.get("GROQ_MODEL")
    if not model:
        try:
            import streamlit as st
            if "GROQ_MODEL" in st.secrets:
                model = st.secrets["GROQ_MODEL"]
        except Exception:
            pass
    return model or "groq/compound"


def generate_llm_response(messages: List[Dict[str, str]], temperature: float = 0.4, max_tokens: int = 1000) -> str:
    """
    Unified LLM response generator supporting both Gemini API and Groq API.
    """
    provider = get_llm_provider()
    
    # 1. Gemini Provider
    if provider == "gemini":
        if genai is None:
            raise RuntimeError("The 'google-genai' python package is not installed. Run `pip install google-genai`.")
        api_key = get_gemini_api_key()
        if not api_key:
            raise ValueError("GEMINI_API_KEY (or GOOGLE_API_KEY) is not set. Please add it to your .env file or Streamlit secrets.")
            
        client = genai.Client(api_key=api_key)
        model_name = get_gemini_model()
        
        # Combine system prompt and user/assistant messages for Gemini
        system_instructions = ""
        prompt_parts = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                system_instructions += content + "\n"
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
                
        full_prompt = "\n\n".join(prompt_parts)
        if system_instructions:
            full_prompt = f"System Instructions:\n{system_instructions}\n\n{full_prompt}"
            
        # Try generation with fallback models
        models_to_try = [model_name, "gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
        seen = set()
        unique_models = [m for m in models_to_try if m and not (m in seen or seen.add(m))]
        
        last_err = None
        for m in unique_models:
            try:
                res = client.models.generate_content(
                    model=m,
                    contents=full_prompt,
                )
                if res and res.text:
                    return res.text.strip()
            except Exception as e:
                last_err = e
                continue
                
        if last_err:
            raise last_err
        raise RuntimeError("Failed to generate response using Gemini API.")

    # 2. Groq Provider
    else:
        if Groq is None:
            raise RuntimeError("The 'groq' python package is not installed. Run `pip install groq`.")
        api_key = get_groq_api_key()
        if not api_key:
            raise ValueError("GROQ_API_KEY is not set. Please add it to your .env file or Streamlit secrets.")
            
        client = Groq(api_key=api_key)
        primary_model = get_groq_model()
        fallback_models = [primary_model, "groq/compound", "groq/compound-mini", "qwen/qwen3.6-27b", "openai/gpt-oss-20b"]
        
        seen = set()
        unique_models = [m for m in fallback_models if m and not (m in seen or seen.add(m))]
        
        last_err = None
        for m in unique_models:
            try:
                response = client.chat.completions.create(
                    model=m,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                last_err = e
                err_str = str(e).lower()
                if "model_not_found" in err_str or "does not exist" in err_str or "404" in err_str:
                    continue
                raise e
                
        if last_err:
            raise last_err
        raise RuntimeError("Failed to generate response using Groq API.")


def get_clarifying_questions(question: str) -> List[str]:
    """
    Generate exactly 3 clarifying questions for a user's original query.
    Returns a list of 3 question strings.
    """
    prompt = f"""
You are a helpful research assistant. A user has asked the following initial question:
"{question}"

Generate EXACTLY 3 short, specific clarifying questions to help narrow down their request.
Aim to clarify:
1. The specific angle, domain, or target aspect of the topic.
2. The desired format or depth (e.g. high-level summary, technical deep dive, step-by-step tutorial).
3. Any practical constraints (timeframe, geographical location, target audience, comparison scope, etc.).

CRITICAL INSTRUCTION: Return ONLY a valid JSON array containing exactly 3 strings. Do not include any intro, markdown wrap-up, or extra text.
Example format:
["First clarifying question?", "Second clarifying question?", "Third clarifying question?"]
"""

    messages = [
        {"role": "system", "content": "You output strictly valid JSON arrays of strings."},
        {"role": "user", "content": prompt.strip()}
    ]

    raw_content = generate_llm_response(messages, temperature=0.4, max_tokens=300)
    
    # Clean potential markdown wrapping like ```json ... ```
    if "```" in raw_content:
        raw_content = re.sub(r"^```(?:json)?", "", raw_content, flags=re.IGNORECASE)
        raw_content = raw_content.rstrip("`").strip()
    
    try:
        parsed = json.loads(raw_content)
        if isinstance(parsed, list) and len(parsed) >= 3:
            return [str(q).strip() for q in parsed[:3]]
    except Exception:
        pass
        
    # Fallback if LLM parsing failed or did not return exactly 3 items
    return [
        f"Which specific aspect or angle of '{question}' are you most interested in?",
        "What depth or format would be most helpful (e.g. quick summary vs detailed analysis)?",
        "Are there any specific context constraints (such as timeframe, location, or comparison targets)?"
    ]


def generate_refined_query(original_question: str, q_and_a: List[Tuple[str, str]]) -> str:
    """
    Combine original question + clarifying Q&A pairs into a focused search query string.
    """
    qa_text = "\n".join([f"- Clarification Q: {q}\n  Answer: {a if a.strip() else '(skipped)'}" for q, a in q_and_a])
    
    prompt = f"""
Original User Question: "{original_question}"

Clarification Questions and Answers:
{qa_text}

Task: Synthesize the original question and the clarified details into ONE single concise, highly effective search engine query.
Output ONLY the raw search query string with no quotes, commentary, or explanation.
"""

    messages = [{"role": "user", "content": prompt.strip()}]
    raw_query = generate_llm_response(messages, temperature=0.3, max_tokens=100)
    
    query = raw_query.strip().strip('"')
    return query if query else original_question


def synthesize_answer(
    original_question: str,
    q_and_a: List[Tuple[str, str]],
    search_results: List[Dict[str, str]],
    chat_history: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    Synthesize a cited answer using the search results.
    Citations should be formatted as [1], [2], corresponding to the index in search_results (1-based).
    """
    if not search_results:
        qa_str = "\n".join([f"Q: {q}\nA: {a}" for q, a in q_and_a if a.strip()])
        fallback_prompt = f"""
User Question: {original_question}
{f'Clarifications:\n{qa_str}' if qa_str else ''}

Note: Web search returned 0 results. Provide a helpful response based on general knowledge, but clearly include a prominent disclaimer at the top that this answer is not grounded in real-time web search results.
"""
        messages = [{"role": "user", "content": fallback_prompt.strip()}]
        return generate_llm_response(messages, temperature=0.5, max_tokens=1000)

    # Build sources text for prompt
    sources_text = ""
    for idx, item in enumerate(search_results, 1):
        sources_text += f"[{idx}] Title: {item.get('title')}\nURL: {item.get('url')}\nSnippet: {item.get('snippet')}\n\n"
        
    qa_str = "\n".join([f"Q: {q}\nA: {a}" for q, a in q_and_a if a.strip()])

    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert research assistant. Synthesize a detailed, well-structured answer to the user's question "
                "using ONLY the provided search results. Include inline numerical citations like [1], [2] whenever "
                "referencing information from a specific search result. DO NOT cite sources that are not in the provided list. "
                "Do NOT fabricate facts or sources. End your response with a summary if appropriate."
            )
        }
    ]
    
    if chat_history:
        for msg in chat_history[-6:]:
            if msg["role"] in ["user", "assistant"]:
                messages.append({"role": msg["role"], "content": msg["content"]})
                
    user_prompt = f"""
Original User Question: {original_question}

Clarification Details:
{qa_str if qa_str else 'None provided'}

Search Results:
{sources_text}

Provide a comprehensive, accurate answer cited with [1], [2], etc. strictly matching the Search Results above.
"""
    messages.append({"role": "user", "content": user_prompt.strip()})

    return generate_llm_response(messages, temperature=0.4, max_tokens=1500)


def classify_topic(thread_title: str, new_message: str) -> str:
    """
    Classify whether a follow-up message belongs to the existing thread topic or is a new topic.
    Returns either 'same_topic' or 'new_topic'.
    """
    prompt = f"""
Current Conversation Topic / Question: "{thread_title}"
New Follow-up Message: "{new_message}"

Determine if the new message is continuing the same overall research topic/context or if it introduces an entirely unrelated new topic.
Respond ONLY with `same_topic` or `new_topic`. Do not include punctuation or extra text.
"""
    messages = [{"role": "user", "content": prompt.strip()}]
    raw_result = generate_llm_response(messages, temperature=0.1, max_tokens=10)
    
    result = raw_result.strip().lower()
    return "new_topic" if "new" in result else "same_topic"
