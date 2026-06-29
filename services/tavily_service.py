import os, re
from tavily import TavilyClient
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()
TAVILY_API_KEY = os.getenv("TAVILY_KEY_URL")


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

def clean_text_for_llm(raw_text: str, max_chars: int = 8000) -> str:
    """
    Strips HTML, scripts, styles, and noise from raw scraped text.
    Truncates to fit within LLM token limits.
    """
    # 1. Remove HTML tags using BeautifulSoup
    try:
        soup = BeautifulSoup(raw_text, "html.parser")
        
        # Remove script, style, noscript tags entirely
        for tag in soup(["script", "style", "noscript", "meta", "link", "head"]):
            tag.decompose()
        
        text = soup.get_text(separator=" ")
    except Exception:
        # Fallback: strip HTML tags with regex if BeautifulSoup fails
        text = re.sub(r'<[^>]+>', ' ', raw_text)
    
    # 2. Remove base64 encoded data (massive blobs like images)
    text = re.sub(r'base64,[A-Za-z0-9+/=]{100,}', '', text)
    
    # 3. Remove URLs
    text = re.sub(r'https?://\S+', '', text)
    
    # 4. Remove excessive whitespace, newlines, tabs
    text = re.sub(r'[\t\r\n]+', ' ', text)
    text = re.sub(r' {2,}', ' ', text)
    
    # 5. Remove non-printable / special characters
    text = re.sub(r'[^\x20-\x7E\u00A0-\uFFFF]', '', text)
    
    # 6. Truncate to max_chars to stay within token limit
    # ~4 chars per token, so 8000 chars ≈ 2000 tokens (leaves room for prompt)
    text = text.strip()
    if len(text) > max_chars:
        text = text[:max_chars] + "... [truncated]"
    
    print("🙄🙄" , text)
    return text 


def extract_text_from_specific_link(url: str) -> str:
    """
    Scrapes the exact text from a specific URL provided by the user.
    Prevents mixing up doctors with the same name.
    """
    print(f"🔍 Extracting data directly from link: {url}")
    tvly = TavilyClient(api_key=TAVILY_API_KEY)
    
    try:
        # Tavily's extract feature gets clean text from a specific URL
        response = tvly.extract(urls=[url])
        
        extracted_text = ""
        # Tavily returns a list of results
        if response and "results" in response:
            for result in response["results"]:
                raw_content = result.get("raw_content", "")
                if raw_content:
                    extracted_text += raw_content + "\n"
                    
        if len(extracted_text) < 50:
            print("⚠️ Tavily extract returned very little text. Trying fallback...")
            # Fallback to standard requests if Tavily extract fails
            import requests
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            res = requests.get(url, headers=headers, timeout=10)
            extracted_text = res.text
            
        return extracted_text
        
    except Exception as e:
        print(f"❌ Failed to extract link: {e}")
        return ""