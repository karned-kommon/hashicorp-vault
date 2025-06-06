import os
import requests
import redis
import logging
import hvac

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

VAULT_ADDR = os.environ["VAULT_ADDR"]
VAULT_TOKEN = os.environ["VAULT_TOKEN"]
REDIS_HOST = os.environ["REDIS_HOST"]
REDIS_PORT = int(os.environ["REDIS_PORT"])
REDIS_DB = int(os.environ["REDIS_DB"])
REDIS_PASSWORD = os.environ["REDIS_PASSWORD"]

def get_redis_client():
    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        password=REDIS_PASSWORD,
        decode_responses=True
    )

def get_vault_token():
    r = get_redis_client()
    token = r.get("vault_token")
    if token:
        logging.info("Using vault_token from Redis")
        return token

    logging.info("vault_token not found in Redis, using from environment")
    r.set("vault_token", VAULT_TOKEN)
    return VAULT_TOKEN

def get_vault_client():
    return hvac.Client(url=VAULT_ADDR, token=get_vault_token())

def renew_token():
    token = get_vault_token()
    url = f"{VAULT_ADDR}/v1/auth/token/renew-self"
    headers = {"X-Vault-Token": token}
    response = requests.post(url, headers=headers)
    response.raise_for_status()
    new_token = response.json()["auth"]["client_token"]
    return new_token

def store_token_in_redis(token):
    r = get_redis_client()
    r.set("vault_token", token)
    logging.info("New token stored in Redis")

if __name__ == "__main__":
    token = renew_token()
    store_token_in_redis(token)
    logging.info("Vault token renewed and stored in Redis.")
