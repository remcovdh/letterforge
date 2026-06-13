FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src/ src/
COPY docker/ docker/

RUN pip install --no-cache-dir ".[all]"

ENV LETTERFORGE_SANDBOX_DIR=/app/docker/sandbox

ENTRYPOINT ["letterforge"]
CMD ["--help"]
