"""utils.py — Reg number, date, name helpers."""
import random
from datetime import datetime

_REG_PREFIXES = {
    "gynaecology": "MCI/GYN",  "gynecology":   "MCI/GYN",
    "cardiology":  "MCI/CARD", "cardiac":       "MCI/CARD",
    "dermatology": "MCI/DERM", "dentistry":     "MCI/DENT",
    "dental":      "MCI/DENT", "orthopedics":   "MCI/ORTH",
    "orthopaedics":"MCI/ORTH", "pediatrics":    "MCI/PED",
    "paediatrics": "MCI/PED",  "psychiatry":    "MCI/PSY",
    "neurology":   "MCI/NEURO","ophthalmology": "MCI/OPH",
    "surgery":     "MCI/SURG", "oncology":      "MCI/ONC",
    "ent":         "MCI/ENT",  "radiology":     "MCI/RAD",
    "urology":     "MCI/URO",  "nephrology":    "MCI/NEPH",
    "pulmonology": "MCI/PULM", "endocrinology": "MCI/ENDO",
    "gastro":      "MCI/GAST", "rheumatology":  "MCI/RHEU",
}

def make_reg_no(specialty: str) -> str:
    s = specialty.lower().strip()
    for key, prefix in _REG_PREFIXES.items():
        if key in s or s in key:
            return f"{prefix}-{random.randint(10000, 99999)}"
    return f"MCI/GP-{random.randint(10000, 99999)}"

def today() -> str:
    return datetime.now().strftime("%d/%m/%Y")

def display_name(name: str) -> str:
    """Strip any existing Dr. prefix — renderer adds DR. (uppercase)."""
    n = name.strip()
    for p in ["Dr. ", "DR. ", "Dr.", "DR.", "dr. ", "dr."]:
        if n.startswith(p):
            n = n[len(p):]
            break
    return n.strip()



