"""
tests/conftest.py
-----------------
Shared pytest configuration.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure pytest-asyncio
pytest_plugins = ["pytest_asyncio"]


def pytest_configure(config):
    """Configure pytest settings."""
    config.addinivalue_line("markers", "asyncio: mark test as async")
