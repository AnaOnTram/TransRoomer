"""
Configuration Settings
Centralizes file paths, model constants, and system prompts.
"""
from pathlib import Path

# -----------------------------------------------------------------------------
# Path Configurations
# -----------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

# Data Directories
DATA_INPUT_DIR = PROJECT_ROOT / "data" / "inputs"
DATA_OUTPUT_DIR = PROJECT_ROOT / "data" / "outputs"
SAMPLES_DIR = PROJECT_ROOT / "data" / "samples"

# Ensure critical directories exist immediately
for directory in [DATA_INPUT_DIR, DATA_OUTPUT_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Model Configurations
# -----------------------------------------------------------------------------
OLLAMA_MODEL = "qwen3:4b"
CHECKPOINT_NAME = "juggernautXL_ragnarokBy.safetensors"

# -----------------------------------------------------------------------------
# System Prompts
# -----------------------------------------------------------------------------
SYSTEM_PROMPT = """Create a detailed Stable Diffusion prompt for interior design based on user's room description:

Focus on:
- Room type and style
- Furniture and decor
- Lighting and atmosphere
- Color scheme
- Architectural elements

Return ONLY the prompt without any explanations, reasoning, <think> tags, or thinking mode. 
/no_think"""