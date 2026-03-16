"""Configuration management for Sentient Printer."""

import copy
import os
import yaml


INSTALLED_CONFIG_PATH = "/usr/local/etc/sentient-printer.yaml"
DEV_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "sentient-printer.yaml")

DEFAULTS = {
    "real_printer": "",
    "personality": "passive-aggressive",
    "llm": {
        "provider": "openai",
        "model": "",
        "api_key": "",
        "base_url": "",
    },
}

DEFAULT_MODELS = {
    "openai": "gpt-4o",
    "anthropic": "claude-sonnet-4-20250514",
    "ollama": "llama3.1",
}


def load_config() -> dict:
    """Load config from installed path, falling back to dev path."""
    config_path = None
    for path in [INSTALLED_CONFIG_PATH, DEV_CONFIG_PATH]:
        if os.path.exists(path):
            config_path = path
            break

    config = copy.deepcopy(DEFAULTS)

    if config_path:
        with open(config_path, "r") as f:
            user_config = yaml.safe_load(f) or {}

        if "real_printer" in user_config:
            config["real_printer"] = user_config["real_printer"]
        if "personality" in user_config:
            config["personality"] = user_config["personality"]
        if "custom_prompt" in user_config:
            config["custom_prompt"] = user_config["custom_prompt"]

        if "llm" in user_config and isinstance(user_config["llm"], dict):
            for key in config["llm"]:
                if key in user_config["llm"]:
                    config["llm"][key] = user_config["llm"][key]

    # Apply default model if not set
    provider = config["llm"]["provider"]
    if not config["llm"]["model"] and provider in DEFAULT_MODELS:
        config["llm"]["model"] = DEFAULT_MODELS[provider]

    return config
