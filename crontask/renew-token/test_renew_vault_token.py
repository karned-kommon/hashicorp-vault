import os
import pytest
import requests
import redis
from renew_vault_token import Config, RedisClient, VaultTokenManager, main


class TestConfig:
    """Tests for the Config class."""

    def test_get_vault_addr_with_vault_addr_env(self, mock_env_vars):
        """Test get_vault_addr when VAULT_ADDR is set."""
        assert Config.get_vault_addr() == "http://vault:8200"

    def test_get_vault_addr_with_host_port_env(self, monkeypatch):
        """Test get_vault_addr when VAULT_HOST and VAULT_PORT are set."""
        # Clear VAULT_ADDR to test the fallback
        monkeypatch.delenv("VAULT_ADDR", raising=False)
        monkeypatch.setenv("VAULT_HOST", "vault")
        monkeypatch.setenv("VAULT_PORT", "8200")
        assert Config.get_vault_addr() == "http://vault:8200"

    def test_get_vault_token(self, mock_env_vars):
        """Test get_vault_token."""
        assert Config.get_vault_token() == "test-token"

    def test_get_redis_config(self, mock_env_vars):
        """Test get_redis_config."""
        redis_config = Config.get_redis_config()
        assert redis_config["host"] == "redis"
        assert redis_config["port"] == 6379
        assert redis_config["db"] == 0
        assert redis_config["password"] == "password"
        assert redis_config["decode_responses"] is True


class TestRedisClient:
    """Tests for the RedisClient class."""

    def test_create_client(self, mocker):
        """Test _create_client method."""
        mock_get_redis_config = mocker.patch('renew_vault_token.Config.get_redis_config')
        mock_redis = mocker.patch('redis.Redis')

        mock_get_redis_config.return_value = {
            "host": "redis",
            "port": 6379,
            "db": 0,
            "password": "password",
            "decode_responses": True
        }

        client = RedisClient()
        mock_redis.assert_called_once_with(
            host="redis",
            port=6379,
            db=0,
            password="password",
            decode_responses=True
        )

    def test_get(self, mocker):
        """Test get method."""
        mock_get_redis_config = mocker.patch('renew_vault_token.Config.get_redis_config')
        mock_redis = mocker.patch('redis.Redis')

        mock_redis_instance = mock_redis.return_value
        mock_redis_instance.get.return_value = "test-value"
        mock_get_redis_config.return_value = {}

        client = RedisClient()
        result = client.get("test-key")

        mock_redis_instance.get.assert_called_once_with("test-key")
        assert result == "test-value"

    def test_set(self, mocker):
        """Test set method."""
        mock_get_redis_config = mocker.patch('renew_vault_token.Config.get_redis_config')
        mock_redis = mocker.patch('redis.Redis')

        mock_redis_instance = mock_redis.return_value
        mock_get_redis_config.return_value = {}

        client = RedisClient()
        client.set("test-key", "test-value")

        mock_redis_instance.set.assert_called_once_with("test-key", "test-value")


