"""
generator.py
────────────
Google Gemini 2.5 Flash (free tier) — google-genai SDK

• Specialty-specific, heartfelt content — different every call
• Mentions years of experience and awards when provided
• 3-layer JSON parser: handles smart quotes, apostrophes, truncation
• Auto-retries once if response is truncated
• NEVER raises on bad JSON — always returns safe defaults
• Prescriptions include duration inline (template layout has one line per slot)
"""

import json, re, random, time
from dataclasses import dataclass
from typing import List, Optional
from google import genai
from google.genai import types
from  prescription.config import *

@dataclass
class PrescriptionContent:
    diagnosis:     str
    symptoms:      List[str]   # 5 items
    prescriptions: List[str]   # 7 items — each ends with " . Duration"
    advice_lines:  List[str]   # 2 lines inside advice box
    refill:        str
    followup:      str


# ── 3-layer JSON parser ────────────────────────────────────────────────────────

_SMART = [
    ("\u201c", '"'), ("\u201d", '"'),
    ("\u2018", '"'), ("\u2019", '"'),
    ("\u201e", '"'), ("\u201a", '"'),
    ("\u00ab", '"'), ("\u00bb", '"'),
]

def _clean(raw: str) -> str:
    t = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    t = re.sub(r"\s*```$", "", t.strip()).strip()
    for b, g in _SMART:
        t = t.replace(b, g)
    # Remove apostrophes — Gemini truncates mid-string after apostrophes
    t = re.sub(r"(?<=\w)'(?=\w)", "", t)   # contractions: don't → dont
    t = re.sub(r"'", " ", t)               # remaining singles → space
    t = re.sub(r",\s*([}\]])", r"\1", t)   # trailing commas
    s = t.find("{")
    if s != -1:
        t = t[s:]
    t += "}" * max(0, t.count("{") - t.count("}"))
    t += "]" * max(0, t.count("[") - t.count("]"))
    return t


def _regex(text: str) -> dict:
    """Field-by-field regex fallback — works even on truncated JSON."""
    result = {}
    for f in ["diagnosis", "advice_line_1", "advice_line_2", "refill", "followup"]:
        m = re.search(r'"' + re.escape(f) + r'"\s*:\s*"([^"\n]{1,200})"', text)
        if m:
            result[f] = m.group(1).strip()
    for f in ["symptoms", "prescriptions"]:
        m = re.search(r'"' + re.escape(f) + r'"\s*:\s*\[([^\]]*)', text, re.DOTALL)
        if m:
            items = re.findall(r'"([^"\n]{1,80})"', m.group(1))
            if items:
                result[f] = [i.strip() for i in items]
    return result


def _parse(raw: str) -> dict:
    """3-layer parser — never raises."""
    try:
        return json.loads(raw)
    except Exception:
        pass
    c = _clean(raw)
    try:
        return json.loads(c)
    except Exception:
        pass
    m = re.search(r"\{[\s\S]*\}", c)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    result = _regex(c)
    if not result.get("diagnosis"):
        result = _regex(raw)
    return result


# ── Prompt ─────────────────────────────────────────────────────────────────────

