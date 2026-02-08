"""
Data Models
Defines the Pydantic schemas for API requests and responses.
"""
from pydantic import BaseModel, Field
from typing import Optional

class EnhancePromptRequest(BaseModel):
    room_description: str = Field(..., description="User provided description of the room")

class EnhancePromptResponse(BaseModel):
    enhanced_prompt: str
    room_description: str
    success: bool
    error: Optional[str] = None

class GenerateImageRequest(BaseModel):
    enhanced_prompt: str
    room_description: str
    image_path: str = Field(..., description="Absolute path to the input image")
    target_resolution: int = Field(1024, description="Target resolution for the shortest side")

class GenerateImageResponse(BaseModel):
    enhanced_prompt: Optional[str] = None
    image_path: Optional[str] = None
    success: bool
    error: Optional[str] = None