class TestVaultTokenManager:
    """Tests for the VaultTokenManager class."""

    def test_init(self, mocker):
        """Test initialization."""
        mock_redis_client = mocker.patch('renew_vault_token.RedisClient')
        mock_config = mocker.patch('renew_vault_token.Config')

        mock_config.get_vault_addr.return_value = "http://vault:8200"
        mock_config.get_vault_token.return_value = "test-token"

        manager = VaultTokenManager()

        assert manager.vault_addr == "http://vault:8200"
        assert manager.initial_token == "test-token"
        assert manager.redis_client == mock_redis_client.return_value

    def test_get_token_from_redis(self, mocker):
        """Test get_token when token exists in Redis."""
        mock_redis_client = mocker.patch('renew_vault_token.RedisClient')
        mock_config = mocker.patch('renew_vault_token.Config')

        mock_redis_instance = mock_redis_client.return_value
        mock_redis_instance.get.return_value = "redis-token"
        mock_config.get_vault_addr.return_value = "http://vault:8200"
        mock_config.get_vault_token.return_value = "env-token"

        manager = VaultTokenManager()
        token = manager.get_token()

        mock_redis_instance.get.assert_called_once_with("vault_token")
        assert token == "redis-token"

    def test_get_token_from_env(self, mocker):
        """Test get_token when token doesn't exist in Redis."""
        mock_redis_client = mocker.patch('renew_vault_token.RedisClient')
        mock_config = mocker.patch('renew_vault_token.Config')

        mock_redis_instance = mock_redis_client.return_value
        mock_redis_instance.get.return_value = None
        mock_config.get_vault_addr.return_value = "http://vault:8200"
        mock_config.get_vault_token.return_value = "env-token"

        manager = VaultTokenManager()
        token = manager.get_token()

        mock_redis_instance.get.assert_called_once_with("vault_token")
        mock_redis_instance.set.assert_called_once_with("vault_token", "env-token")
        assert token == "env-token"

    def test_renew_token_success(self, mocker):
        """Test renew_token successful case."""
        mock_redis_client = mocker.patch('renew_vault_token.RedisClient')
        mock_config = mocker.patch('renew_vault_token.Config')
        mock_post = mocker.patch('requests.post')

        mock_redis_instance = mock_redis_client.return_value
        mock_redis_instance.get.return_value = "old-token"
        mock_config.get_vault_addr.return_value = "http://vault:8200"
        mock_config.get_vault_token.return_value = "env-token"

        mock_response = mocker.Mock()
        mock_response.json.return_value = {"auth": {"client_token": "new-token"}}
        mock_post.return_value = mock_response

        manager = VaultTokenManager()
        new_token = manager.renew_token()

        mock_post.assert_called_once_with(
            "http://vault:8200/v1/auth/token/renew-self",
            headers={"X-Vault-Token": "old-token"}
        )
        assert new_token == "new-token"

    def test_renew_token_failure(self, mocker):
        """Test renew_token failure case."""
        mock_redis_client = mocker.patch('renew_vault_token.RedisClient')
        mock_config = mocker.patch('renew_vault_token.Config')
        mock_post = mocker.patch('requests.post')

        mock_redis_instance = mock_redis_client.return_value
        mock_redis_instance.get.return_value = "old-token"
        mock_config.get_vault_addr.return_value = "http://vault:8200"
        mock_config.get_vault_token.return_value = "env-token"

        mock_post.side_effect = requests.exceptions.RequestException("Connection error")

        manager = VaultTokenManager()
        with pytest.raises(requests.exceptions.RequestException):
            manager.renew_token()

    def test_store_token(self, mocker):
        """Test store_token."""
        mock_redis_client = mocker.patch('renew_vault_token.RedisClient')
        mock_config = mocker.patch('renew_vault_token.Config')

        mock_redis_instance = mock_redis_client.return_value
        mock_config.get_vault_addr.return_value = "http://vault:8200"
        mock_config.get_vault_token.return_value = "env-token"

        manager = VaultTokenManager()
        manager.store_token("new-token")

        mock_redis_instance.set.assert_called_with("vault_token", "new-token")

    def test_get_vault_client(self, mocker):
        """Test get_vault_client."""
        mock_redis_client = mocker.patch('renew_vault_token.RedisClient')
        mock_config = mocker.patch('renew_vault_token.Config')
        mock_hvac_client = mocker.patch('hvac.Client')

        mock_redis_instance = mock_redis_client.return_value
        mock_redis_instance.get.return_value = "redis-token"
        mock_config.get_vault_addr.return_value = "http://vault:8200"
        mock_config.get_vault_token.return_value = "env-token"

        manager = VaultTokenManager()
        client = manager.get_vault_client()

        mock_hvac_client.assert_called_once_with(
            url="http://vault:8200",
            token="redis-token"
        )
        assert client == mock_hvac_client.return_value


def test_main_success(mocker):
    """Test main function successful case."""
    mock_token_manager_class = mocker.patch('renew_vault_token.VaultTokenManager')
    mock_token_manager = mock_token_manager_class.return_value
    mock_token_manager.renew_token.return_value = "new-token"

    main()

    mock_token_manager.renew_token.assert_called_once()
    mock_token_manager.store_token.assert_called_once_with("new-token")

def test_main_failure(mocker):
    """Test main function failure case."""
    mock_token_manager_class = mocker.patch('renew_vault_token.VaultTokenManager')
    mock_token_manager = mock_token_manager_class.return_value
    mock_token_manager.renew_token.side_effect = Exception("Test error")

    with pytest.raises(Exception):
        main()

    mock_token_manager.renew_token.assert_called_once()
    mock_token_manager.store_token.assert_not_called()
