"""
Data Models
Defines the Pydantic schemas for API requests and responses.
"""

from pydantic import BaseModel, Field
from typing import Optional


class EnhancePromptRequest(BaseModel):
    room_description: str = Field(
        ..., description="User provided description of the room"
    )
    image_path: Optional[str] = Field(
        None, description="Path to the uploaded room image for multimodal analysis"
    )


class EnhancePromptResponse(BaseModel):
    reasoning: str = Field("", description="Chain-of-thought reasoning for display")
    sd_prompt: str = Field(
        "", description="Stable Diffusion optimized comma-separated tags"
    )
    task_type: str = Field(
        "style",
        description="Task type for ControlNet adjustment: add, replace, material, style",
    )
    room_description: str
    success: bool
    error: Optional[str] = None


class GenerateImageRequest(BaseModel):
    enhanced_prompt: str
    room_description: str
    image_path: str = Field(..., description="Absolute path to the input image")
    target_resolution: int = Field(
        1024, description="Target resolution for the shortest side"
    )
    task_type: str = Field(
        "style",
        description="Task type for ControlNet adjustment: add, replace, material, style",
    )


class GenerateImageResponse(BaseModel):
    enhanced_prompt: Optional[str] = None
    image_path: Optional[str] = None
    success: bool
    error: Optional[str] = None


class RefineDesignRequest(BaseModel):
    """Request model for refining a previously generated design."""

    user_feedback: str = Field(
        ..., description="User's feedback/comments on the previous generation"
    )
    previous_reasoning: str = Field(
        ..., description="Previous generation's reasoning for context"
    )
    previous_sd_prompt: str = Field(..., description="Previous generation's SD prompt")
    previous_result_path: str = Field(
        ..., description="Path to the previously generated image"
    )
    original_image_path: str = Field(
        ..., description="Path to the original input image (for ComfyUI)"
    )
    target_resolution: int = Field(
        1024, description="Target resolution for the shortest side"
    )
    iteration: int = Field(1, description="Iteration number for this refinement")


class RefineDesignResponse(BaseModel):
    """Response model for design refinement."""

    reasoning: str = Field(
        "", description="Updated reasoning with feedback incorporated"
    )
    sd_prompt: str = Field("", description="Updated SD prompt")
    image_path: Optional[str] = None
    success: bool
    error: Optional[str] = None
