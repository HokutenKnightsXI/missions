FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --home-dir /app --shell /usr/sbin/nologin app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=app:app . .
RUN mkdir -p /app/instance && chown app:app /app/instance

USER app

EXPOSE 8000
VOLUME ["/app/instance"]

# Keep one process while SQLite is the database; threads handle concurrent reads.
CMD ["gunicorn", "--bind=0.0.0.0:8000", "--workers=1", "--threads=8", "--timeout=60", "--access-logfile=-", "--error-logfile=-", "missions:app"]
