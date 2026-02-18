"""
Image-to-Image Controller
Orchestrates the image generation process via ComfyUI.
"""

import shutil
import time
import requests
from pathlib import Path

from app.workflow_manager import WorkflowManager
from app.config import DATA_OUTPUT_DIR, COMFYUI_BASE_PATH


class ComfyUI:
    # Default Paths - use ~/ComfyUI as base
    BASE_PATH = Path(COMFYUI_BASE_PATH).expanduser().resolve()
    INPUT_DIR = BASE_PATH / "input"
    OUTPUT_DIR = BASE_PATH / "output"
    SERVER_URL = "http://127.0.0.1:8188"

    def __init__(self, server_address: str = None):
        if server_address:
            self.SERVER_URL = f"http://{server_address}"

        self.workflow_manager = WorkflowManager()

        # Ensure directories exist
        self.INPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def generate_image(
        self,
        prompt: str,
        input_image_path: Path,
        target_resolution: int = 1024,
        task_type: str = "style",
    ) -> str:
        """
        Main entry point to generate a staged image.

        Steps:
        1. Prepares input file in ComfyUI directory.
        2. Submits workflow.
        3. Waits for completion.
        4. Retrieves and moves output file.
        """
        if not input_image_path.exists():
            raise FileNotFoundError(f"Input image not found: {input_image_path}")

        # Determine file sequence
        try:
            number = input_image_path.stem.split("_")[-1]
        except IndexError:
            number = "00001"

        final_output_path = DATA_OUTPUT_DIR / f"virtual_staging_{number}.png"
        temp_prefix = f"vs_temp_{number}_{int(time.time())}_"

        comfy_input_path = None

        try:
            # 1. Prepare
            comfy_input_path = self._copy_to_comfy_input(input_image_path)

            # 2. Create Workflow with task-specific ControlNet settings
            workflow = self.workflow_manager.create_custom_workflow(
                prompt=prompt,
                input_image_path=input_image_path,
                output_prefix=temp_prefix,
                target_resolution=target_resolution,
                task_type=task_type,
            )

            # 3. Queue & Wait
            prompt_id = self._queue_prompt(workflow)
            generated_filename = self._wait_for_generation(prompt_id)

            # 4. Retrieve & Cleanup
            return self._retrieve_result(
                generated_filename, temp_prefix, final_output_path
            )

        finally:
            # Always clean up the input copy
            if comfy_input_path and comfy_input_path.exists():
                try:
                    comfy_input_path.unlink()
                except OSError:
                    pass

    def _copy_to_comfy_input(self, source: Path) -> Path:
        """Copies the source image to the ComfyUI input folder."""
        target = self.INPUT_DIR / source.name
        shutil.copy2(source, target)
        return target

    def _queue_prompt(self, workflow: dict) -> str:
        """Submits the workflow to the ComfyUI API."""
        try:
            res = requests.post(f"{self.SERVER_URL}/prompt", json={"prompt": workflow})
            if res.status_code != 200:
                raise RuntimeError(f"ComfyUI Error {res.status_code}: {res.text}")
            return res.json()["prompt_id"]
        except requests.exceptions.ConnectionError:
            raise RuntimeError("Could not connect to ComfyUI. Is the service running?")

    def _wait_for_generation(self, prompt_id: str, timeout: int = 600) -> str:
        """Polls the history endpoint until the specific prompt ID is finished."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                res = requests.get(f"{self.SERVER_URL}/history/{prompt_id}")
                if res.status_code == 200:
                    history = res.json()
                    if prompt_id in history:
                        # Extract filename from outputs
                        outputs = history[prompt_id].get("outputs", {})
                        for node_output in outputs.values():
                            for img in node_output.get("images", []):
                                if img.get("type") == "output":
                                    return img["filename"]
            except Exception:
                pass  # Transient network errors or partial JSON ignored
            time.sleep(1)

        raise TimeoutError("Image generation timed out.")

    def _retrieve_result(self, filename: str, prefix: str, destination: Path) -> str:
        """Finds the generated file in ComfyUI output, moves it, and cleans up."""
        source_file = self.OUTPUT_DIR / filename

        # Strategy 1: Direct Filename Match
        if source_file.exists():
            shutil.copy2(source_file, destination)
            try:
                source_file.unlink()
            except:
                pass
            return str(destination)

        # Strategy 2: Prefix Match (Fallback)
        candidates = list(self.OUTPUT_DIR.glob(f"{prefix}*"))
        if candidates:
            shutil.copy2(candidates[0], destination)
            try:
                candidates[0].unlink()
            except:
                pass
            return str(destination)

        raise RuntimeError(f"Generated file missing from {self.OUTPUT_DIR}")
