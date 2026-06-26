import os
from tavily import TavilyClient

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "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")


def get_reviews_from_tavily(doctor_name: str, address: str) -> str:
    """
    Searches Google for doctor reviews using Tavily.
    
    Args:
        doctor_name: Name of the doctor
        address: City or hospital location
        
    Returns:
        Combined text from search results
    """
    print(f"🔍 Searching Tavily for reviews: {doctor_name} from {address}")
    tvly = TavilyClient(api_key=TAVILY_API_KEY)
    
    query = f"{doctor_name} {address} reviews patient feedback Google"
    
    response = tvly.search(
        query=query,
        search_depth="advanced",
        include_raw_content=True,
        max_results=3
    )
    
    extracted_text = ""
    for result in response.get('results', []):
        extracted_text += f"Title: {result.get('title', '')}\n"
        extracted_text += f"URL: {result.get('url', '')}\n"
        extracted_text += f"Content: {result.get('content', '')}\n"
        
        if result.get('raw_content'):
            extracted_text += f"Raw Details: {result['raw_content'][:2000]}\n"
            
        extracted_text += "---\n"
        
    return extracted_text