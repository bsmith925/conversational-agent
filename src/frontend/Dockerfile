FROM python:3.11-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ \
&& rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements-frontend.txt .
RUN pip install --upgrade --no-compile pip \
&& pip install --no-compile -r requirements-frontend.txt


FROM python:3.11-slim

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
&& rm -rf /var/lib/apt/lists/*

RUN groupadd -g 1000 appuser && useradd --system --create-home -u 1000 -g 1000 -s /usr/sbin/nologin appuser

COPY --from=builder --chown=appuser:appuser /opt/venv /opt/venv


COPY --chown=appuser:appuser src/frontend/ /app/

RUN mkdir -p /app/.files /app/.chainlit && chown -R appuser:appuser /app/.files /app/.chainlit

USER appuser
EXPOSE 8000

CMD ["chainlit","run","app.py","--host","0.0.0.0","--port","8000","--headless"]
