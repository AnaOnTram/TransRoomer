"""
Prompt Enhancer Module
Handles interaction with OpenAI-compatible LLM API with multimodal support (Qwen3VL).
Two-step process: 1) Generate reasoning from image+text, 2) Convert reasoning to SD tags.
"""

import base64
from pathlib import Path
from typing import Optional
import requests
from app.config import (
    LLM_API_URL,
    LLM_MODEL,
    SYSTEM_PROMPT,
    SD_PROMPT_SYSTEM,
    REFINEMENT_SYSTEM,
)


class LLMClient:
    def __init__(
        self,
        api_url: str = LLM_API_URL,
        model: str = LLM_MODEL,
        reasoning_prompt: str = SYSTEM_PROMPT,
        sd_prompt: str = SD_PROMPT_SYSTEM,
    ):
        self.api_url = api_url.rstrip("/")
        self.model = model
        self.reasoning_prompt = reasoning_prompt
        self.sd_prompt = sd_prompt

    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64 string."""
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")
        with open(path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    def _call_llm(self, system_prompt: str, user_content, max_tokens: int = 512) -> str:
        """Make API call to LLM."""
        response = requests.post(
            f"{self.api_url}/v1/chat/completions",
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                "temperature": 0.7,
                "max_tokens": max_tokens,
            },
            headers={"Content-Type": "application/json"},
            timeout=120,
        )

        if response.status_code != 200:
            raise RuntimeError(f"LLM API Error {response.status_code}: {response.text}")

        result = response.json()
        return result["choices"][0]["message"]["content"].strip()

    def generate_reasoning(
        self, room_description: str, image_path: Optional[str] = None
    ) -> str:
        """
        Step 1: Generate chain-of-thought reasoning from image and description.

        Args:
            room_description (str): Raw user input.
            image_path (str, optional): Path to the uploaded room image.

        Returns:
            str: Reasoning about the transformation (80-100 words).
        """
        try:
            # Build message content with optional image
            if image_path and Path(image_path).exists():
                base64_image = self._encode_image(image_path)
                user_content = [
                    {"type": "text", "text": room_description},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                    },
                ]
            else:
                user_content = room_description

            return self._call_llm(self.reasoning_prompt, user_content, max_tokens=512)

        except requests.exceptions.ConnectionError:
            raise Exception(
                f"Could not connect to LLM API at {self.api_url}. Is the service running?"
            )
        except Exception as e:
            raise Exception(f"LLM reasoning generation failed: {str(e)}")

    def convert_to_sd_prompt(self, reasoning: str) -> str:
        """
        Step 2: Convert reasoning into Stable Diffusion optimized comma-separated tags.

        Args:
            reasoning (str): The reasoning output from step 1.

        Returns:
            str: Comma-separated tags optimized for SD/CLIP.
        """
        try:
            user_content = f"Convert this interior design description into Stable Diffusion tags:\n\n{reasoning}"
            return self._call_llm(self.sd_prompt, user_content, max_tokens=256)

        except requests.exceptions.ConnectionError:
            raise Exception(
                f"Could not connect to LLM API at {self.api_url}. Is the service running?"
            )
        except Exception as e:
            raise Exception(f"SD prompt conversion failed: {str(e)}")

    def enhance_prompt(
        self, room_description: str, image_path: Optional[str] = None
    ) -> dict:
        """
        Two-step enhancement: Generate reasoning then convert to SD tags.

        Args:
            room_description (str): Raw user input.
            image_path (str, optional): Path to the uploaded room image.

        Returns:
            dict: Contains both 'reasoning' (for display) and 'sd_prompt' (for generation).
        """
        # Step 1: Generate reasoning
        reasoning = self.generate_reasoning(room_description, image_path)

        # Step 2: Convert to SD tags
        sd_prompt = self.convert_to_sd_prompt(reasoning)

        # Step 3: Detect task type for ControlNet adjustment
        task_type = self._detect_task_type(reasoning, room_description)

        return {"reasoning": reasoning, "sd_prompt": sd_prompt, "task_type": task_type}

    def _detect_task_type(self, reasoning: str, description: str) -> str:
        """Detect task type from reasoning and description for ControlNet adjustment."""
        text = (reasoning + " " + description).lower()

        # Check for object addition keywords
        if any(
            word in text
            for word in ["add", "place", "position", "insert", "put in", "include"]
        ):
            return "add"

        # Check for replacement keywords
        if any(
            word in text
            for word in ["replace", "swap", "change to", "switch", "instead of"]
        ):
            return "replace"

        # Check for material/surface changes
        if any(
            word in text
            for word in [
                "paint",
                "floor",
                "wall",
                "surface",
                "material",
                "finish",
                "texture",
            ]
        ):
            return "material"

        # Default to style transformation
        return "style"

    def refine_design(
        self,
        user_feedback: str,
        previous_reasoning: str,
        previous_sd_prompt: str,
        previous_result_path: str,
    ) -> dict:
        """
        Refine a design based on user feedback and the previous result.

        Args:
            user_feedback: User's comments/requests for changes
            previous_reasoning: Previous generation's reasoning
            previous_sd_prompt: Previous generation's SD prompt
            previous_result_path: Path to the previously generated image

        Returns:
            dict: Contains updated 'reasoning' and 'sd_prompt'
        """
        try:
            # Build multimodal content with previous result image
            base64_image = self._encode_image(previous_result_path)

            user_content = [
                {
                    "type": "text",
                    "text": f"Previous reasoning: {previous_reasoning}\n\nPrevious SD prompt: {previous_sd_prompt}\n\nUser feedback: {user_feedback}\n\nPlease provide an updated design reasoning that addresses the user's feedback.",
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                },
            ]

            # Step 1: Generate updated reasoning with feedback
            updated_reasoning = self._call_llm(
                REFINEMENT_SYSTEM, user_content, max_tokens=512
            )

            # Step 2: Convert updated reasoning to SD tags
            updated_sd_prompt = self.convert_to_sd_prompt(updated_reasoning)

            # Step 3: Detect task type
            task_type = self._detect_task_type(updated_reasoning, user_feedback)

            return {
                "reasoning": updated_reasoning,
                "sd_prompt": updated_sd_prompt,
                "task_type": task_type,
            }

        except requests.exceptions.ConnectionError:
            raise Exception(
                f"Could not connect to LLM API at {self.api_url}. Is the service running?"
            )
        except Exception as e:
            raise Exception(f"Design refinement failed: {str(e)}")
