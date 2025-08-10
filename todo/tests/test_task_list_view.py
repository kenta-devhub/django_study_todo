# tests/test_task_list_view.py  # テストモジュールのファイルパス（pytest/Django Test Runner で検出される）
import datetime  # 標準ライブラリ：日付計算用
from django.test import TestCase, RequestFactory  # Djangoのテスト基底クラスとリクエスト生成ユーティリティ
from django.utils import timezone  # タイムゾーン対応の現在時刻取得などに使用
from django.conf import settings  # 設定値（LOGIN_URL など）参照のため
from django.contrib.auth import get_user_model  # カスタムUser対応のため、直接Userをimportせずに取得
from django.contrib.auth.models import AnonymousUser  # 未ログイン状態を表すユーザーオブジェクト
from django.http import HttpResponseRedirect  # リダイレクトの型チェック等に使える（未使用でも文脈として妥当）
from django.core.exceptions import FieldDoesNotExist  # モデルにフィールドが無い場合の例外
from urllib.parse import urlparse, parse_qs  # リダイレクトURL解析のため
from django.shortcuts import resolve_url  # URL名/相対/絶対を正規のURLへ解決

# ← 実プロジェクトのパスに合わせて修正  # テストと実装のパス整合性に注意
from todo.models import Task  # テスト対象：Taskモデル
from todo.views.task import TaskListView  # 一覧ビュー（CBV）をテスト対象として読み込み

User = get_user_model()  # 実行時のUserモデル（標準/カスタム）を取得


def user_has_username_field() -> bool:  # カスタムUserにusernameフィールドが存在するかを真偽で返すユーティリティ
    try:
        User._meta.get_field("username")  # メタ情報からusernameフィールドの定義を取得
        return True  # 取得できればTrue
    except FieldDoesNotExist:
        return False  # 無ければFalse


