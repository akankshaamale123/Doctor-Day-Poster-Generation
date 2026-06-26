import os
import textwrap
import math
from PIL import Image, ImageDraw, ImageFont
from typing import Optional, Dict

# Paths
UPLOADS_DIR = "uploads"
POSTERS_DIR = "posters"


# Colors
BG_COLOR = (240, 248, 255)       # Alice Blue
TITLE_COLOR = (0, 51, 102)       # Dark Blue
TEXT_COLOR = (51, 51, 51)        # Dark Gray
KEYWORD_COLOR = (0, 102, 153)    # Medium Blue
ACCENT_COLOR = (0, 153, 204)     # Light Blue
FOOTER_BG = (0, 51, 102)         # Dark Blue
FOOTER_TEXT = (220, 240, 255)    # Light Blue
STAR_FILLED = (255, 193, 7)      # Gold
STAR_EMPTY = (200, 200, 200)     # Gray


def get_fonts() -> Dict:
    """Load fonts with fallback to default."""
    try:
        return {
            'title': ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 60),
            'subtitle': ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 28),
            'body': ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 26),
            'keywords': ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 24),
            'rating': ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 36),
            'specialization': ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 24),
        }
    except IOError:
        print("⚠️ Arial fonts not found, using default")
        default = ImageFont.load_default()
        return {
            'title': default,
            'subtitle': default,
            'body': default,
            'keywords': default,
            'rating': default,
            'specialization': default,
        }


def draw_star(draw: ImageDraw.Draw, x: int, y: int, size: int, fill_color: tuple, outline_color: tuple):
    """Draw a 5-pointed star."""
    points = []
    for i in range(5):
        angle = math.radians(-90 + i * 72)
        points.append((x + size * math.cos(angle), y + size * math.sin(angle)))
        angle = math.radians(-90 + i * 72 + 36)
        points.append((x + size * 0.4 * math.cos(angle), y + size * 0.4 * math.sin(angle)))
    draw.polygon(points, fill=fill_color, outline=outline_color)


def generate_poster(
    doctor_data: Dict, 
    photo_path: Optional[str] = None, 
    output_filename: Optional[str] = None
) -> str:
    """
    Generates a poster and returns the path to saved image.
    """
    print("🖼️ Generating poster...")
    
    # Ensure output directory exists
    os.makedirs(POSTERS_DIR, exist_ok=True)
    
    # Generate output filename
    if not output_filename:
        safe_name = doctor_data.get("doctor_name", "doctor").replace(" ", "_").replace(".", "")
        output_filename = f"{safe_name}_poster.png"
    
    output_path = os.path.join(POSTERS_DIR, output_filename)
    
    # 1. Setup Canvas (Increased height to 1500 to fit footer properly)
    width, height = 800, 1500
    background_color = (240, 248, 255)  # Alice Blue
    poster = Image.new("RGB", (width, height), color=background_color)
    draw = ImageDraw.Draw(poster)
    
    # 2. Load Fonts (Adjusted sizes for better layout)
    try:
        font_title = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 52)
        font_subtitle = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 24)
        font_body = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 22)
        font_keywords = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 22)
        font_small_header = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 26)
    except IOError:
        print("⚠️ Arial fonts not found, using default")
        default = ImageFont.load_default()
        font_title = font_subtitle = font_body = font_keywords = font_small_header = default

    # 3. Add Doctor Photo
    try:
        photo_to_use = photo_path or DEFAULT_PHOTO
        if photo_to_use and os.path.exists(photo_to_use):
            doc_img = Image.open(photo_to_use)
            doc_img = doc_img.resize((280, 280))
            img_x = (width - 280) // 2
            poster.paste(doc_img, (img_x, 40))
            draw.rectangle([(img_x, 40), (img_x + 280, 320)], outline=(0, 51, 102), width=4)
    except Exception as e:
        print(f"⚠️ Could not load photo: {e}")

    # 4. Add Doctor Name
    y_text = 355
    name = doctor_data.get("doctor_name", "Doctor")
    draw.text((width/2, y_text), name, font=font_title, fill=(0, 51, 102), anchor="mm")
    
    # 5. Add Specialization
    y_text += 55
    specialization = doctor_data.get("specialization", "")
    if specialization:
        draw.text((width/2, y_text), specialization, font=font_subtitle, fill=(0, 102, 153), anchor="mm")
        y_text += 35
    
    # 6. Divider Line
    draw.line([(150, y_text), (650, y_text)], fill=(0, 153, 204), width=3)
    y_text += 30

    # 7. Add Professional Summary (Strictly 2-3 lines)
    # Fallback to both possible keys just in case
    summary_text = doctor_data.get("professional_summary") or doctor_data.get("review_summary", "Providing exceptional medical care with a focus on accurate diagnosis and patient well-being.")
    
    # Force wrap to roughly 2-3 lines
    wrapped_summary = textwrap.wrap(summary_text, width=60)
    for line in wrapped_summary[:3]:  # Limit to max 3 lines
        draw.text((width/2, y_text), line, font=font_body, fill=(51, 51, 51), anchor="mm")
        y_text += 30
    y_text += 20

    # 8. Add Keywords (Inline to save space)
    keywords = doctor_data.get("important_keywords", [])
    if keywords:
        draw.text((width/2, y_text), "What Patients Say:", font=font_small_header, fill=(0, 51, 102), anchor="mm")
        y_text += 35
        
        kw_string = "  •  ".join(keywords[:4]) # Max 4 keywords
        wrapped_kw = textwrap.wrap(kw_string, width=55)
        for line in wrapped_kw:
            draw.text((width/2, y_text), line, font=font_keywords, fill=(0, 102, 153), anchor="mm")
            y_text += 28
    y_text += 20

    # 9. Add Achievements
    achievements = doctor_data.get("achievements", [])
    if achievements:
        draw.text((100, y_text), "🏆 Achievements", font=font_small_header, fill=(0, 51, 102))
        y_text += 35
        for ach in achievements[:3]: 
            draw.text((120, y_text), f"✔  {ach}", font=font_body, fill=(51, 51, 51))
            y_text += 28
        y_text += 15

    # 10. Add Professional Highlights
    highlights = doctor_data.get("professional_highlights", [])
    if highlights:
        draw.text((100, y_text), "⭐ Professional Highlights", font=font_small_header, fill=(0, 51, 102))
        y_text += 35
        for hl in highlights[:3]:
            draw.text((120, y_text), f"✔  {hl}", font=font_body, fill=(51, 51, 51))
            y_text += 28

    # 11. Add Hospital Address (FOOTER - Fixed at bottom, guaranteed to print)
    address = doctor_data.get("hospital_address", "Contact us for appointments")
    
    # Draw footer background exactly at the bottom
    y_footer = height - 130
    draw.rectangle([(0, y_footer), (width, height)], fill=(0, 51, 102))
    
    # Add text inside footer safely
    y_text = y_footer + 35
    draw.text((width/2, y_text), "📍 Visit Us At:", font=font_subtitle, fill=(255, 255, 255), anchor="mm")
    y_text += 40
    
    # Wrap address to prevent it going out of bounds
    wrapped_addr = textwrap.wrap(address, width=50)
    for line in wrapped_addr[:2]: # Max 2 lines for address
        draw.text((width/2, y_text), line, font=font_body, fill=(220, 240, 255), anchor="mm")
        y_text += 30
    
    # 12. Save the Poster
    poster.save(output_path, quality=95)
    print(f"✅ Poster saved to {output_path}")
    
    return output_path