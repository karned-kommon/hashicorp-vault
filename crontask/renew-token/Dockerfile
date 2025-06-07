FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
COPY renew_vault_token.py .

RUN pip install -r requirements.txt

CMD ["python", "renew_vault_token.py"]