def _prompt(name: str, specialty: str,
            years_exp: Optional[int], awards: Optional[str], seed: int) -> str:

    exp_line   = f"\n- Experience: {years_exp} years of dedicated practice" if years_exp else ""
    award_line = f"\n- Awards: {awards}" if awards else ""
    exp_note   = (
        f"In one symptom or prescription, meaningfully mention "
        f"their {years_exp} years of experience — make it personal and warm."
        if years_exp else ""
    )

    return f"""You are Dr. GPT. Write a heartfelt, funny "Prescription for Happiness" for a real doctor.

Doctor:
- Name: DR. {name.upper()}
- Specialty: {specialty}{exp_line}{award_line}
- Creativity seed (generate COMPLETELY FRESH, unique content): {seed}

{exp_note}

=== STRICT OUTPUT RULES (machine-parsed) ===
1. Output ONLY the JSON object. No markdown, no code fences, no explanation before or after.
2. Use ONLY straight ASCII double-quote characters ( " ). Never curly/smart quotes.
3. Never use apostrophes inside any string value. Write "dont" not "don't".
4. Every string must end with a double-quote before the next comma or bracket.
5. No trailing commas before }} or ]].
6. Symptoms: max 60 chars. Must be 100% specific to {specialty} — inside jokes only they get.
7. Prescriptions: include duration at end, separated by " . ".
   Format: "Prescription text . Duration"
   Durations: OD x 7 days / Q90D / BID Daily / Unlimited PRN / 60 min/day / Strictly / SOS
8. Each prescription line: max 68 chars total.
9. Advice line 2 must end with the Unicode heart symbol \u2665.
10. Make it genuinely heartfelt — the doctor must feel truly seen and appreciated.

=== RETURN THIS EXACT JSON STRUCTURE ===
{{
  "diagnosis": "Funny 3-5 word burnout diagnosis specific to {specialty}",
  "symptoms": [
    "Symptom 1 — unique {specialty} burnout sign, under 60 chars",
    "Symptom 2 — unique {specialty} daily grind, under 60 chars",
    "Symptom 3 — skipped meals or zero breaks, {specialty} twist",
    "Symptom 4 — phone or WhatsApp overuse, {specialty} context",
    "Symptom 5 — funny irony: {specialty} doctor ignoring own health"
  ],
  "prescriptions": [
    "8 hours uninterrupted sleep . OD x 7 days",
    "One full vacation, zero work calls . Q90D",
    "Self-care time, just for you . BID Daily",
    "Chai or Coffee or Green Tea . Unlimited PRN",
    "Family laughter, mandatory dose . 60 min/day",
    "Ignore all calls after 9 PM . Strictly",
    "One {specialty}-specific fun activity . SOS"
  ],
  "advice_line_1": "Warm personal line about the unique burden of being a {specialty} doctor. Max 72 chars.",
  "advice_line_2": "Hopeful, loving closer. End with the heart symbol \u2665. Max 72 chars.",
  "refill": "UNLIMITED",
  "followup": "30 days or when you feel like it"
}}"""


# ── Main ───────────────────────────────────────────────────────────────────────

def generate_content(
    doctor_name:    str,
    specialty:      str,
    years_exp:      Optional[int] = None,
    awards:         Optional[str] = None,
) -> PrescriptionContent:
    """
    Calls Gemini 2.5 Flash. Returns unique prescription content every call.
    Auto-retries once if the response is truncated (< 4 symptoms).
    Never raises on JSON parse failure — uses safe defaults instead.
    """
    # client = genai.Client(api_key=gemini_api_key)
    ## if gemini 
    # def _call(seed: int) -> dict:
    #     response = client.models.generate_content(
    #         model    = "gemini-2.5-flash",
    #         contents = _prompt(doctor_name, specialty, years_exp, awards, seed),
    #         config   = types.GenerateContentConfig(
    #             temperature       = 0.85,
    #             max_output_tokens = 2048,   # large enough to prevent truncation
    #         ),
    #     )
    #     return _parse(response.text.strip())

    def _call(seed: int) -> dict:
        response = generate_response(
            user_query = _prompt(doctor_name, specialty, years_exp, awards, seed),
        )
        return _parse(response.strip()) 
    
    data = _call(random.randint(1000, 9999))

    # Retry once if truncated
    if len([s for s in data.get("symptoms", []) if s.strip()]) < 4:
        time.sleep(1)
        data2 = _call(random.randint(1000, 9999))
        if len(data2.get("symptoms", [])) > len(data.get("symptoms", [])):
            data = data2

    def _lst(key: str, n: int, fallback: str = "") -> List[str]:
        items = [str(x).strip() for x in data.get(key, [])][:n]
        while len(items) < n:
            items.append(fallback)
        return items

    symptoms      = [s[:62] for s in _lst("symptoms",      5, "Long hours, no breaks")]
    prescriptions = [s[:70] for s in _lst("prescriptions", 7, "Rest and recharge . Daily")]

    adv1 = str(data.get(
        "advice_line_1",
        f"You give everything to your patients every single day..."
    )).strip()[:74]
    adv2 = str(data.get(
        "advice_line_2",
        "Dont forget to care for yourself too. \u2665"
    )).strip()[:74]

    refill   = str(data.get("refill",   "UNLIMITED")).strip()
    followup = str(data.get("followup", "30 days (or when you feel like it)")).strip()
    if "\u263a" not in refill and "\u2665" not in refill:
        refill = refill.rstrip() + " \u263a"

    return PrescriptionContent(
        diagnosis     = str(data.get("diagnosis", "Chronic Overwork Syndrome")).strip()[:56],
        symptoms      = symptoms,
        prescriptions = prescriptions,
        advice_lines  = [adv1, adv2],
        refill        = refill,
        followup      = followup,
    )
