from pydantic import BaseModel, Field
from typing import Optional, List


class AnalyzeRequest(BaseModel):
    """Request model for /api/analyze endpoint"""
    doctor_name: str = Field(..., min_length=1, description="Doctor's full name")
    address: str = Field(default="", description="City or hospital location")


class CustomDataRequest(BaseModel):
    """Request model for /api/generate-from-data endpoint"""
    doctor_name: str = Field(..., min_length=1, description="Doctor's full name")
    specialization: Optional[str] = Field(default="General Physician", description="Doctor's specialization")
    hospital_address: Optional[str] = Field(default="Contact for address", description="Hospital/clinic address")
    review_summary: Optional[str] = Field(default="Excellent patient care.", description="Review summary text")
    important_keywords: Optional[List[str]] = Field(default=["Professional", "Caring"], description="List of keywords")
    key_themes: Optional[List[str]] = Field(default=None, description="List of themes")
    overall_sentiment: Optional[str] = Field(default="Positive", description="Overall sentiment")
    achievements: Optional[List[str]] = Field(default=None, description="List of achievements")
    professional_highlights: Optional[List[str]] = Field(default=None, description="List of professional highlights")
                


class AnalyzeResponse(BaseModel):
    """Response model for /api/analyze endpoint"""
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None
    doctor_name: Optional[str] = None
    address: Optional[str] = None


class HealthResponse(BaseModel):
    """Response model for /api/health endpoint"""
    status: str
    message: str
    version: str


class ErrorResponse(BaseModel):
    """Error response model"""
    success: bool = False
    error: str
    

class ExtractByLinkRequest(BaseModel):
    """Request model when user provides a direct link"""
    doctor_name : str = Field(..., min_length=1, description="Doctor's Name")
    reviews_link : str = Field(..., min_length=1, description= "Exact Google Maps or Practo profile link")
    
class QuizPrescriptionInput(BaseModel):
    """
    Data sent by the Quiz module after doctor completes the quiz.
    Only doctor_name and review_link are needed — everything else is auto-extracted.
    """
    doctor_name: str = Field(
        ...,
        description = "Doctor full name",
        example     = "Dr. Anil Sawarkar",
    )
    review_link: str = Field(
        ...,
        description = "Doctor profile URL (Google Maps / Practo) from quiz registration",
        example     = "https://www.google.com/search?q=Dr.+Anil+Sawarkar+Amravati+reviews",
    )