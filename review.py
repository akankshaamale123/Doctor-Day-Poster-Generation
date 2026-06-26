import os
import requests
import json
import re
from tavily import TavilyClient
from PIL import Image, ImageDraw, ImageFont
import textwrap

# --- Configuration ---
TAVILY_API_KEY = "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"
ENDPOINT = "http://3.7.220.118:5003/v1/chat/completions"
MODEL_NAME = "microsoft/Phi-3-mini-128k-instruct"
TEMPERATURE = 0.3
MAX_TOKENS = 1024


def get_reviews_from_tavily(doctor_name: str, address: str) -> str:
    """Searches Google for doctor reviews using Tavily."""
    print(f"🔍 Searching Tavily for reviews for {doctor_name}...")
    tvly = TavilyClient(api_key=TAVILY_API_KEY)
    
    query = f"{doctor_name} from {address} reviews patient feedback Google"
    
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


def build_review_analysis_prompt(doctor_name: str, reviews_text: str) -> str:
    """Builds the prompt instructing the LLM to extract key info."""
    json_structure = """
{
  "doctor_name": "Name of the doctor",
  "hospital_address": "Extract the hospital or clinic address from the reviews. If not found, say 'Visit our clinic today'",
  "overall_sentiment": "Positive, Neutral, or Negative",
  "average_rating_guess": "A guessed rating out of 5 based on the text",
  "important_keywords": ["List of 3-5 main positive words"],
  "key_themes": ["List of main themes, e.g., 'Punctual', 'Good Listener', 'Effective Treatment'"],
  "review_summary": "A detailed 5-6 line summary combining the best points from patient reviews."
}
"""
    prompt = f"""
Analyze the following patient reviews for {doctor_name}. 
Extract the key important words, identify the main themes, and summarize the overall patient sentiment.

Return ONLY a valid JSON object matching exactly this structure:
{json_structure}

Here is the review data:
---
{reviews_text}
---
"""
    return prompt


def generate_response(user_query: str) -> str | None:
    """Sends user_query to the hosted LLM and returns the text response."""
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an expert data analyst specializing in analyzing patient reviews and feedback. "
                    "You extract key themes, sentiments, and important keywords. "
                    "Always respond ONLY with a valid JSON object — no markdown, no extra text, no explanations."
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
        print(f"📤 Sending to LLM: model={MODEL_NAME}")
        response = requests.post(
            url=ENDPOINT,
            json=payload,
            timeout=60,
        )
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
        print(f"❌ LLM HTTP error {e.response.status_code}: {e.response.text[:300]}")
        return None
    except KeyError:
        print("❌ Unexpected LLM response format")
        return None
    except Exception as e:
        print(f"❌ LLM error: {e}")
        return None


def extract_json_from_llm(llm_output: str) -> dict | None:
    """Safely extracts JSON from LLM output, handling markdown backticks."""
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
        print(f"Raw LLM Output was: {llm_output}")
        return None


