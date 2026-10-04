# EcoRisk AI: one small container serving the page and the trained models.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HOST=0.0.0.0 PORT=7860
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# app code, trained models, results, the page and the original EcoRisk pages
COPY ml/ ml/
COPY ecorisk-ai/ ecorisk-ai/
COPY dashboard/ dashboard/
COPY demo/ demo/
COPY awareness/ awareness/
# per-site daily weather (needed to replay any site and date), ~11 MB
COPY datasourceSIH/sites/ datasourceSIH/sites/

# run as a non-root user (required by some hosts, good practice everywhere)
RUN useradd -m -u 1000 app && chown -R app /app
USER app

EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import os,urllib.request;urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/healthz')"
CMD ["python", "ml/ef_server.py"]
