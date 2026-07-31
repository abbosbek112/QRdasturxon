# --- 1-bosqich: kutubxonalarni yig'ish ---
FROM python:3.13-slim AS builder

WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt


# --- 2-bosqich: ishga tushirish ---
FROM python:3.13-slim

# Konteyner root ostida ishlamasin — buzib kirilsa zarar cheklangan bo'ladi
RUN useradd --create-home --uid 10001 app

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
COPY --chown=app:app alembic.ini ./
COPY --chown=app:app alembic ./alembic
COPY --chown=app:app app ./app
COPY --chown=app:app scripts ./scripts

# Rasmlar shu yerga yoziladi — compose'da doimiy volume ulanadi
RUN mkdir -p /app/media && chown app:app /app/media
USER app

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2 --proxy-headers --forwarded-allow-ips='*'"]
