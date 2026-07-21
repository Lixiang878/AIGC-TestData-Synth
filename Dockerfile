# syntax=docker/dockerfile:1
FROM python:3.11-slim

LABEL org.opencontainers.image.source="https://github.com/Lixiang878/aigc-testdata-synth"
LABEL org.opencontainers.image.description="AIGC test-data factory: spec-driven synthesis, dedup, diversity audit, quality filter"

WORKDIR /app

COPY . /app

# Offline core install: numpy only. The LLM synthesis backend is OPTIONAL and
# lazy-imported; a template/mock backend runs with no network.
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e . \
    && pip install --no-cache-dir pytest

CMD ["pytest", "-q"]

# Run the offline factory with the mock provider:
#   docker build -t aigc-testdata-synth .
#   docker run --rm aigc-testdata-synth python -m aigc_synth.cli synth --provider mock
