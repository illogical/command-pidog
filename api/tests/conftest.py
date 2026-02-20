"""Test fixtures: mock PiDog, test client, app with mock hardware."""

import pytest
from fastapi.testclient import TestClient

# Force mock mode before importing the app
import os
os.environ["PIDOG_MOCK_HARDWARE"] = "true"

from app.main import app  # noqa: E402


@pytest.fixture
def client():
    """Test client with mock PiDog hardware."""
    with TestClient(app) as c:
        yield c
