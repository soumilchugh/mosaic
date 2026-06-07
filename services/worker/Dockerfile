FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY packages ./packages
COPY services ./services
RUN pip install --no-cache-dir .

CMD ["python", "-m", "worker.main"]
