# Django ToDoアプリケーション

Djangoで構築されたシンプルなToDo管理アプリケーションです。

このアプリケーションは、タスクの基本的なCRUD（作成、読み取り、更新、削除）機能を提供します。また、`django-simple-history`を利用して、各タスクへの変更履歴を記録・表示する機能を備えています。

## 主な機能

- **タスク管理 (CRUD)**
  - タスクの新規作成
  - タスクの一覧表示
  - タスクの詳細表示
  - タスクの更新
  - タスクの削除
- **タスクの属性**
  - タイトル
  - 説明
  - 期限
  - 優先度（高、中、低）
  - 完了ステータス
- **変更履歴**
  - 各タスクの作成、更新日時、更新者、変更内容を記録
  - 変更履歴をタスク詳細ページに表示

## 使用技術

- **バックエンド:** Python, Django
- **フロントエンド:** HTML, CSS, Bootstrap
- **データベース:** SQLite3 (Djangoデフォルト)
- **その他ライブラリ:**
  - `django-simple-history`: モデルの変更履歴を追跡

## ディレクトリ構成

```
todo/
├── manage.py          # Djangoプロジェクト管理用スクリプト
├── todo/              # プロジェクト設定ディレクトリ
│   ├── settings.py    # プロジェクト設定ファイル
│   └── urls.py        # プロジェクト全体のURL設定
├── tasks/             # ToDoアプリケーションディレクトリ
│   ├── models      # データモデル定義
│   ├── views       # ビュー（ロジック）定義
│   ├── forms       # フォーム定義
│   ├── urls.py        # アプリケーションのURL設定
│   ├── admin.py       # Django管理サイトの設定
│   ├── templates/     # HTMLテンプレート
│   │   └── tasks/
│   │       ├── base.html, task_list.html, task_detail.html, etc.
│   └── migrations/    # データベーススキーマの変更履歴
└── README.md          # このファイル
```

## セットアップ手順

### 1. 前提条件

- Python 3.8以上
- pip

### 2. インストール

1.  **リポジトリをクローンします。**
    ```bash
    git clone <your-repository-url>
    cd todo
    ```

2.  **Python仮想環境を作成し、有効化します。**
    ```bash
    python -m venv venv
    # Windowsの場合
    # venv\Scripts\activate
    # macOS/Linuxの場合
    source venv/bin/activate
    ```

3.  **必要なパッケージをインストールします。**
    *(注: `requirements.txt` がない場合は、以下のコマンドで主要なライブラリをインストールしてください)*
    ```bash
    pip install Django django-simple-history
    ```

4.  **データベースのマイグレーションを実行します。**
    ```bash
    python manage.py migrate
    ```

5.  **管理者ユーザーを作成します。**
    ```bash
    python manage.py createsuperuser
    ```

6.  **開発サーバーを起動します。**
    ```bash
    python manage.py runserver
    ```

7.  ブラウザで `http://127.0.0.1:8000/` にアクセスしてアプリケーションを確認します。