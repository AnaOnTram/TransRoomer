"""
FastAPI Backend
Exposes endpoints for prompt enhancement and image generation.
"""

import json
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.data_models import (
    EnhancePromptRequest,
    EnhancePromptResponse,
    GenerateImageRequest,
    GenerateImageResponse,
)
from app.img2img import ComfyUI
from app.prompt_enhancer import LLMClient

# Initialize App & Services
app = FastAPI(title="Virtual Staging API")
llm_client = LLMClient()
comfyui = ComfyUI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
            "input_image": Path(image_path).name,  # Storing filename primarily
            "resolution_setting": resolution,
        }
        with open(path.with_suffix(".json"), "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
    except Exception as e:
        print(f"Metadata save failed: {e}")


# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------


@app.post("/enhance-prompt", response_model=EnhancePromptResponse)
async def enhance_prompt(request: EnhancePromptRequest):
    """Enhance room description into SD prompt."""
    try:
        enhanced = llm_client.enhance_prompt(request.room_description)
        return EnhancePromptResponse(
            enhanced_prompt=enhanced,
            room_description=request.room_description,
            success=True,
        )
    except Exception as e:
        return EnhancePromptResponse(
            success=False, error=str(e), enhanced_prompt="", room_description=""
        )


@app.post("/generate-image", response_model=GenerateImageResponse)
async def generate_image(request: GenerateImageRequest):
    """Generate staged image from enhanced prompt."""
    try:
        output_path = comfyui.generate_image(
            request.enhanced_prompt, Path(request.image_path), request.target_resolution
        )

        save_generation_metadata(
            output_path,
            request.enhanced_prompt,
            request.room_description,
            request.target_resolution,
        )

        return GenerateImageResponse(
            enhanced_prompt=request.enhanced_prompt,
            image_path=output_path,
            success=True,
        )
    except Exception as e:
        return GenerateImageResponse(success=False, error=str(e))


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
