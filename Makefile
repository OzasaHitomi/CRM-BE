# eval $(poetry env activate) でシェルに入る　（deactivate で抜ける）
# or
# poetry run を使う（アクティベート不要）

.PHONY: lint lint-fix format format-fix fix check-all test-up test-down e2e-up e2e-down test cov migrate-create migrate-up migrate-down

lint:
	ruff check .

lint-fix:
	ruff check . --fix

format:
	ruff format --check .

format-fix:
	ruff format .

# linter・formatterの自動修正をまとめて実行
fix: lint-fix format-fix

# すべて実行（チェック＋整形）
check-all:
	ruff format --check .
	ruff check .

# local 開発開発起動
build:
	docker compose build

up:
	docker compose up -d

stop:
	docker compose stop

down:
	docker compose down

# マイグレーションファイルの新規作成（autogenerate）
# 例: make migrate-create msg="add customers table"
migrate-create:
	@if [ -z "$(msg)" ]; then \
		echo "Usage: make migrate-create msg=\"revision message\""; \
		exit 1; \
	fi
	docker compose exec api alembic revision --autogenerate -m "$(msg)"

# マイグレーションを適用してDBを最新状態にする
migrate-up:
	docker compose exec api alembic upgrade head

# マイグレーションを1つ戻す（失敗時のロールバック用）
migrate-down:
	docker compose exec api alembic downgrade -1

# 単体・結合テスト（pytest）用DBの起動・停止
# e2e-upとはprojectを分離しているため、同時に起動していてもDBが混ざらない
test-up:
	docker compose -f docker-compose.test.yml --env-file .env.test.unit -p crm_be-unit up -d

test-down:
	docker compose -f docker-compose.test.yml --env-file .env.test.unit -p crm_be-unit down

# E2E用（FEと繋いだ結合テスト）のDB＋API起動・停止
e2e-up:
	docker compose -f docker-compose.test.yml --env-file .env.test.e2e -p crm_be-e2e --profile e2e up -d

e2e-down:
	docker compose -f docker-compose.test.yml --env-file .env.test.e2e -p crm_be-e2e --profile e2e down

# テスト実行（カバレッジなし・高速）
test:
	poetry run pytest tests/ -v --no-cov

# カバレッジ付きテスト実行（HTMLレポートは htmlcov/ に出力）
cov:
	poetry run pytest tests/ -v
