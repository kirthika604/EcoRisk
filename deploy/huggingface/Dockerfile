# Hugging Face Space for EcoRisk AI.
# The Space holds only this file and README.md. The app (code, trained models, data) is pulled from
# the public GitHub repo at build time, so the Space needs no Git LFS and no tokens.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HOST=0.0.0.0 PORT=7860
ARG REPO=kirthika604/EcoRisk
ARG BRANCH=main
WORKDIR /app

# Docker re-downloads this archive whenever its content changes, so a "Factory rebuild" of the
# Space always picks up the latest commit on the branch.
ADD https://codeload.github.com/${REPO}/tar.gz/refs/heads/${BRANCH} /tmp/app.tar.gz
RUN tar -xzf /tmp/app.tar.gz -C /app --strip-components=1 && rm /tmp/app.tar.gz \
 && pip install --no-cache-dir -r requirements.txt \
 && useradd -m -u 1000 app && chown -R app /app
USER app

EXPOSE 7860
CMD ["python", "ml/ef_server.py"]
