import os
import uuid
from typing import Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from werkzeug.utils import secure_filename

# Models
from models import (
    AnalyzeRequest, 
    AnalyzeResponse, 
    CustomDataRequest, 
    HealthResponse, 
    ErrorResponse
)

# Services
from services.llm_service import analyze_doctor_reviews
from services.poster_service import generate_poster, POSTERS_DIR, UPLOADS_DIR

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