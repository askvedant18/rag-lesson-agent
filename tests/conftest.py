"""
Pytest configuration for hermetic offline testing.
Ensures unit tests never depend on external network calls or burn live API quota.
"""

import os
import pytest
from llm import LLMClient

@pytest.fixture(autouse=True)
def force_offline_mode_for_tests(monkeypatch):
    """Ensures tests run in hermetic offline simulation mode."""
    monkeypatch.setenv("GEMINI_API_KEY", "")
    from llm import _default_client
    import llm
    llm._default_client = LLMClient(api_key="")
