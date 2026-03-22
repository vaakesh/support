FROM python:3.14-slim
WORKDIR /backend

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_NO_DEV=0

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    zsh \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN git clone --depth=1 https://github.com/romkatv/powerlevel10k.git /root/powerlevel10k \
    && printf '%s\n' \
    'export TERM=xterm-256color' \
    'source /root/powerlevel10k/powerlevel10k.zsh-theme' \
    '[[ -f ~/.p10k.zsh ]] && source ~/.p10k.zsh' \
    > /root/.zshrc

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates

ADD https://astral.sh/uv/0.10.8/install.sh /uv-installer.sh
RUN env UV_UNMANAGED_INSTALL="/usr/local/bin" sh /uv-installer.sh \
    && rm /uv-installer.sh


COPY pyproject.toml uv.lock alembic.ini .python-version entrypoint.sh /backend
RUN uv sync --locked
COPY alembic/ /backend/alembic
COPY tests/ /backend/tests
COPY app/ /backend/app
COPY certs/ /backend/certs
RUN chmod +x /backend/entrypoint.sh


EXPOSE 8000

ENTRYPOINT ["/backend/entrypoint.sh"]