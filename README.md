# CRM-BE

Novel CRM の Backend API サーバー。
顧客（Customer）・商談（Deal）・活動ログ（ActivityLog）を管理する CRM。
sales・manager・admin の 3 ロールを持つ。

## 技術スタック

| 用途 | 採用技術 |
|---|---|
| フレームワーク | FastAPI |
| ORM | SQLAlchemy v2 |
| マイグレーション | Alembic |
| DB | MySQL 8.0 |
| 実行環境 | Docker / docker compose |
| パッケージ管理 | Poetry |
| Python | 3.14 |

## 前提条件

- Docker / Docker Compose がインストールされていること
- Poetry がインストールされていること（ローカルで lint/format/pytest を実行する場合）

## セットアップ

```bash
# 1. 環境変数ファイルを作成
#    SECRET_KEY は各自生成すること（例: python -c "import secrets; print(secrets.token_urlsafe(64))"）
cp .env.example .env
cp .env.test.unit.example .env.test.unit
cp .env.test.e2e.example .env.test.e2e

# 2. コンテナ起動（マイグレーション・初期データ投入は自動実行）
make build
make up

# 3. ローカルで lint/format/pytest を実行する場合は Poetry 環境をセットアップ
#    （dependency-groups の dev グループも含めて一括インストールされる）
poetry install
```

コンテナ起動時（`docker/api/entrypoint.sh`）に以下が自動で実行されます：
- `alembic upgrade head`（マイグレーション）
- `python -m crm_be.scripts.seed`（`SEED_PROFILE` に応じた初期データ投入）

## ロールと認可

| ロール | 権限 |
|---|---|
| `sales` | 自分が担当する customer / deal のみ閲覧・編集可 |
| `manager` | 全ての customer / deal を閲覧・編集可 |
| `admin` | ユーザー管理のみ（CRM 業務データは扱わない） |

認証は JWT を httponly Cookie（`access_token`）に格納する方式。リクエストごとに `verify_access_token` / `get_current_user`（`api/common/dependencies/authentication.py`）で検証し、ロール制御は `user_checker(roles)`（`api/common/dependencies/authorization.py`）で行う。

## API

ベース URL: `http://localhost:8000/api/v1`

### Auth

| メソッド | パス | 説明 |
|---|---|---|
| POST | `/auth/login` | ログイン（Cookie に access_token を発行） |
| POST | `/auth/logout` | ログアウト（Cookie 削除） |
| GET | `/auth/me` | ログインユーザー情報取得 |

### Customers

| メソッド | パス | 説明 |
|---|---|---|
| GET | `/customers` | 顧客一覧（sales は自分の担当分のみ） |
| GET | `/customers/{customer_id}` | 顧客詳細（紐づく deal・活動ログを含む） |
| POST | `/customers` | 顧客作成 |
| PUT | `/customers/{customer_id}` | 顧客更新（sales / manager） |
| POST | `/customers/{customer_id}/deals` | 商談作成（sales / manager） |
| PUT | `/customers/{customer_id}/assigned-user` | 担当者アサイン（sales / manager） |
| DELETE | `/customers/{customer_id}/assigned-user` | 担当者解除（sales / manager） |

### Deals

| メソッド | パス | 説明 |
|---|---|---|
| PUT | `/deals/{deal_id}` | 商談更新（sales / manager） |
| PUT | `/deals/{deal_id}/status` | 商談ステータス変更（sales / manager） |
| POST | `/deals/{deal_id}/activity-logs` | 活動ログ作成（sales / manager） |
| PUT | `/deals/{deal_id}/activity-logs/{activity_log_id}` | 活動ログ更新（sales / manager） |

### Admin

| メソッド | パス | 説明 |
|---|---|---|
| GET | `/admin/users` | ユーザー一覧（admin のみ） |
| POST | `/admin/users` | ユーザー作成（admin のみ） |
| PUT | `/admin/users/status/{user_id}` | ユーザー有効化・無効化（admin のみ） |

### Healthcheck

| メソッド | パス | 説明 |
|---|---|---|
| GET | `/healthcheck` | ヘルスチェック |

## よく使うコマンド

```bash
make build         # イメージビルド
make up            # コンテナ起動（ローカル開発用）
make stop          # コンテナ停止
make down          # コンテナ削除

make lint          # Linter チェック（ruff check）
make lint-fix      # Linter による自動修正（ruff check --fix）
make format        # Formatter チェック（ruff format --check）
make format-fix    # Formatter による自動整形（ruff format）
make fix           # lint-fix + format-fix をまとめて実行
make check-all     # format --check + lint（CI 相当のチェック）

make migrate-create msg="add xxx table"  # マイグレーションファイル自動生成
make migrate-up     # マイグレーション適用
make migrate-down   # マイグレーションを1つロールバック

make test-up        # 単体・結合テスト用 DB 起動
make test-down      # 単体・結合テスト用 DB 停止
make e2e-up          # E2E（FE 結合）用 DB + API 起動
make e2e-down        # E2E（FE 結合）用 DB + API 停止

make test           # pytest 実行（カバレッジなし・高速）
make cov            # pytest 実行（カバレッジ付き、htmlcov/ にレポート出力）
```

