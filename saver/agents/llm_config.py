"""LLM provider configuration — auto-detects from available API keys."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

PROVIDER_CONFIGS = {
    "nvidia": {
        "base_url": "https://integrate.api.nvidia.com/v1",
        "default_model": "nvidia/llama-3.3-nemotron-super-49b-v1",
        "api_key_env": "NVIDIA_API_KEY",
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com/v1",
        "default_model": "claude-sonnet-4-20250514",
        "api_key_env": "ANTHROPIC_API_KEY",
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
        "api_key_env": "GROQ_API_KEY",
    },
}


def detect_provider() -> str:
    """Auto-detect which provider to use based on available API keys."""
    explicit = os.environ.get("LLM_PROVIDER", "").lower()
    if explicit in PROVIDER_CONFIGS:
        return explicit
    for provider in ["nvidia", "groq", "anthropic"]:
        key_env = PROVIDER_CONFIGS[provider]["api_key_env"]
        if os.environ.get(key_env):
            return provider
    return "nvidia"


def get_llm(model: str | None = None) -> ChatOpenAI:
    """Get an LLM instance — auto-detects provider from available API keys."""
    provider = detect_provider()
    config = PROVIDER_CONFIGS[provider]

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=model or os.environ.get("SUPERVISOR_MODEL", config["default_model"]),
            api_key=os.environ.get(config["api_key_env"], ""),
            temperature=0.3,
            max_tokens=2048,
        )

    return ChatOpenAI(
        model=model or os.environ.get("SUPERVISOR_MODEL", config["default_model"]),
        base_url=config["base_url"],
        api_key=os.environ.get(config["api_key_env"], ""),
        temperature=0.3,
        max_tokens=2048,
    )
