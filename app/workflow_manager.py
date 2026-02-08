"""
Workflow Manager
Handles loading and modifying the ComfyUI workflow JSON format.
"""
import json
import random
import copy
from pathlib import Path
from PIL import Image

from app.config import CHECKPOINT_NAME

class WorkflowManager:
    DEFAULT_WORKFLOW_PATH = Path("workflows/virtual_staging_workflow.json")

    def __init__(self, workflow_path: str = None, checkpoint_name: str = CHECKPOINT_NAME):
        self.workflow_path = Path(workflow_path) if workflow_path else self.DEFAULT_WORKFLOW_PATH
        self.checkpoint_name = checkpoint_name
        self.base_workflow = self._load_base_workflow()
    
    def _load_base_workflow(self) -> dict:
        """Loads the template JSON workflow from disk."""
        # Handle relative path fallback if script is run from different locations
        if not self.workflow_path.exists():
            fallback = Path(__file__).parent.parent / self.DEFAULT_WORKFLOW_PATH
            if fallback.exists():
                self.workflow_path = fallback
            else:
                raise FileNotFoundError(f"Workflow file not found: {self.workflow_path}")
                
        with open(self.workflow_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def _get_image_dimensions(self, image_path: Path) -> tuple[int, int]:
        """Safely retrieves image dimensions, defaulting to 1024x1024 on error."""
        try:
            with Image.open(image_path) as img:
                return img.size
        except Exception as e:
            print(f"Warning: Could not read image size: {e}")
            return 1024, 1024

    def create_custom_workflow(self, prompt: str, input_image_path: Path, output_prefix: str, target_resolution: int = 1024) -> dict:
        """
        Generates a runtime workflow with specific inputs inserted.
        
        Modifications:
        1. Injects image path, prompt, seed, and checkpoint.
        2. Calculates scaling to ensure SDXL works at ~1024px.
        3. Optimizes topology: Bypasses the Upscale node if target resolution matches base resolution.
        """
        workflow = copy.deepcopy(self.base_workflow)
        
        # 1. Calculations
        width, height = self._get_image_dimensions(input_image_path)
        shortest_side = min(width, height)
        # Scale to ensure shortest side is 1024 for SDXL generation
        input_scale_factor = 1024 / shortest_side if shortest_side > 0 else 1.0
        final_scale_factor = target_resolution / 1024.0
        seed = random.randint(1, 1_000_000_000_000)

        # 2. Node Mapping (Node ID -> Input Key -> Value)
        # These IDs correspond to specific nodes in the virtual_staging_workflow.json
        node_updates = {
            "2":   {"image": input_image_path.name},      # Load Image Node
            "22":  {"text": prompt},                      # Positive Prompt Node
            "25":  {"seed": seed},                        # KSampler Node
            "7":   {"ckpt_name": self.checkpoint_name},   # Checkpoint Loader
            "213": {"factor": input_scale_factor},        # Initial Downscale Node
            "126": {"filename_prefix": output_prefix},    # Save Image Node
        }

        # Apply updates
        for node_id, inputs in node_updates.items():
            if node_id in workflow:
                workflow[node_id]["inputs"].update(inputs)

        # 3. Topology Optimization
        # If target is 1024, we don't need the final upscale step.
        is_base_res = abs(target_resolution - 1024) < 1
        
        if is_base_res:
            # Bypass Upscale: Connect VAE Decode (26) directly to Save Image (126)
            workflow["126"]["inputs"]["images"] = ["26", 0]
            # Remove Upscale Node (131) to keep graph clean
            workflow.pop("131", None)
        else:
            # Enable Upscale: Configure Upscale Node (131)
            if "131" in workflow:
                workflow["131"]["inputs"]["factor"] = final_scale_factor
                # Connect Upscale Node output to Save Image input
                workflow["126"]["inputs"]["images"] = ["131", 0]

        return workflow