import os
import pytest


@pytest.fixture
def mock_env_vars():
    """Fixture to set up environment variables for testing."""
    original_environ = os.environ.copy()

    # Set up test environment variables
    os.environ.update({
        "VAULT_HOST": "http://vault",
        "VAULT_PORT": "8200",
        "VAULT_TOKEN": "test-token",
        "REDIS_HOST": "redis",
        "REDIS_PORT": "6379",
        "REDIS_DB": "0",
        "REDIS_PASSWORD": "password"
    })

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_environ)
