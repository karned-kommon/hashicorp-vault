import os
import requests
import redis
import logging
import hvac
import datetime
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class Config:

    @staticmethod
    def get_vault_addr():
        host = os.environ["VAULT_HOST"]
        port = os.environ["VAULT_PORT"]
        return f"{host}:{port}"

    @staticmethod
    def get_vault_token():
        return os.environ["VAULT_TOKEN"]

    @staticmethod
    def get_redis_config():
        return {
            "host": os.environ["REDIS_HOST"],
            "port": int(os.environ["REDIS_PORT"]),
            "db": int(os.environ["REDIS_DB"]),
            "password": os.environ["REDIS_PASSWORD"],
            "decode_responses": True
        }


class RedisClient:

    def __init__(self):
        self.config = Config.get_redis_config()
        self.client = self._create_client()

    def _create_client(self):
        return redis.Redis(**self.config)

    def get(self, key):
        return self.client.get(key)

    def set(self, key, value):
        self.client.set(key, value)
        logger.info(f"Value stored in Redis for key: {key}")


class VaultTokenManager:

    def __init__(self):
        self.redis_client = RedisClient()
        self.vault_addr = Config.get_vault_addr()
        self.initial_token = Config.get_vault_token()

    def get_token(self):
        token = self.redis_client.get("VAULT_TOKEN")
        if token:
            logger.info("Using VAULT_TOKEN from Redis")
            return token

        logger.info("VAULT_TOKEN not found in Redis, using from environment")
        self.redis_client.set("VAULT_TOKEN", self.initial_token)
        return self.initial_token

    def renew_token(self):
        token = self.get_token()
        url = f"{self.vault_addr}/v1/auth/token/renew-self"
        headers = {"X-Vault-Token": token}

        try:
            response = requests.post(url, headers=headers)
            response.raise_for_status()
            response_json = response.json()

            if "auth" in response_json and "client_token" in response_json["auth"]:
                new_token = response_json["auth"]["client_token"]
                if new_token == token:
                    logger.info("New token is the same as the old token")

                # Extract and log the TTL if available
                ttl = None
                if "lease_duration" in response_json["auth"]:
                    ttl = response_json["auth"]["lease_duration"]
                    logger.info(f"New token TTL: {ttl} seconds")

                return new_token, ttl
            else:
                logger.warning("No new token found in response, using current token")
                return token, None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error renewing Vault token: {e}")
            raise

    def store_token(self, token):
        self.redis_client.set("VAULT_TOKEN", token)

    def get_vault_client(self):
        return hvac.Client(url=self.vault_addr, token=self.get_token())


def main():
    token_manager = VaultTokenManager()

    try:
        new_token, ttl = token_manager.renew_token()
        token_manager.store_token(new_token)
        logger.info("Vault token renewed and stored in Redis.")
        if ttl is not None:
            logger.info(f"The new token will expire in {ttl} seconds.")
            expiration_time = datetime.datetime.now() + datetime.timedelta(seconds=ttl)
            logger.info(f"New token expiration date: {expiration_time.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"New token expires at: {expiration_time.timestamp()}")
    except Exception as e:
        logger.error(f"Failed to renew Vault token: {e}")
        raise


if __name__ == "__main__":
    main()
