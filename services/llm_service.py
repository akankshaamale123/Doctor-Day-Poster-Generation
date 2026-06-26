import requests
import json
import re
import os
from typing import Optional, Dict
from dotenv import load_dotenv

load_dotenv()

ENDPOINT = os.getenv("LLM_ENDPOINT")
MODEL_NAME = os.getenv("LLM_MODEL")
TEMPERATURE = 0.3
MAX_TOKENS = 1024


def build_review_analysis_prompt(doctor_name: str, reviews_text: str) -> str:
    """Builds the prompt for LLM analysis."""
    json_structure = """
{
  "doctor_name": "Name of the doctor",
  "specialization": "Doctor's specialization if found in the text, else 'General Physician'",
  "hospital_address": "Extract the hospital or clinic address. If not found, say 'Contact for address'",
  "overall_sentiment": "Positive, Neutral, or Negative",
  "important_keywords": ["List of 3-5 main positive adjectives describing the doctor"],
   "key_themes": ["Extract exactly 7 to 10 specific key themes describing the doctor's practice, behavior, and treatment approach. Deduce themes if not explicitly stated but strongly implied by the text."],
  "achievements": ["Extract 2-3 notable achievements (e.g., '15+ Years Experience', 'Award Winner', 'Published Researcher'). If none found, invent plausible standard medical achievements based on their specialty."],
  "professional_highlights": ["Extract 2-3 professional highlights (e.g., 'Expert in IVF', 'Advanced Laparoscopic Surgeon', 'Former Head of Department'). If none found, deduce logical highlights from the specialization."],
  "professional_summary": "A detailed 5-6 line professional summary about the doctor."
}
"""
    prompt = f"""
Read the provided text about {doctor_name}. 
Extract key words, identify main themes, write a professional summary, and identify achievements & highlights.

STRICT RULES FOR "professional_summary":
1. Write it as a direct, high-quality professional biography about the doctor.
2. ABSOLUTELY DO NOT use these forbidden words: "review", "reviews", "feedback", "rated", "rating", "patients say", "according to reviews", "patient feedback".


Return ONLY a valid JSON object matching exactly this structure:
{json_structure}

Here is the text data:
---
{reviews_text}
---
"""
    return prompt


def generate_response(user_query: str) -> Optional[str]:
    """Sends query to LLM and returns text response."""
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an expert data analyst specializing in analyzing patient reviews. "
                    "Extract key themes, sentiments, and important keywords. "
                    "Always respond ONLY with a valid JSON object — no markdown, no extra text."
                ),
            },
            {
                "role": "user",
                "content": user_query,
            },
        ],
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
    }

    try:
        print(f"📤 Sending to LLM: {MODEL_NAME}")
        response = requests.post(url=ENDPOINT, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        print(f"📥 LLM replied ({len(content)} chars)")
        return content.strip()

    except requests.exceptions.ConnectionError:
        print(f"❌ LLM not reachable at {ENDPOINT}")
        return None
    except requests.exceptions.Timeout:
        print("❌ LLM request timed out")
        return None
    except requests.exceptions.HTTPError as e:
        print(f"❌ LLM HTTP error: {e.response.status_code}")
        return None
    except Exception as e:
        print(f"❌ LLM error: {e}")
        return None


def extract_json_from_llm(llm_output: str) -> Optional[Dict]:
    """Safely extracts JSON from LLM output."""
    if not llm_output:
        return None
        
    match = re.search(r"```json\s*([\s\S]*?)\s*```", llm_output)
    if match:
        llm_output = match.group(1)
    elif re.search(r"```\s*([\s\S]*?)\s*```", llm_output):
        llm_output = re.search(r"```\s*([\s\S]*?)\s*```", llm_output).group(1)

    try:
        return json.loads(llm_output)
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse JSON: {e}")
        return None


def analyze_doctor_reviews(doctor_name: str, address: str) -> Optional[Dict]:
    """
    Main function: Fetches reviews and analyzes them.
    Returns structured dict or None.
    """
    from services.tavily_service import get_reviews_from_tavily
    
    # 1. Fetch reviews
    scraped_reviews = get_reviews_from_tavily(doctor_name, address)
    
    if not scraped_reviews or len(scraped_reviews) < 50:
        print("⚠️ Not enough review data found")
        return None
    
    print(f"✅ Extracted {len(scraped_reviews)} chars of review data")
    
    # 2. Build prompt
    prompt = build_review_analysis_prompt(doctor_name, scraped_reviews)
    
    # 3. Get LLM response
    llm_response = generate_response(prompt)
    print(llm_response)
    # 4. Parse JSON
    if llm_response:
        return extract_json_from_llm(llm_response)
    
    return None