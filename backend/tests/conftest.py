"""
Pytest configuration and shared fixtures.
"""

import pytest
from app.config.settings import get_settings, Settings


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Provide test settings with safe defaults."""
    get_settings.cache_clear()
    return get_settings()
