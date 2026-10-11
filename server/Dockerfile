# Agent Golf: the website, its upload API and the counter, in one image (plan 002, 5.1).
# Build from the repo root, with server/ as the context:
#   docker build -t agent-golf server/
FROM python:3.12-slim

# No bytecode files (the code is read-only to the app's user), logs straight to
# `docker logs`, and no pip cache or pip warnings in the image.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore

WORKDIR /app

# The pinned requirements first, so a code change does not reinstall them.
COPY requirements.txt /app/server/requirements.txt
RUN pip install -r /app/server/requirements.txt

# The whole server/ folder (less .dockerignore) at /app/server, so `server.app` and
# `server.counter` import as in the repo. Owned by root: the app cannot change its code.
COPY . /app/server

# The app runs as golf (uid 10001), which may write only /data.
RUN groupadd --gid 10001 golf \
 && useradd --uid 10001 --gid golf --no-create-home --home-dir /nonexistent \
    --shell /usr/sbin/nologin golf \
 && mkdir /data \
 && chown golf:golf /data

# The database and uploaded logs live in a volume (plan 002, 5.2), so they outlive the
# container and are never in the image. A new named volume takes /data's owner (golf);
# a bind mount must be writable by uid 10001.
ENV AGENT_GOLF_DATA_DIR=/data
VOLUME /data
USER golf

EXPOSE 8000
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]
