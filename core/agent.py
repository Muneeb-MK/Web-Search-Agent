from typing import Tuple, List, Dict, Any, Optional
from core import db, search, llm

def start_new_thread(user_question: str) -> Tuple[str, List[str]]:
    """
    Start a new research thread with a user's initial question.
    Generates 3 clarifying questions and stores pending state in database.
    """
    # 1. Create thread in DB
    thread_id = db.create_thread(title=user_question, status="clarifying")
    
    # 2. Add initial user message
    db.add_message(thread_id=thread_id, role="user", content=user_question)
    
    # 3. Generate 3 clarifying questions
    questions = llm.get_clarifying_questions(user_question)
    
    # 4. Save pending clarifications
    db.save_pending_clarifications(
        thread_id=thread_id,
        original_question=user_question,
        questions=questions,
        answers=[""] * len(questions)
    )
    
    return thread_id, questions

def process_clarification_submission(thread_id: str, answers: List[str]) -> Tuple[str, List[Dict[str, str]]]:
    """
    Process submitted clarification answers, execute web search, synthesize response,
    and save assistant message to DB. Returns (synthesized_answer, search_sources).
    """
    # 1. Fetch pending record
    pending = db.get_pending_clarifications(thread_id)
    if not pending:
        raise ValueError(f"No pending clarifications found for thread {thread_id}")
        
    original_question = pending["original_question"]
    questions = pending["questions"]
    q_and_a = list(zip(questions, answers))
    
    # 2. Refine search query
    refined_query = llm.generate_refined_query(original_question, q_and_a)
    
    # 3. Perform web search
    search_results = search.search_web(refined_query, max_results=8)
    
    # 4. Fetch history for context
    history = db.get_thread_messages(thread_id)
    
    # 5. Synthesize answer
    synthesized_answer = llm.synthesize_answer(
        original_question=original_question,
        q_and_a=q_and_a,
        search_results=search_results,
        chat_history=history
    )
    
    # 6. Update thread status to active
    db.update_thread_status(thread_id, status="active")
    
    # 7. Add assistant message to DB with sources
    db.add_message(
        thread_id=thread_id,
        role="assistant",
        content=synthesized_answer,
        sources=search_results
    )
    
    # 8. Clear pending clarifications
    db.delete_pending_clarifications(thread_id)
    
    return synthesized_answer, search_results

def handle_followup(thread_id: str, new_message: str) -> Dict[str, Any]:
    """
    Process a follow-up message in an active thread.
    Classifies if topic is same or new.
    """
    thread = db.get_thread(thread_id)
    if not thread:
        raise ValueError(f"Thread {thread_id} not found")
        
    # Classify topic
    classification = llm.classify_topic(thread["title"], new_message)
    
    if classification == "new_topic":
        return {
            "status": "divergence",
            "message": new_message
        }
        
    # Same topic: append message and answer directly
    db.add_message(thread_id=thread_id, role="user", content=new_message)
    
    # Perform contextual search for follow-up
    search_results = search.search_web(new_message, max_results=5)
    history = db.get_thread_messages(thread_id)
    
    synthesized_answer = llm.synthesize_answer(
        original_question=new_message,
        q_and_a=[],
        search_results=search_results,
        chat_history=history
    )
    
    db.add_message(
        thread_id=thread_id,
        role="assistant",
        content=synthesized_answer,
        sources=search_results
    )
    
    return {
        "status": "answered",
        "answer": synthesized_answer,
        "sources": search_results
    }
