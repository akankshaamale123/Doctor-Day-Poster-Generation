"""
config.py
─────────
MedRite Prescription Generator — single universal template.
Coordinates calibrated by RGBA pixel-scanning of the actual template image.
Template: medrite.png  (1588 × 2246 px)

How coordinates were found:
  • Scanned every row for navy-blue label pixels (R<130, G<130, B<175)
  • Located label end-x positions → text starts 15px after label end
  • Found underline rows (light gray spanning 1364px wide)
  • Text placed 40px ABOVE each underline so baseline sits ON the line
"""
import os
from typing import Optional 
from dotenv import load_dotenv 
load_dotenv()  # load .env file if present 
import requests  


MODEL_NAME = os.environ["LLM_MODEL"]  
MODEL_URL = os.environ["LLM_URL"] 



BASE_DIR      = os.path.dirname(__file__)
TEMPLATE_FILE = os.path.join(BASE_DIR, "templates", "pads", "medrite.png")
FONT_PATH     = os.path.join(BASE_DIR, "fonts", "Caveat-Regular.ttf")

FONT_SIZE    = 40    # main handwriting size
FONT_SIZE_SM = 32    # for date and follow-up (smaller fields)
INK          = (20, 35, 140)   # dark navy blue — matches MedRite template ink

TEMPERATURE = 0.1 
MAX_TOKENS = 2048 


LAYOUT = {

    # ── HEADER ────────────────────────────────────────────────────────────────
    # Underlines at y=256 (Name/Age row), y=308 (Speciality/Gender), y=360 (Reg.No)
    # Text y = underline_y - FONT_SIZE - 4

    "name":      {"x": 195,  "y": 212},   # after "Name :" label (label ends x≈177)
    "age":       {"x": 878,  "y": 212},   # after "Age :" label  (label ends x≈860)
    "specialty": {"x": 232,  "y": 264},   # after "Speciality :" (label ends x≈214)
    "gender":    {"x": 910,  "y": 264},   # after "Gender :"     (label ends x≈893)
    "reg":       {"x": 223,  "y": 316},   # after "Reg. No. :"   (label ends x≈205)
    "date":      {"x": 1312, "y": 82},    # inside DATE box top-right

    # ── DIAGNOSIS ─────────────────────────────────────────────────────────────
    # "DIAGNOSIS :" label occupies y≈399–414, ends x≈365
    # Diagnosis text goes on its own indented line below the label
    "diagnosis": {"x": 383, "y": 430},

    # ── SYMPTOMS — 5 rows ─────────────────────────────────────────────────────
    # "SYMPTOMS :" label at y≈460. Bottom separator at y=756.
    # 5 checkboxes printed at x≈230. Text starts at x=258.
    # Rows spaced ~48px apart starting at y=492.
    "symptoms": [
        {"x": 258, "y": 492},
        {"x": 258, "y": 540},
        {"x": 258, "y": 588},
        {"x": 258, "y": 636},
        {"x": 258, "y": 684},
    ],

    # ── PRESCRIPTIONS — 7 slots ───────────────────────────────────────────────
    # Numbers "1."–"7." printed at x≈115–126.
    # Underlines at y = 856,918,980,1042,1104,1166,1228.
    # Text on same line as number, starting at x=155, y = underline - 40.
    "prescriptions": [
        {"x": 155, "y": 816},    # underline y=856
        {"x": 155, "y": 878},    # underline y=918
        {"x": 155, "y": 940},    # underline y=980
        {"x": 155, "y": 1002},   # underline y=1042
        {"x": 155, "y": 1064},   # underline y=1104
        {"x": 155, "y": 1126},   # underline y=1166
        {"x": 155, "y": 1188},   # underline y=1228
    ],

    # ── DOCTOR'S ADVICE BOX ───────────────────────────────────────────────────
    # Pink border box: y=1246–1408. Two text lines inside.
    "advice": [
        {"x": 130, "y": 1305},
        {"x": 130, "y": 1360},
    ],

    # ── FOOTER ────────────────────────────────────────────────────────────────
    # Refill: label ends x≈172, underline y=1517 → text x=190, y=1484
    # Follow-up: label ends x≈214, underline y=1558 → text x=232, y=1526
    # Dr.: label "Dr." ends x≈1008, underline y=1519 → text x=1025, y=1484
    "refill":   {"x": 190,  "y": 1484},
    "followup": {"x": 232,  "y": 1526},
    "dr_sig":   {"x": 1025, "y": 1484},

    # ── QR CODE BOX ───────────────────────────────────────────────────────────
    # Dashed box: y=1599–1757, x=112–271. QR pasted at inner top-left.
    "qr": {"x": 116, "y": 1605, "size": 148},
}




def generate_response(user_query: str) -> Optional[str]:
    """Sends query to LLM and returns text response."""
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": "You are Dr. GPT. Write a heartfelt, funny 'Prescription for Happiness' for a real doctor.",
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
        response = requests.post(f"{MODEL_URL}/v1/chat/completions", json=payload, timeout=30) 

        response.raise_for_status()  # Raise an error for non-2xx responses 

        res = response.json()

        response = res["choices"][0]["message"]["content"].strip() 

        print(response) 
        print("===") 
        print(type(response))
        return response 
    
    except Exception as e: 
        print(f"Error generating response: {e}") 
        raise f"Got error {e}" 
    


if __name__ == "__main__":
    # Example usage
    query = "what is ml?"
    result = generate_response(query)
    print(result) 





