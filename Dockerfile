FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# les dependances d'abord pour profiter du cache Docker
COPY requirements-docker.txt .
RUN pip install -r requirements-docker.txt

COPY src/app.py src/features.py src/schema.py ./

# l'API ne tourne pas en root
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

# pas de curl dans l'image slim, on fait le healthcheck en python
HEALTHCHECK --interval=15s --timeout=3s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
