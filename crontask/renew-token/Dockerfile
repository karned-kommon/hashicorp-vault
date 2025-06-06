FROM python:3.11-slim

WORKDIR /app

COPY renew_vault_token.py .

RUN pip install requests redis hvac

CMD ["python", "renew_vault_token.py"]
