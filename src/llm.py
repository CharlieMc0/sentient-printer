"""LLM client for Sentient Printer. Supports OpenAI, Anthropic, and Ollama."""

import sys
import requests

from personalities import get_system_prompt

TIMEOUT = 30
MAX_TOKENS = 300
TEMPERATURE = 0.9
MAX_CHARS = 8000


def get_commentary(text: str, personality: str, config: dict) -> str:
    """Get LLM commentary on a printed document.

    Args:
        text: Extracted text from the printed document.
        personality: Personality name.
        config: Full config dict (needs config["llm"] and optionally config["custom_prompt"]).

    Returns:
        Commentary string from the LLM.

    Raises:
        Exception on any failure (caller should catch and fail open).
    """
    llm_config = config["llm"]
    provider = llm_config["provider"]
    custom_prompt = config.get("custom_prompt", "")
    system_prompt = get_system_prompt(personality, custom_prompt)

    # Validate API key for cloud providers
    if provider in ("openai", "anthropic") and not llm_config.get("api_key"):
        raise ValueError(f"{provider} API key not configured")

    # Truncate very long documents to avoid token limits
    if len(text) > MAX_CHARS:
        print(
            f"SENTIENT-PRINTER: Truncating document from {len(text)} to {MAX_CHARS} chars",
            file=sys.stderr,
        )
        text = text[:MAX_CHARS] + "\n\n[Document truncated for analysis...]"

    user_message = f"Here is the document that was just printed:\n\n{text}"

    providers = {
        "openai": _call_openai,
        "anthropic": _call_anthropic,
        "ollama": _call_ollama,
    }
    call_fn = providers.get(provider)
    if not call_fn:
        raise ValueError(f"Unknown LLM provider: {provider}")
    return call_fn(system_prompt, user_message, llm_config)


def _call_openai(system_prompt: str, user_message: str, llm_config: dict) -> str:
    base_url = llm_config.get("base_url") or "https://api.openai.com/v1"
    url = f"{base_url.rstrip('/')}/chat/completions"

    resp = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {llm_config['api_key']}",
            "Content-Type": "application/json",
        },
        json={
            "model": llm_config["model"],
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "max_tokens": MAX_TOKENS,
            "temperature": TEMPERATURE,
        },
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def _call_anthropic(system_prompt: str, user_message: str, llm_config: dict) -> str:
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": llm_config["api_key"],
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        json={
            "model": llm_config["model"],
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_message},
            ],
            "max_tokens": MAX_TOKENS,
            "temperature": TEMPERATURE,
        },
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["content"][0]["text"].strip()


def _call_ollama(system_prompt: str, user_message: str, llm_config: dict) -> str:
    base_url = llm_config.get("base_url") or "http://localhost:11434"
    url = f"{base_url.rstrip('/')}/api/chat"

    resp = requests.post(
        url,
        json={
            "model": llm_config["model"],
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "stream": False,
            "options": {
                "temperature": TEMPERATURE,
                "num_predict": MAX_TOKENS,
            },
        },
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"].strip()