## テスト

単体・結合テストは `docker-compose.test.yml` + `.env.test.unit` で起動した DB（ポート 3307）に対して実行する。

```bash
make test-up
make test    # または make cov（カバレッジ付き）
make test-down
```

`make test` / `make cov` はローカルの Poetry 環境から直接 pytest を実行するショートカット（既に起動済みのテスト用 DB に対して実行する想定）。

E2E テストは FE と繋いで結合させるための構成で、`.env.test.e2e`（DB ポート 3308、API ポート 8001）を使い、`--profile e2e` で API コンテナも含めて起動する。`test-up` / `e2e-up` は project 名（`-p crm_be-unit` / `-p crm_be-e2e`）を分けているため、同時に起動しても DB が混ざらない。

## シードデータ

`SEED_PROFILE`（`.env` 系ファイルで指定）に応じて `python -m crm_be.scripts.seed` が投入するデータが変わる。

| SEED_PROFILE | 用途 | 投入されるデータ |
|---|---|---|
| `none` | 単体・結合テスト | admin ユーザーのみ（テストは各テストが個別にデータを用意） |
| `development` | ローカル開発 | admin + sales/manager ユーザー + サンプル顧客・商談・活動ログ |
| `e2e` | E2E テスト | admin + sales/manager ユーザーのみ（顧客・商談・活動ログは各テストが API/UI 経由で用意） |

- `seed_admin`: `ADMIN_EMAIL` / `ADMIN_PASSWORD` から管理者ユーザーを作成（既に存在する場合は skip）
- `seed_sales_manager_users`: `sales@example.com` / `manager@example.com`（パスワードは共通で `password`）を作成
- `seed_development`: 上記に加えてサンプル顧客・商談・活動ログを作成

いずれも既にデータが存在する場合は何もせず skip する（再実行しても安全）。

## マイグレーション

Alembic を使用。マイグレーションファイルは `src/crm_be/migrations/versions/` に格納。

```bash
make migrate-create msg="add xxx table"  # モデル変更後、自動生成
make migrate-up                          # 最新まで適用
make migrate-down                        # 1つ戻す（失敗時のロールバック用）
```

## ディレクトリ構成

```
src/crm_be/
├── api/            # ルーター（v1/、admin/）、認証・認可・DB セッションの依存関数
├── core/config/     # 設定（環境変数）・DB 接続設定
├── exceptions/      # 業務例外（Business/NotFound/Forbidden/Unauthorized）
├── handlers/        # 例外ハンドラ（業務例外・バリデーション・想定外エラー）
├── logic/           # ドメインロジック（商談ステータス遷移、日付計算、JWT/パスワード）
├── models/          # SQLAlchemy モデル
├── repositories/    # エンティティ単位の DB アクセス
├── schemas/v1/       # リクエスト/レスポンスの Pydantic スキーマ
├── scripts/seed/     # 初期データ投入スクリプト
├── store/           # 定数・Enum（ロール・商談ステータス/プラン等）
└── migrations/       # Alembic マイグレーション
```

## 環境変数

`.env.example` / `.env.test.unit.example` / `.env.test.e2e.example` を参照。

| ファイル | 用途 |
|---|---|
| `.env` | ローカル開発（`make up`） |
| `.env.test.unit` | 単体・結合テスト用 DB（`make test-up`） |
| `.env.test.e2e` | E2E テスト用 DB + API（`make e2e-up`） |

主要な変数：

| 変数名 | 説明 |
|---|---|
| `ENVIRONMENT` | デプロイ先の種別（`local` / `production`、デフォルト `local`）。`production` では起動時のシード処理（admin ユーザー作成含む）を実行しない |
| `SEED_PROFILE` | 投入する初期データの種類（`none` / `development` / `e2e`） |
| `SECRET_KEY` | JWT 署名キー |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | 初期管理者アカウント |
| `FRONTEND_BASE_URL` | フロントエンドのオリジン（CORS 設定） |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | アクセストークンの有効期限（分） |
| `COOKIE_SECURE` | access_token Cookie の Secure 属性（ローカルは `false`） |
| `MYSQL_*` | DB 接続情報 |
