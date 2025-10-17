FROM python:3.10-slim AS builder
WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" PIP_NO_CACHE_DIR=1

COPY requirements-backend.txt .
RUN pip install --upgrade pip \
    && pip install --no-deps -r requirements-backend.txt \
    && pip check


FROM python:3.10-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

RUN groupadd -g 1000 appuser && useradd --system --create-home -u 1000 -g 1000 -s /usr/sbin/nologin appuser

RUN mkdir -p /home/appuser/.dspy_cache && chown -R 1000:1000 /home/appuser

COPY --chown=1000:1000 src/backend/app /app/app

USER 1000:1000
EXPOSE 8000

CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
