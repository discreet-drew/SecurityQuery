from __future__ import annotations
import json
import time
from typing import Any
import requests


class OllamaClient:
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.1:8b",
        timeout_seconds: int = 90,
        retries: int = 1,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.retries = max(0, retries)
        self.session = session or requests.Session()

    def generate(self, prompt: str, *, json_mode: bool = False) -> str:
        payload: dict[str, Any] = {"model": self.model, "prompt": prompt, "stream": False}
        if json_mode:
            payload["format"] = "json"
        response = self.session.post(
            f"{self.base_url}/api/generate", json=payload, timeout=self.timeout_seconds
        )
        response.raise_for_status()
        body = response.json()
        answer = body.get("response")
        if not isinstance(answer, str):
            raise RuntimeError("Ollama response did not include a text 'response' field")
        return answer

    def generate_json(self, prompt: str) -> dict[str, Any]:
        last_error: Exception | None = None
        current_prompt = prompt
        for attempt in range(self.retries + 1):
            try:
                raw = self.generate(current_prompt, json_mode=True)
                parsed = json.loads(raw)
                if not isinstance(parsed, dict):
                    raise ValueError("Expected a JSON object")
                return parsed
            except (json.JSONDecodeError, ValueError, requests.RequestException, RuntimeError) as exc:
                last_error = exc
                if attempt < self.retries:
                    current_prompt = (
                        f"{prompt}\nYour previous response was invalid JSON ({exc}). Return a valid JSON object only."
                    )
                    time.sleep(0.1)
        raise RuntimeError(f"Ollama failed to return valid JSON: {last_error}") from last_error