def generate_poster(doctor_data: dict, output_path: str = "dr_akkalkotkar_poster.png"):
    """Generates a digital poster using the LLM structured data."""
    print("🖼️ Generating poster...")
    
    # 1. Setup Canvas
    width, height = 800, 1400
    background_color = (240, 248, 255)
    poster = Image.new("RGB", (width, height), color=background_color)
    draw = ImageDraw.Draw(poster)
    
    # 2. Load Fonts
    try:
        font_title = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 60)
        font_subtitle = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 28)
        font_body = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 26)
        font_keywords = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 24)
    except IOError:
        print("⚠️ Warning: Arial fonts not found. Using default PIL font.")
        font_title = ImageFont.load_default()
        font_subtitle = ImageFont.load_default()
        font_body = ImageFont.load_default()
        font_keywords = ImageFont.load_default()

    # 3. Add Doctor Photo
    y_text = 410 
    try:
        doc_img = Image.open(r"C:\Users\Admin\Downloads\avtar.png")
        doc_img = doc_img.resize((300, 300))
        poster.paste(doc_img, (250, 50))
        draw.rectangle([(250, 50), (550, 350)], outline=(0, 51, 102), width=4)
    except FileNotFoundError:
        print("⚠️ Doctor photo not found. Skipping photo.")

    # 4. Add Doctor Name
    name = doctor_data.get("doctor_name", "Dr. Umesh Akkalkotkar")
    draw.text((width/2, y_text), name, font=font_title, fill=(0, 51, 102), anchor="mm")
    
    # Divider Line
    y_text += 70
    draw.line([(150, y_text), (650, y_text)], fill=(0, 153, 204), width=3)

    # 5. Add Review Summary (FROM LLM EXTRACTED DATA)
    y_text += 40
    review_summary = doctor_data.get("review_summary", "Providing excellent patient care with compassion and accurate diagnoses.")
    
    wrapped_summary = textwrap.wrap(review_summary, width=45)
    for line in wrapped_summary:
        draw.text((width/2, y_text), line, font=font_subtitle, fill=(51, 51, 51), anchor="mm")
        y_text += 38

    # 6. Add Keywords (FROM LLM EXTRACTED DATA)
    y_text += 40
    keywords = doctor_data.get("important_keywords", [])
    if keywords:
        draw.text((width/2, y_text), "What Patients Say:", font=font_subtitle, fill=(0, 51, 102), anchor="mm")
        y_text += 45
        
        kw_string = "  •  ".join(keywords)
        wrapped_kw = textwrap.wrap(kw_string, width=40)
        for line in wrapped_kw:
            draw.text((width/2, y_text), line, font=font_keywords, fill=(0, 102, 153), anchor="mm")
            y_text += 32

    # 7. Add Hospital Address (FROM LLM EXTRACTED DATA)
    address = doctor_data.get("hospital_address", "Contact us for appointments")
    
    y_footer = height - 160
    draw.rectangle([(0, y_footer), (width, height)], fill=(0, 51, 102))
    
    y_text = y_footer + 35
    draw.text((width/2, y_text), "Visit Us At:", font=font_subtitle, fill=(255, 255, 255), anchor="mm")
    y_text += 45
    
    wrapped_addr = textwrap.wrap(address, width=40)
    for line in wrapped_addr:
        draw.text((width/2, y_text), line, font=font_body, fill=(220, 240, 255), anchor="mm")
        y_text += 32

    # 8. Save the Poster
    poster.save(output_path)
    print(f"✅ Poster successfully saved to {output_path}")


# ==========================================
# COMBINED Main Execution - Single Block
# ==========================================
if __name__ == "__main__":
    doctor_name = "Dr. Umesh Akkalkotkar"
    address = "Pune"
    
    # 1. Fetch real reviews from Google via Tavily
    scraped_reviews = get_reviews_from_tavily(doctor_name, address)
    
    if not scraped_reviews or len(scraped_reviews) < 50:
        print("⚠️ Could not find enough review data from Tavily.")
        # Fallback data if Tavily fails
        structured_data = {
            "doctor_name": doctor_name,
            "hospital_address": "Visit our clinic today",
            "review_summary": "Excellent patient care with accurate diagnoses.",
            "important_keywords": ["Professional", "Caring", "Expert"]
        }
    else:
        print(f"✅ Successfully extracted {len(scraped_reviews)} characters of review data.")
        
        # 2. Build the prompt using REAL scraped reviews
        prompt = build_review_analysis_prompt(doctor_name, scraped_reviews)
        
        # 3. Send to AWS Phi-3 model
        llm_response = generate_response(prompt)
        
        # 4. Parse the structured JSON
        if llm_response:
            structured_data = extract_json_from_llm(llm_response)
            
            if structured_data:
                print("\n✅ Successfully Structured Reviews:")
                print(json.dumps(structured_data, indent=4))
            else:
                print("\n⚠️ LLM responded, but it wasn't valid JSON.")
                structured_data = None
        else:
            print("\n❌ LLM failed to generate a response.")
            structured_data = None
    
    # 5. Generate poster ONLY if we have structured data
    if structured_data:
        print("\n🎨 Now generating poster with EXTRACTED data...")
        generate_poster(
            doctor_data=structured_data,
            output_path="Dr_Umesh_Poster.png"
        )
    else:
        print("\n❌ Cannot generate poster - no valid data available.")