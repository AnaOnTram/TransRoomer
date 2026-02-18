"""
Prompt Enhancer Module
Handles interaction with OpenAI-compatible LLM API to convert raw descriptions into Stable Diffusion prompts.
"""

import os
import requests
from app.config import LLM_API_URL, LLM_MODEL, SYSTEM_PROMPT


class LLMClient:
    def __init__(
        self,
        api_url: str = LLM_API_URL,
        model: str = LLM_MODEL,
        system_prompt: str = SYSTEM_PROMPT,
    ):
        self.api_url = api_url.rstrip("/")
        self.model = model
        self.system_prompt = system_prompt

    def enhance_prompt(self, room_description: str) -> str:
        """
        Sends the user description to the LLM API and returns a refined prompt.

        Args:
            room_description (str): Raw user input.

        Returns:
            str: The enhanced prompt suitable for image generation.
        """
        try:
            prompt_content = f"{room_description}\n/no_think"

            response = requests.post(
                f"{self.api_url}/v1/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": prompt_content},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 1024,
                },
                headers={"Content-Type": "application/json"},
                timeout=60,
            )

            if response.status_code != 200:
                raise RuntimeError(
                    f"LLM API Error {response.status_code}: {response.text}"
                )

            result = response.json()
            return result["choices"][0]["message"]["content"].strip()

        except requests.exceptions.ConnectionError:
            raise Exception(
                f"Could not connect to LLM API at {self.api_url}. Is the service running?"
            )
        except Exception as e:
            raise Exception(f"LLM API interaction failed: {str(e)}")
