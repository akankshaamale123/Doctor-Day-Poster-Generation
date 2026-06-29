from typing import Optional
from pathlib import Path
import json, os
from models import QuizPrescriptionInput
from services.tavily_service import extract_text_from_specific_link
from services.llm_service import generate_response, extract_json_from_llm
from fastapi import HTTPException
from prescription.generator import generate_content
import traceback
from prescription.renderer  import render
from prescription.config import TEMPLATE_FILE
from prescription.utils import make_reg_no, today, display_name
from fastapi.responses import FileResponse



# Config
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}


def _find_doctor_json(doctor_name: str) -> Optional[dict]:
    """
    Searches extracted_data/ for a JSON matching the doctor.

    Handles all filename patterns found in the actual JSONs:
      Dr._Anil_Sawarkar.json
      Dr._Bhagyashri_Abak_prescription_data.json
      Dr.Anjali_Khalane_prescription_data.json

    Also handles different JSON structures:
      { "doctor_name", "key_specializations", "key_important_points", "google_review_link" }
      { "doctor_name", "specialization", "main_key_points", "google_review_link" }
    """
    data_dir = Path(EXTRACTED_DATA_FOLDER)
    if not data_dir.exists():
        return None

    # Normalize search key: "Dr. Anil Sawarkar" → "anil_sawarkar"
    search_key = (
        doctor_name.lower()
        .replace("dr.", "").replace("dr ", "")
        .strip()
        .replace(" ", "_")
        .replace(".", "")
    )

    # 1. Filename match
    for json_file in data_dir.glob("*.json"):
        normalized_stem = json_file.stem.lower().replace(".", "").replace(" ", "_")
        if search_key in normalized_stem:
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                print(f"✅ Found by filename: {json_file.name}")
                return data
            except Exception:
                continue

    # 2. Content match — check doctor_name field inside each JSON
    for json_file in data_dir.glob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            stored = (
                data.get("doctor_name", "").lower()
                .replace("dr.", "").replace("dr ", "")
                .strip().replace(" ", "_").replace(".", "")
            )
            if search_key in stored or stored in search_key:
                print(f"✅ Found by content match: {json_file.name}")
                return data
        except Exception:
            continue

    print(f"⚠️  No JSON found for: {doctor_name}")
    return None


def _get_highlights(doctor_profile: dict) -> list:
    """
    Extract highlights from doctor JSON regardless of which key they're stored under.
    Handles both JSON structures present in extracted_data/.
    """
    # New format: key_important_points
    if doctor_profile.get("key_important_points"):
        return doctor_profile["key_important_points"]
    # Old format: main_key_points
    if doctor_profile.get("main_key_points"):
        return doctor_profile["main_key_points"]
    return []


def _get_specialization(doctor_profile: dict) -> Optional[str]:
    """Extract specialization from JSON regardless of key name."""
    # New format: list
    specs = doctor_profile.get("key_specializations")
    if specs and isinstance(specs, list):
        return specs[0]
    # Old format: string
    spec = doctor_profile.get("specialization")
    if spec:
        return spec
    return None


def _build_awards(
    quiz_score:     Optional[int],
    rewards:        Optional[str],
    doctor_profile: Optional[dict],
) -> Optional[str]:
    """
    Builds awards string for Gemini.
    Combines: quiz reward/badge + top professional highlight from extracted profile.
    """
    parts = []

    if rewards:
        parts.append(rewards)
    elif quiz_score is not None:
        if quiz_score >= 90:
            parts.append(f"Quiz Excellence Award — {quiz_score}/100, Top 10%")
        elif quiz_score >= 75:
            parts.append(f"Quiz High Scorer — {quiz_score}/100")
        else:
            parts.append(f"Doctor's Day Quiz Participant — {quiz_score}/100")

    if doctor_profile:
        highlights = _get_highlights(doctor_profile)
        if highlights:
            parts.append(highlights[0])

    return "; ".join(parts) if parts else None


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



# ══════════════════════════════════════════════════════════════════════════════
# ROUTE 5 — ⭐ NEW: Generate Prescription from Quiz Result
# ══════════════════════════════════════════════════════════════════════════════


