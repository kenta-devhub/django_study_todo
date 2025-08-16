# Django Todo Application

これはDjangoとDjango REST Frameworkで構築された、かんばんボードスタイルの高機能なTodo管理アプリケーションです。
タスクのリアルタイム更新通知機能や、変更履歴の完全な追跡機能を備えています。

## 概要

ユーザーはタスクを作成し、そのステータスを「ToDo」「進行中」「保留」「完了」の4つのカラムで管理できます。タスクの変更履歴は自動的に記録されます。

`django-simple-history`による変更履歴の自動記録機能により、誰がいつタスクを更新したかを追跡できます。
さらに、Server-Sent Events (SSE) を利用したリアルタイム通知APIにより、タスクの変更が他のユーザーの画面にも即座に反映されるようなインタラクティブな体験を実現できます。

## 主な機能

-   **ユーザー認証**: サインアップ、ログイン、ログアウト機能
-   **タスク管理 (CRUD)**: タスクの作成、閲覧、更新、削除
-   **かんばんボード表示**: ステータス (`todo`, `doing`, `blocked`, `done`) ごとのタスク管理
-   **タスク履歴**: `django-simple-history`による変更履歴の完全な自動記録
-   **REST API**: 外部アプリケーションと連携するための豊富なAPIエンドポイント
-   **リアルタイム更新**: Server-Sent Events (SSE) によるタスク変更のリアルタイム通知

+## ディレクトリ構造

```
.
├── tasks/            # Todoアプリケーションのコアロジック
│   ├── migrations/
│   ├── templates/
│   ├── admin.py
│   ├── models.py     # TaskモデルとHistoricalTaskモデル
│   ├── views.py      # ビュー（かんばんボード、API、SSE）
│   ├── urls.py
│   └── serializers.py  # DRF用のシリアライザー
├── config/           # プロジェクト全体の設定
│   ├── settings.py   # 環境変数を読み込む設定
│   └── urls.py       # プロジェクト全体のURLルーティング
├── secrets/
│   └── .env.dev      # 開発用の環境変数ファイル
├── manage.py         # Django管理コマンド
└── requirements.txt  # 依存パッケージリスト
```

## 技術スタックと選定理由

-   **バックエンド**: Python, Django
-   **データベース**: MySQL
-   **API**: Django REST Framework
-   **環境変数管理**: django-environ
-   **環境変数管理**: `django-environ`
    -   理由: `settings.py`からデータベース接続情報などの機密情報を分離し、安全に管理するため。
-   **履歴管理**: django-simple-history
-   **履歴管理**: `django-simple-history`
    -   理由: モデルへの変更履歴を自動的にデータベースに保存し、監査やデバッグを容易にするため。

## セットアップ手順

### 1. 前提条件

-   Python 3.x
-   MySQL Server
-   Git

### 2. リポジトリのクローン

```bash
git clone <your-repository-url>
cd todo
```

### 3. 依存関係のインストール

このプロジェクトには`requirements.txt`が含まれていない可能性があります。もしない場合は、以下のコマンドで現在の環境のライブラリを元に作成してください。

```bash
pip freeze > requirements.txt
```

次に、仮想環境を作成し、依存ライブラリをインストールします。

```bash
python -m venv venv
source venv/bin/activate  # for Linux/macOS
# venv\Scripts\activate    # for Windows

pip install -r requirements.txt
```

### 4. 環境変数の設定

プロジェクトルートに`secrets`ディレクトリを作成し、その中に`.env.dev`ファイルを作成します。

```bash
mkdir secrets
touch secrets/.env.dev
```

`.env.dev`ファイルに以下の内容を記述し、ご自身の環境に合わせて値を設定してください。

```dotenv
# .env.dev

# Django
SECRET_KEY='your-very-long-and-secure-secret-key'
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (MySQL)
MYSQL_NAME=todo_db
MYSQL_USER=todo_user
MYSQL_PASSWORD=your_db_password
MYSQL_HOST=localhost
MYSQL_PORT=3306
```

`SECRET_KEY`は以下のコマンドで安全なキーを生成できます。

```python
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

### 5. データベースのセットアップ

MySQLに接続し、`.env.dev`で設定したデータベースを作成します。

```sql
CREATE DATABASE todo_db CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
```

### 6. マイグレーションの実行

Djangoのマイグレーションを実行して、データベースにテーブルを作成します。

```bash
python manage.py migrate
```

### 7. 管理者ユーザーの作成

管理サイトにログインするためのスーパーユーザーを作成します。

```bash
python manage.py createsuperuser
```

### 8. 開発サーバーの起動

以下のコマンドで開発サーバーを起動します。

```bash
python manage.py runserver
```

ブラウザで `http://127.0.0.1:8000/` にアクセスすると、アプリケーションが表示されます。
管理サイトは `http://127.0.0.1:8000/admin/` です。

## APIエンドポイント

認証（セッション認証）が必要です。

-   `GET /api/tasks/`: タスク一覧を取得
-   `POST /api/tasks/`: 新しいタスクを作成
-   `GET /api/tasks/<id>/`: 特定のタスクの詳細を取得
-   `PUT/PATCH /api/tasks/<id>/`: 特定のタスクを更新
-   `DELETE /api/tasks/<id>/`: 特定のタスクを削除
-   `GET /api/tasks/events/`: タスクの変更イベントをストリーミング (Server-Sent Events)