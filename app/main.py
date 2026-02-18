"""
FastAPI Backend
Exposes endpoints for prompt enhancement and image generation.
Serves the modern HTML frontend.
"""

import json
import shutil
import time
import uuid
from pathlib import Path
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from app.data_models import (
    EnhancePromptRequest,
    EnhancePromptResponse,
    GenerateImageRequest,
    GenerateImageResponse,
    RefineDesignRequest,
    RefineDesignResponse,
)
from app.img2img import ComfyUI
from app.prompt_enhancer import LLMClient
from app.config import DATA_INPUT_DIR, DATA_OUTPUT_DIR, PROJECT_ROOT

# Initialize App & Services
app = FastAPI(title="Virtual Staging API")
llm_client = LLMClient()
comfyui = ComfyUI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
frontend_path = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=frontend_path / "static"), name="static")


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def save_generation_metadata(
    image_path: str, prompt: str, description: str, resolution: int
):
    """Saves a sidecar JSON file with generation details."""
    try:
        path = Path(image_path)
        metadata = {
            "prompt": prompt,
            "description": description,
            "input_image": Path(image_path).name,
            "resolution_setting": resolution,
        }
        with open(path.with_suffix(".json"), "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
    except Exception as e:
        print(f"Metadata save failed: {e}")


# -----------------------------------------------------------------------------
# Frontend Routes
# -----------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the main HTML frontend."""
    html_path = frontend_path / "templates" / "index.html"
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()


# -----------------------------------------------------------------------------
# API Routes
# -----------------------------------------------------------------------------
@app.post("/save-input")
async def save_input(file: UploadFile = File(...)):
    """Save uploaded input image and return its path."""
    try:
        # Generate unique filename
        filename_str = file.filename or "image.png"
        ext = Path(filename_str).suffix or ".png"
        filename = f"input_{uuid.uuid4().hex[:8]}_{int(time.time())}{ext}"
        file_path = DATA_INPUT_DIR / filename

        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return {
            "success": True,
            "path": str(file_path),
            "url": f"/data/inputs/{filename}",
            "filename": filename,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/enhance-prompt", response_model=EnhancePromptResponse)
async def enhance_prompt(request: EnhancePromptRequest):
    """Enhance room description with optional image analysis (multimodal)."""
    try:
        # Pass image path if provided for multimodal analysis
        enhanced = llm_client.enhance_prompt(
            request.room_description, image_path=request.image_path
        )
        return EnhancePromptResponse(
            reasoning=enhanced.get("reasoning", ""),
            sd_prompt=enhanced.get("sd_prompt", ""),
            task_type=enhanced.get("task_type", "style"),
            room_description=request.room_description,
            success=True,
        )
    except Exception as e:
        return EnhancePromptResponse(
            success=False,
            error=str(e),
            reasoning="",
            sd_prompt="",
            task_type="style",
            room_description=request.room_description,
        )


@app.post("/generate-image", response_model=GenerateImageResponse)
async def generate_image(request: GenerateImageRequest):
    """Generate staged image from enhanced prompt with task-specific ControlNet settings."""
    try:
        output_path = comfyui.generate_image(
            request.enhanced_prompt,
            Path(request.image_path),
            request.target_resolution,
            task_type=request.task_type,
        )

        save_generation_metadata(
            output_path,
            request.enhanced_prompt,
            request.room_description,
            request.target_resolution,
        )

        return GenerateImageResponse(
            enhanced_prompt=request.enhanced_prompt,
            image_path=f"/data/outputs/{Path(output_path).name}",
            success=True,
        )
    except Exception as e:
        return GenerateImageResponse(success=False, error=str(e))


@app.post("/refine-design", response_model=RefineDesignResponse)
async def refine_design(request: RefineDesignRequest):
    """Refine a design based on user feedback and previous result."""
    try:
        # Construct full paths from relative paths
        # previous_result_path comes as filename or relative path, construct full path
        previous_result_full_path = (
            DATA_OUTPUT_DIR / Path(request.previous_result_path).name
        )

        # Verify the previous result image exists
        if not previous_result_full_path.exists():
            raise FileNotFoundError(
                f"Previous result image not found: {previous_result_full_path}"
            )

        # Ensure original image path exists
        original_image_full_path = Path(request.original_image_path)
        if not original_image_full_path.exists():
            # Try resolving from project root
            original_image_full_path = (
                PROJECT_ROOT / request.original_image_path.lstrip("/")
            )

        if not original_image_full_path.exists():
            raise FileNotFoundError(
                f"Original image not found: {request.original_image_path}"
            )

        # Step 1: Generate updated reasoning and SD prompt with feedback
        refined = llm_client.refine_design(
            user_feedback=request.user_feedback,
            previous_reasoning=request.previous_reasoning,
            previous_sd_prompt=request.previous_sd_prompt,
            previous_result_path=str(previous_result_full_path),
        )

        # Step 2: Generate new image using original input image
        # This ensures the new generation is still based on the original room
        output_path = comfyui.generate_image(
            refined["sd_prompt"],
            original_image_full_path,
            request.target_resolution,
            task_type=refined["task_type"],
        )

        save_generation_metadata(
            output_path,
            refined["sd_prompt"],
            f"Iteration {request.iteration}: {request.user_feedback}",
            request.target_resolution,
        )

        return RefineDesignResponse(
            reasoning=refined["reasoning"],
            sd_prompt=refined["sd_prompt"],
            image_path=f"/data/outputs/{Path(output_path).name}",
            success=True,
        )
    except Exception as e:
        return RefineDesignResponse(
            success=False, error=str(e), reasoning="", sd_prompt=""
        )


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# Mount data directories for serving images
app.mount("/data/inputs", StaticFiles(directory=DATA_INPUT_DIR), name="inputs")
app.mount("/data/outputs", StaticFiles(directory=DATA_OUTPUT_DIR), name="outputs")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
