import os
from typing import List, Dict, Any

def search_web(query: str, max_results: int = 8) -> List[Dict[str, str]]:
    """
    Search the web using DuckDuckGo (via ddgs or duckduckgo_search package).
    Returns a list of dicts: [{"title": ..., "url": ..., "snippet": ...}]
    """
    provider = os.environ.get("SEARCH_PROVIDER", "ddgs").lower()
    
    results: List[Dict[str, str]] = []
    
    if provider == "ddgs":
        # Attempt import from ddgs package or duckduckgo_search
        DDGS_class = None
        try:
            from ddgs import DDGS
            DDGS_class = DDGS
        except ImportError:
            try:
                from duckduckgo_search import DDGS
                DDGS_class = DDGS
            except ImportError:
                pass
        
        if DDGS_class is None:
            raise RuntimeError(
                "Neither 'ddgs' nor 'duckduckgo_search' python package is installed. "
                "Please run `pip install ddgs`."
            )
        
        try:
            ddgs_inst = DDGS_class()
            raw_results = list(ddgs_inst.text(query, max_results=max_results))
            for item in raw_results:
                results.append({
                    "title": item.get("title", "No Title"),
                    "url": item.get("href", item.get("link", "")),
                    "snippet": item.get("body", item.get("snippet", ""))
                })
        except Exception as e:
            print(f"Error executing DuckDuckGo search: {e}")
            return []
            
    return results
