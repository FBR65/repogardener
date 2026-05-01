"""LLM client — unified interface for Ollama (local) and OpenRouter (cloud)."""
import json
import httpx

# LLM config mirrors Hermes defaults
DEFAULTS = {
    "provider": "ollama",
    "ollama": {"model": "kimi-k2.6:cloud", "base_url": "http://localhost:11434"},
    "openrouter": {"model": "deepseek/deepseek-v4-flash", "base_url": "https://openrouter.ai/api/v1"},
}


class LLMClient:
    def __init__(self, provider=None, model=None):
        self.provider = provider or DEFAULTS["provider"]
        cfg = DEFAULTS[self.provider]
        self.model = model or cfg["model"]
        self.base_url = cfg["base_url"]

    def chat(self, prompt: str, system: str = "", temperature=0.3) -> str:
        if self.provider == "ollama":
            return self._ollama_chat(prompt, system, temperature)
        else:
            return self._openrouter_chat(prompt, system, temperature)

    def _ollama_chat(self, prompt, system, temperature):
        body = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if system:
            body["system"] = system
        resp = httpx.post(f"{self.base_url}/api/generate", json=body, timeout=120)
        resp.raise_for_status()
        return resp.json()["response"]

    def _openrouter_chat(self, prompt, system, temperature):
        from os import getenv
        api_key = getenv("OPENROUTER_API_KEY", "")
        body = {
            "model": self.model,
            "messages": [],
            "temperature": temperature,
        }
        if system:
            body["messages"].append({"role": "system", "content": system})
        body["messages"].append({"role": "user", "content": prompt})
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        resp = httpx.post(
            f"{self.base_url}/chat/completions", json=body, headers=headers, timeout=120
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
