FROM python:3.14-slim
WORKDIR /backend

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_NO_DEV=1

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates

ADD https://astral.sh/uv/0.10.8/install.sh /uv-installer.sh
RUN env UV_UNMANAGED_INSTALL="/usr/local/bin" sh /uv-installer.sh \
    && rm /uv-installer.sh


COPY pyproject.toml uv.lock alembic.ini .python-version entrypoint.sh /backend
RUN uv sync --locked
COPY alembic/ /backend/alembic
COPY app/ /backend/app
RUN chmod +x /backend/entrypoint.sh


EXPOSE 8000

ENTRYPOINT ["/backend/entrypoint.sh"]