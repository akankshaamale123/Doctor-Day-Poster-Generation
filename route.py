import os
import uuid
from typing import Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from werkzeug.utils import secure_filename
import json
from services.tavily_service import get_reviews_from_tavily
from services.llm_service import analyze_doctor_reviews
from services.poster_service import generate_poster, POSTERS_DIR, UPLOADS_DIR
from services.tavily_service import get_reviews_from_tavily, extract_text_from_specific_link
import traceback



# Models
from models import (
    AnalyzeRequest, 
    AnalyzeResponse, 
    CustomDataRequest, 
    ExtractByLinkRequest,
    HealthResponse, 
    ErrorResponse
)

# Services


# Config
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

# Create directories
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(POSTERS_DIR, exist_ok=True)

# ============================================
# Initialize FastAPI App
# ============================================
app = FastAPI(
    title="Doctor Poster Generator API",
    description="API to fetch doctor reviews, analyze them, and generate digital posters",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ============================================
# ROUTE 1: Health Check
# ============================================
@app.get("/api/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Check if API is running."""
    return HealthResponse(
        status="healthy",
        message="Doctor Poster API is running",
        version="1.0.0"
    )


# ============================================
# ROUTE 2: Analyze Doctor Reviews - CLEAN VERSION
# ============================================
@app.post("/api/analyze", tags=["Analysis"])
async def analyze_doctor(request: AnalyzeRequest):
    """
    Analyze doctor reviews and return structured JSON data.
    """
    try:
        result = analyze_doctor_reviews(request.doctor_name, request.address)
        
        if result:
            os.makedirs("output", exist_ok=True)

            filename = request.doctor_name.replace(" ", "_").replace("/", "_")
            filepath = os.path.join("output", f"{filename}.json")

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=4, ensure_ascii=False)

            return {
                "success": True,
                "data": result
            }
        else:
            return {
                "success": False,
                "error": "Could not analyze reviews. Not enough data found.",
                "doctor_name": request.doctor_name,
                "address": request.address
            }
            
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    

# ============================================
# ROUTE: Extract Full Prescription Profile from Link
# ============================================
@app.post("/api/extract-from-link", tags=["Data Extraction"])
async def extract_from_link(request: ExtractByLinkRequest):
    """
    Extracts Doctor's Name, Specializations, and Key Important Points.
    Specifically designed for generating doctor prescriptions.
    """
    try:
        # 1. Scrape ONLY the provided link
        raw_text = extract_text_from_specific_link(request.reviews_link)
        
        if not raw_text or len(raw_text) < 50:
            raise HTTPException(
                status_code=404, 
                detail="Could not read data from this link. Make sure it is a public profile."
            )
        
        # 2. Send to LLM with a STRICT prescription-focused prompt
        from services.llm_service import generate_response, extract_json_from_llm
        
        prescription_prompt = f"""
Read the following text extracted strictly from this link: {request.reviews_link}
This data is exclusively for {request.doctor_name}. 

Extract exactly three things for a medical prescription profile:
1. The exact full name of the doctor.
2. Key specializations: Specific areas of medical expertise and exact medical conditions they treat. (Provide 3 to 5 highly specific medical points).
3. Key important points: Read the patient experiences and extract 3 to 4 standout professional qualities or practices of this specific doctor. 

STRICT RULES FOR "key_important_points":
- Phrased as professional facts, NOT as reviews.
- ABSOLUTELY DO NOT use words like "review", "reviews", "patients say", "feedback", "rated", "according to people".
- Example of GOOD points: "Known for highly accurate diagnostics", "Spends ample time explaining conditions to families", "Maintains a strictly hygienic and advanced clinic".

Return ONLY a valid JSON object matching this exact structure:
{{
  "doctor_name": "Full Name",
  "key_specializations": ["Exact Medical Specialty 1", "Expertise in Specific Surgery 2"],
  "key_important_points": ["Standout professional quality 1", "Standout professional quality 2", "Standout professional quality 3"]
}}

Here is the text data:
---
{raw_text}
---
"""
        llm_response = generate_response(prescription_prompt)
        
        if not llm_response:
            raise HTTPException(status_code=503, detail="LLM failed to respond.")
            
        llm_data = extract_json_from_llm(llm_response)
        if not llm_data:
            raise HTTPException(status_code=500, detail="LLM returned invalid JSON.")
        
        # 3. Build the final clean data for the prescription (how_doctor_helps REMOVED)
        clean_data = {
            "doctor_name": llm_data.get("doctor_name", request.doctor_name),
            "key_specializations": llm_data.get("key_specializations", ["General Physician"]),
            "key_important_points": llm_data.get("key_important_points", ["Dedicated to patient well-being"])
        }
        
        # 4. Save to local folder
        save_folder = "extracted_data"
        os.makedirs(save_folder, exist_ok=True)
        filename = request.doctor_name.replace(" ", "_").replace("/", "_")
        filepath = os.path.join(save_folder, f"{filename}_prescription_data.json")

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(clean_data, f, indent=4, ensure_ascii=False)
        
        return {
            "success": True,
            "data": clean_data,
            "saved_to": filepath
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        print(f"❌ FULL TRACEBACK:\n{error_traceback}")
        raise HTTPException(status_code=500, detail={"error_message": str(e), "traceback": error_traceback})
    
# ============================================
# ROUTE 4: Upload Photo + Poster - CLEAN VERSION
# ============================================
@app.post("/api/generate-poster-with-photo", tags=["Poster Generation"])
async def create_poster_with_photo(
    doctor_name: str = Form(...),
    address: str = Form(...),
    photo: Optional[UploadFile] = File(...)
):
    """
    Upload doctor photo and generate poster with reviews.
    Returns PNG image file.
    """
    saved_photo_path = None
    
    try:
        if photo and photo.filename:
            if not allowed_file(photo.filename):
                raise HTTPException(status_code=400, detail="Invalid file type")
            
            filename = secure_filename(f"{uuid.uuid4()}_{photo.filename}")
            saved_photo_path = os.path.join(UPLOADS_DIR, filename)
            content = await photo.read()
            with open(saved_photo_path, "wb") as f:
                f.write(content)
        
        result = analyze_doctor_reviews(doctor_name, address)
        
        if not result:
            if saved_photo_path and os.path.exists(saved_photo_path):
                os.remove(saved_photo_path)
            raise HTTPException(status_code=404, detail="Could not analyze reviews.")
        
        poster_path = generate_poster(result, photo_path=saved_photo_path)
        filename = os.path.basename(poster_path)
        
        return FileResponse(
            path=poster_path,
            media_type="image/png",
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        if saved_photo_path and os.path.exists(saved_photo_path):
            os.remove(saved_photo_path)
        raise HTTPException(status_code=500, detail=str(e))



# ============================================
# ROUTE 6: Get Previously Generated Poster
# ============================================
@app.get(
    "/api/poster/{filename}",
    responses={
        200: {"content": {"image/png": {}}},
        404: {"model": ErrorResponse}
    },
    tags=["Poster Retrieval"]
)
async def get_poster(filename: str):
    """
    Retrieve a previously generated poster by filename.
    """
    try:
        safe_filename = secure_filename(filename)
        poster_path = os.path.join(POSTERS_DIR, safe_filename)
        
        if os.path.exists(poster_path):
            return FileResponse(
                path=poster_path,
                media_type="image/png",
                filename=safe_filename
            )
        else:
            raise HTTPException(status_code=404, detail="Poster not found")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# ROUTE 7: List All Generated Posters
# ============================================
@app.get("/api/posters", tags=["Poster Retrieval"])
async def list_posters():
    """List all generated poster filenames."""
    try:
        posters = []
        if os.path.exists(POSTERS_DIR):
            for f in os.listdir(POSTERS_DIR):
                if f.endswith('.png'):
                    posters.append(f)
        return {"success": True, "posters": posters, "count": len(posters)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# ROUTE 8: Delete a Generated Poster
# ============================================
@app.delete(
    "/api/poster/{filename}",
    responses={200: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    tags=["Poster Retrieval"]
)
async def delete_poster(filename: str):
    """Delete a generated poster."""
    try:
        safe_filename = secure_filename(filename)
        poster_path = os.path.join(POSTERS_DIR, safe_filename)
        
        if os.path.exists(poster_path):
            os.remove(poster_path)
            return {"success": True, "message": f"Deleted {safe_filename}"}
        else:
            raise HTTPException(status_code=404, detail="Poster not found")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    
