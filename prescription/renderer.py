"""
renderer.py
───────────
Overlays handwritten Caveat font text on MedRite prescription template.
Every field placed at pixel-calibrated coordinates — zero overlaps guaranteed.
QR code stamped inside the dashed QR CODE box (bottom-left).
"""

import io, random
import qrcode
from PIL import Image, ImageDraw, ImageFont
from prescription.config import LAYOUT, TEMPLATE_FILE, FONT_PATH, FONT_SIZE, FONT_SIZE_SM, INK
from prescription.generator import PrescriptionContent

_CACHE: dict = {}

def _font(size: int) -> ImageFont.FreeTypeFont:
    if size not in _CACHE:
        _CACHE[size] = ImageFont.truetype(FONT_PATH, size)
    return _CACHE[size]


def _put(draw: ImageDraw.Draw, coord: dict, text: str, size: int):
    """Draw text at coord with tiny natural jitter. Skips empty strings."""
    if not text or not text.strip():
        return
    jx = random.randint(-1, 1)
    jy = random.randint(-1, 0)
    draw.text(
        (coord["x"] + jx, coord["y"] + jy),
        text,
        font=_font(size),
        fill=INK,
    )


def _clip(text: str, max_chars: int) -> str:
    """Truncate with ellipsis to prevent text overflow."""
    text = text.strip()
    return text if len(text) <= max_chars else text[:max_chars - 1] + "…"


def _make_qr(url: str, size_px: int) -> Image.Image:
    """Generate navy-blue QR code sized exactly size_px × size_px."""
    qr = qrcode.QRCode(
        version          = 1,
        error_correction = qrcode.constants.ERROR_CORRECT_M,
        box_size         = 5,
        border           = 2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(
        fill_color  = (20, 35, 140),
        back_color  = (255, 255, 255),
    ).convert("RGB")
    return img.resize((size_px, size_px), Image.LANCZOS)


def render(
    content:            PrescriptionContent,
    doctor_name:        str,
    specialty:          str,
    reg_no:             str,
    date_str:           str,
    google_profile_url: str,
) -> bytes:
    """
    Stamps all fields onto the MedRite template.
    Returns PNG bytes ready for HTTP response.
    """
    img  = Image.open(TEMPLATE_FILE).convert("RGB")
    draw = ImageDraw.Draw(img)
    L    = LAYOUT
    FS   = FONT_SIZE      # 40
    FSS  = FONT_SIZE_SM   # 32

    # ── Header ────────────────────────────────────────────────────────────────
    _put(draw, L["name"],      _clip(f"DR. {doctor_name.upper()}", 34), FS)
    _put(draw, L["age"],       "Timeless \u2661",                        FS)
    _put(draw, L["specialty"], _clip(specialty, 30),                     FS)
    _put(draw, L["gender"],    "Legend \u263a",                          FS)
    _put(draw, L["reg"],       _clip(reg_no, 26),                        FS)
    _put(draw, L["date"],      date_str,                                  FSS)

    # ── Diagnosis ─────────────────────────────────────────────────────────────
    _put(draw, L["diagnosis"], _clip(content.diagnosis + " \u263a", 56), FS)

    # ── Symptoms (5 rows) ─────────────────────────────────────────────────────
    for i, coord in enumerate(L["symptoms"]):
        if i < len(content.symptoms) and content.symptoms[i].strip():
            _put(draw, coord, _clip(content.symptoms[i], 64), FS)

    # ── Prescriptions (7 rows, each includes duration) ────────────────────────
    for i, coord in enumerate(L["prescriptions"]):
        if i < len(content.prescriptions) and content.prescriptions[i].strip():
            _put(draw, coord, _clip(content.prescriptions[i], 72), FS)

    # ── Doctor's Advice (2 lines inside pink box) ──────────────────────────────
    for i, coord in enumerate(L["advice"]):
        if i < len(content.advice_lines) and content.advice_lines[i].strip():
            _put(draw, coord, _clip(content.advice_lines[i], 82), FS)

    # ── Footer ────────────────────────────────────────────────────────────────
    _put(draw, L["refill"],   _clip(content.refill,   24), FS)
    _put(draw, L["followup"], _clip(content.followup, 40), FSS)
    _put(draw, L["dr_sig"],   "Dr. GPT \u263a",            FS)

    # ── QR code — inside the printed dashed QR CODE box ───────────────────────
    qr_cfg = L["qr"]
    qr_img = _make_qr(google_profile_url, qr_cfg["size"])
    img.paste(qr_img, (qr_cfg["x"], qr_cfg["y"]))

    # ── Serialise ─────────────────────────────────────────────────────────────
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()
