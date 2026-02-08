"""
Virtual Staging AI - App Module
Exposes key components for the backend and frontend interaction.
"""
from app.config import OLLAMA_MODEL, CHECKPOINT_NAME, SYSTEM_PROMPT
from app.data_models import (
    EnhancePromptRequest,
    EnhancePromptResponse,
    GenerateImageRequest,
    GenerateImageResponse
)
from app.img2img import ComfyUI
from app.main import app
from app.prompt_enhancer import Ollama
from app.workflow_manager import WorkflowManager