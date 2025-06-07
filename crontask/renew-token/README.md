# Vault Token Renewal Cron Task

This directory contains a cron task for renewing HashiCorp Vault tokens and storing them in Redis.

## Overview

The `renew_vault_token.py` script is designed to be run as a cron job to periodically renew a Vault token and store it in Redis for use by other applications. This ensures that the token doesn't expire and applications can continue to access Vault.

## Configuration

The script requires the following environment variables:

- `VAULT_ADDR` or (`VAULT_HOST` and `VAULT_PORT`): The address of the Vault server
- `VAULT_TOKEN`: The initial Vault token to use
- `REDIS_HOST`: The Redis server hostname
- `REDIS_PORT`: The Redis server port
- `REDIS_DB`: The Redis database number
- `REDIS_PASSWORD`: The Redis password

## Running the Script

```bash
python renew_vault_token.py
```

## Running Tests

The project includes unit tests written with pytest. To run the tests:

1. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the tests:
   ```bash
   pytest test_renew_vault_token.py -v
   ```

## Test Coverage

The tests cover:

- Configuration retrieval from environment variables
- Redis client operations
- Vault token management (retrieval, renewal, storage)
- Error handling

## Docker

A Dockerfile is provided to build a container for running the script:

```bash
docker build -t vault-token-renewer .
docker run --env-file .env vault-token-renewer
```

## Kubernetes

A sample Kubernetes CronJob configuration is provided in `cronjob.yaml`. Customize it for your environment before applying.