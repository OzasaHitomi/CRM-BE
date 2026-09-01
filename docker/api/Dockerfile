FROM python:3.14

WORKDIR /crm_be

RUN apt-get update && \
  apt-get install -y --no-install-recommends tzdata && \
  rm -rf /var/lib/apt/lists/*

# Poetryのインストール
RUN pip install poetry

# Poetryの仮想環境は使わずグローバルに（Docker内ではこれがシンプル）
RUN poetry config virtualenvs.create false

COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --only main

COPY docker/api/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# アプリケーションのソースコードをコピー(Cloud deploy時にDockerfileで完結するため)
# WORKDIR(/crm_be) = crm_be パッケージのルートとなるよう src/crm_be/ の中身だけをコピーする
# これにより uvicorn main:app や alembic upgrade head が WORKDIR から直接解決できる
COPY src/crm_be/ .

ENTRYPOINT ["/entrypoint.sh"]

