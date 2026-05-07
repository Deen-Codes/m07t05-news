# syntax=docker/dockerfile:1.6

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# mysqlclient needs these to build
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        build-essential \
        default-libmysqlclient-dev \
        pkg-config \
        netcat-openbsd \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# install requirements first so the layer caches
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip \
 && pip install -r requirements.txt \
 && pip install gunicorn==22.0.0

COPY . /app

# entrypoint waits for db then runs migrate + seed_groups
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