class TaskListViewTests(TestCase):  # Djangoのトランザクション管理付きテストケース
    @classmethod
    def setUpTestData(cls):  # 全テスト共通で最初に一度だけ実行される初期データ作成フック
        cls.factory = RequestFactory()  # 疑似HTTPリクエストを生成するためのファクトリ

        # email が必須のカスタムユーザーを想定  # usernameの有無で生成引数を切替
        extra_alice = {}  # alice用の追加キーワード引数（username等）
        extra_bob = {}  # bob用の追加キーワード引数
        if user_has_username_field():  # Userモデルにusernameがある場合のみ設定
            extra_alice["username"] = "alice"  # aliceのusernameを設定
            extra_bob["username"] = "bob"  # bobのusernameを設定

        cls.alice = User.objects.create_user(  # 認証可能なユーザーaliceを作成
            email="alice@example.com",  # メールアドレス
            password="pass1234",  # テスト用の平易なパスワード
            **extra_alice,  # 必要に応じてusernameを渡す
        )
        cls.bob = User.objects.create_user(  # 認証可能なユーザーbobを作成
            email="bob@example.com",
            password="pass1234",
            **extra_bob,
        )

        base = timezone.now().date() - datetime.timedelta(days=30)  # 基準日：今日から30日前
        # alice のタスク 12件  # 並び順やページネーション検証に十分な件数を用意
        for i in range(12):  # 0〜11
            Task.objects.create(  # タスク1件を作成
                title=f"Alice Task {i}",  # 識別しやすいタイトル
                user=cls.alice,  # 所有者：alice
                due_date=base + datetime.timedelta(days=i),  # 期日を日単位で前後に散らす（昇順検証用）
                priority=i,  # 優先度をiで設定（ソート検証用）
                completed=(i % 2 == 0),  # 偶数番は完了True、奇数番はFalse（ブールソート検証用）
            )
        # bob のタスク 3件（フィルタで除外されることの確認用）  # ログインユーザーで絞り込めるかを検証
        for i in range(3):  # 0〜2
            Task.objects.create(
                title=f"Bob Task {i}",  # bob用タイトル
                user=cls.bob,  # 所有者：bob
                due_date=base + datetime.timedelta(days=100 + i),  # aliceと離れた期日（混在影響を避ける）
                priority=100 + i,  # 大きめの優先度（混同防止）
                completed=False,  # 未完了
            )

    def _get_response(self, user=None, params=None, path="/tasks/"):  # ヘルパー：任意ユーザー/クエリで一覧ビューを呼び出す
        request = self.factory.get(path, data=params or {})  # GETリクエストを生成（クエリ文字列をparamsで指定）
        request.user = user if user is not None else AnonymousUser()  # ログインユーザーか匿名かを割当
        return TaskListView.as_view()(request)  # CBVをASGI/Wsgiのように呼び出してレスポンス取得

    def test_login_required_redirects_anonymous(self):  # 未ログイン時にログインページへリダイレクトされるか
        resp = self._get_response(user=None)  # 匿名ユーザーでアクセス
        self.assertEqual(resp.status_code, 302)  # リダイレクト（302）であること

        loc = resp["Location"]  # 例: 'http://testserver/accounts/login/?next=/tasks/'  # リダイレクト先URLを取得
        parsed = urlparse(loc)  # URLを分解（スキーム/ホスト/パス/クエリ等）
        qs = parse_qs(parsed.query)  # クエリ文字列を辞書へ（値はリスト）

        # 期待されるログインURLの「パス」部分を比較（settings.LOGIN_URL が名前/URLどちらでもOK）
        expected_path = urlparse(resolve_url(getattr(settings, "LOGIN_URL", "/accounts/login/"))).path  # LOGIN_URLを正規URL化してパス抽出
        self.assertEqual(parsed.path, expected_path)  # 実際のリダイレクト先パスと一致すること

        # next パラメータが /tasks/ であること（parse_qs はデコード済みを返す）
        self.assertEqual(qs.get("next"), ["/tasks/"])  # 認証後に元のページへ戻るためのnextが正しいこと

    def test_filters_by_request_user(self):  # ログインユーザーのレコードだけが表示されるか
        resp = self._get_response(user=self.alice)  # aliceでアクセス
        ctx = resp.context_data  # テンプレートコンテキストを取得
        for task in ctx["object_list"]:  # 一覧に含まれる各Taskを検証
            self.assertEqual(task.user, self.alice)  # すべてaliceのタスクであること

    def test_default_ordering_due_date_asc(self):  # デフォルトの並び順がdue_date昇順であるか
        resp = self._get_response(user=self.alice)  # 一覧取得
        due_dates = [t.due_date for t in resp.context_data["object_list"]]  # 現在の順序の期日リスト
        self.assertEqual(due_dates, sorted(due_dates))  # 自然昇順と一致すること

    def test_invalid_sort_falls_back_to_default(self):  # 無効なsortパラメータ時にデフォルト並びへフォールバックするか
        resp_default = self._get_response(user=self.alice)  # デフォルト
        ids_default = [t.id for t in resp_default.context_data["object_list"]]  # デフォルト順のID

        resp_invalid = self._get_response(user=self.alice, params={"sort": "___invalid___"})  # 不正なsort指定
        ids_invalid = [t.id for t in resp_invalid.context_data["object_list"]]  # 実際のID順
        self.assertEqual(ids_default, ids_invalid)  # デフォルトと同一順序であること

    def test_sort_by_priority_desc(self):  # priorityの降順ソートが機能するか
        resp = self._get_response(user=self.alice, params={"sort": "priority", "dir": "desc"})  # sort=priority, dir=desc
        priorities = [t.priority for t in resp.context_data["object_list"]]  # 表示順のpriorityを抽出
        self.assertEqual(priorities, sorted(priorities, reverse=True))  # 降順と一致

    def test_sort_by_priority_asc(self):  # priorityの昇順ソートが機能するか
        resp = self._get_response(user=self.alice, params={"sort": "priority", "dir": "asc"})  # sort=priority, dir=asc
        priorities = [t.priority for t in resp.context_data["object_list"]]  # 表示順のpriority
        self.assertEqual(priorities, sorted(priorities))  # 昇順と一致

    def test_sort_by_completed_desc_true_first(self):  # completedの降順（Trueを先頭）で並ぶか
        resp = self._get_response(user=self.alice, params={"sort": "completed", "dir": "desc"})  # sort=completed, dir=desc
        flags = [1 if t.completed else 0 for t in resp.context_data["object_list"]]  # True=1, False=0に変換
        self.assertTrue(all(flags[i] >= flags[i + 1] for i in range(len(flags) - 1)))  # 非増加（1が先→0が後）であること

    def test_sort_by_user_field_if_supported(self):  # Userモデルの表示名（例：username）でのソートが可能な場合の検証
        # カスタムユーザーで username が無い構成ならスキップ
        if not user_has_username_field():  # usernameフィールド非対応なら
            self.skipTest("User model に 'username' フィールドが無いためスキップ（SORTABLE_FIELDS を user__email 等に変更してください）")  # 条件付きスキップ

        resp = self._get_response(user=self.alice, params={"sort": "user", "dir": "asc"})  # userで昇順ソートを要求
        self.assertEqual(resp.status_code, 200)  # 正常応答
        for t in resp.context_data["object_list"]:  # ただし一覧はログインユーザーfilterが先に掛かる想定
            self.assertEqual(t.user, self.alice)  # そのため、結果はaliceのタスクに限定されていること

    def test_pagination_page2(self):  # ページネーション挙動の検証（2ページ目）
        resp = self._get_response(user=self.alice, params={"page": 2})  # page=2でアクセス
        ctx = resp.context_data  # コンテキスト取得
        self.assertTrue(ctx["is_paginated"])  # ページネーションが有効であること
        self.assertEqual(ctx["page_obj"].number, 2)  # 現在ページが2であること
        self.assertEqual(len(ctx["object_list"]), 2)  # 2ページ目の要素数が2件（※ paginate_by=10, 全12件を前提）

    def test_context_titles_and_alias_name(self):  # テンプレートに渡すカスタム文言/エイリアスの検証
        resp = self._get_response(user=self.alice)  # 一覧取得
        ctx = resp.context_data  # コンテキスト取得
        self.assertEqual(ctx.get("header_title"), "タスク一覧")  # 見出しタイトル
        self.assertEqual(ctx.get("title"), "タスク")  # タイトル
        self.assertIn("obj", ctx)  # 'obj' エイリアスが存在すること（テンプレで使い回し用）
        self.assertEqual(list(ctx["obj"]), list(ctx["object_list"]))  # 'obj' が object_list の別名であること
