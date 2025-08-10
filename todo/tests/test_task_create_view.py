# tests/test_task_create_view.py  # テストモジュールのファイルパス（Django Test Runner/pytestが検出）
import datetime  # 標準ライブラリ：日付/時間の計算に使用
from urllib.parse import urlparse, parse_qs  # リダイレクトURL検証のためにURLとクエリを分解

from django.test import TestCase, RequestFactory  # Djangoのテスト基底クラスとリクエスト生成ユーティリティ
from django.utils import timezone  # タイムゾーン対応の現在日付/時刻を扱う
from django.contrib.auth import get_user_model  # カスタムUser対応：実行時のUserモデルを取得
from django.contrib.auth.models import AnonymousUser  # 未ログイン（匿名）ユーザーを表すオブジェクト
from django.core.exceptions import FieldDoesNotExist  # モデルにフィールドが無い場合に送出される例外
from django.shortcuts import resolve_url  # URL名/相対/絶対の混在を実URLへ解決
from django.conf import settings  # 設定（LOGIN_URLなど）の参照

from todo.models.task import Task  # テスト対象のTaskモデル
from todo.views.task import TaskCreateView  # テスト対象の作成ビュー（CBV）

User = get_user_model()  # 実際に使用されるUserモデル（標準/カスタム）を取得


def user_has_username_field() -> bool:  # Userモデルにusernameフィールドが存在するか確認するヘルパ
    try:
        User._meta.get_field("username")  # メタ情報からusernameフィールドの定義を取得
        return True  # 取得できた＝存在する
    except FieldDoesNotExist:  # フィールドが無い場合
        return False  # 存在しない


def next_weekday(start_date=None):  # 入力日以降で最初に来る平日（将来日）を返すユーティリティ
    """土日を避けて、将来日の平日を返す"""  # 関数の目的を説明するDocstring
    d = (start_date or timezone.now().date()) + datetime.timedelta(days=1)  # デフォルトは今日の翌日を起点
    while d.weekday() >= 5:  # 5=土, 6=日 の間はループで翌日に進める
        d += datetime.timedelta(days=1)  # 週末をスキップ
    return d  # 平日になった日付を返す


class TaskCreateViewTests(TestCase):  # DjangoのDBトランザクション管理付きテストケース
    @classmethod
    def setUpTestData(cls):  # クラス全体で一度だけ実行される初期化フック（ユーザー等の準備）
        cls.factory = RequestFactory()  # 疑似HTTPリクエストを生成するファクトリ

        extra_alice = {}  # alice作成時に追加する引数（usernameがある場合のみ付与）
        extra_bob = {}  # bob作成時の追加引数
        if user_has_username_field():  # カスタムUserにusernameがある構成のとき
            extra_alice["username"] = "alice"  # aliceのusername
            extra_bob["username"] = "bob"  # bobのusername

        cls.alice = User.objects.create_user(  # 認証可能なユーザーaliceを作成
            email="alice@example.com", password="pass1234", **extra_alice  # メール＋パス＋必要に応じてusername
        )
        cls.bob = User.objects.create_user(  # 認証可能なユーザーbobを作成
            email="bob@example.com", password="pass1234", **extra_bob  # 同上
        )

    # --------- helpers ---------  # テスト内で使い回すヘルパメソッド群

    def _view(self):  # テスト対象ビューのas_viewを返す（success_urlを固定してURL名に依存しないようにする）
        # URL名に依存しないようここで success_url を固定
        return TaskCreateView.as_view(success_url="/tasks/")  # 成功後は /tasks/ にリダイレクトさせる

    def _request(self, method="get", user=None, data=None, path="/tasks/create/"):  # 疑似リクエストを生成するヘルパ
        req = getattr(self.factory, method)(path, data=data or {})  # methodに応じてfactory.get/postを呼ぶ
        req.user = user if user is not None else AnonymousUser()  # 認証ユーザーまたは匿名を割り当て
        return req  # 生成したリクエストを返す

    def _valid_post_data(self, **overrides):  # 正常系POSTデータ（必要に応じて上書き可）を組み立てる
        """フォーム仕様に合わせた正常値。将来日の平日・安全な priority=1 を採用"""  # 方針の説明
        data = {
            "title": "New Task",  # 必須：タイトル
            "description": "write tests for create view",  # 任意：説明
            "due_date": next_weekday().isoformat(),  # 'YYYY-MM-DD' 形式の将来平日
            "priority": 1,  # 整合性の取りやすい優先度（最小側）
            # 'completed' は省略（未チェック）→ False  # チェックボックス省略時のデフォルト動作
        }
        data.update(overrides)  # 呼び出し側からの上書きを適用
        return data  # 最終データを返す

    def _assert_redirect_or_show_form_errors(self, resp):  # 302期待の場面で200になったらformのエラー詳細を表示して即失敗させる
        """期待が302の場面で200（form_invalid）だった場合、エラー内容を出して即原因特定"""  # 補足説明
        if resp.status_code == 302:  # 期待通りリダイレクトなら何もしない
            return  # 正常終了
        # 200 のときは form 無い可能性もあるが、CreateView なら基本含まれる  # フォーム取得を試みる
        form = getattr(resp, "context_data", {}).get("form")  # コンテキストからformを取得（無い場合はNone）
        errors = getattr(form, "errors", None)  # formがあればerrorsを取得
        # errorsにas_jsonがあればJSONで、無ければそのまま出力して失敗させ原因を可視化
        self.fail(f"Expected redirect(302) but got {resp.status_code}. form.errors={getattr(errors, 'as_json', lambda: errors)()}")  # 失敗理由を詳細表示

    # --------- tests ---------  # ここから個別テスト

    def test_login_required_redirects_anonymous(self):  # 未ログインユーザーはログインページへリダイレクトされるか
        req = self._request(method="get", user=None)  # 匿名でGET
        resp = self._view()(req)  # ビューを実行
        self.assertEqual(resp.status_code, 302)  # 302リダイレクトであること

        loc = resp["Location"]  # リダイレクト先URL（例: 'http://testserver/accounts/login/?next=/tasks/create/'）
        parsed = urlparse(loc)  # URLを構造体に分解
        qs = parse_qs(parsed.query)  # クエリ文字列を辞書へ（値はリスト）
        expected_path = urlparse(resolve_url(getattr(settings, "LOGIN_URL", "/accounts/login/"))).path  # LOGIN_URLを正規化してパス部分のみ比較
        self.assertEqual(parsed.path, expected_path)  # リダイレクト先のパスがLOGIN_URLと一致
        self.assertEqual(qs.get("next"), ["/tasks/create/"])  # nextクエリが元のURLパスであること

    def test_get_authenticated_returns_200_and_context_titles(self):  # ログイン済みGETで200と各種コンテキストが設定されるか
        req = self._request(method="get", user=self.alice)  # aliceでGET
        resp = self._view()(req)  # ビューを実行
        self.assertEqual(resp.status_code, 200)  # 正常表示
        ctx = resp.context_data  # テンプレートコンテキスト
        self.assertIn("form", ctx)  # フォームがコンテキストに含まれている
        self.assertEqual(ctx.get("header_title"), "タスク登録")  # ヘッダタイトルの検証
        self.assertEqual(ctx.get("title"), "タスク登録")  # ページタイトルの検証

    def test_post_creates_task_and_sets_user(self):  # 正常POSTでTaskが作成され、userがログインユーザーに設定されるか
        before = Task.objects.count()  # 事前の件数を記録
        req = self._request(method="post", user=self.alice, data=self._valid_post_data())  # aliceで有効データをPOST
        resp = self._view()(req)  # ビュー実行（CreateViewのpost処理）

        # 失敗時は form.errors を表示して落とす  # デバッグ容易化のため
        self._assert_redirect_or_show_form_errors(resp)  # 302でなければ詳細を出してfail

        self.assertTrue(resp["Location"].endswith("/tasks/"))  # success_urlへリダイレクトされること
        self.assertEqual(Task.objects.count(), before + 1)  # 件数が1増えていること
        task = Task.objects.latest("id")  # 直近作成レコードを取得
        self.assertEqual(task.title, "New Task")  # タイトルがPOST値と一致
        self.assertEqual(task.description, "write tests for create view")  # 説明も一致
        self.assertEqual(task.priority, 1)  # 優先度も一致
        self.assertFalse(task.completed)  # completed未指定→Falseで保存されていること
        self.assertEqual(task.user, self.alice)  # userはリクエストユーザーに強制されていること

    def test_post_completed_checked_true(self):  # completedチェックONでTrueとして保存されるか
        data = self._valid_post_data(completed="on")  # チェックボックスは"on"が送られる想定
        req = self._request(method="post", user=self.alice, data=data)  # POST実行
        resp = self._view()(req)  # ビュー処理

        self._assert_redirect_or_show_form_errors(resp)  # 成功（302）を期待

        task = Task.objects.latest("id")  # 直近作成Task
        self.assertTrue(task.completed)  # completedがTrueで保存されている

    def test_post_cannot_spoof_user_field(self):  # POSTでuserフィールドを偽装しても無視されること（サーバ側でrequest.userを使用）
        before = Task.objects.count()  # 事前件数
        # user を偽装して混ぜてもフォームに無いので無視される想定  # セキュリティ確認
        data = self._valid_post_data(user=self.bob.pk)  # 悪意あるクライアントを想定
        req = self._request(method="post", user=self.alice, data=data)  # 実際のログインはalice
        resp = self._view()(req)  # ビュー処理

        self._assert_redirect_or_show_form_errors(resp)  # 成功（302）を期待

        self.assertEqual(Task.objects.count(), before + 1)  # 1件作成
        task = Task.objects.latest("id")  # 直近作成Task
        self.assertEqual(task.user, self.alice)  # DB上のuserはalice（偽装は反映されない）

    def test_post_invalid_shows_errors(self):  # 必須欠落など無効POSTではフォーム再表示（200）となりエラーが含まれる
        data = self._valid_post_data()  # 正常データを用意
        data["title"] = ""  # 必須のtitleを空にしてバリデーションエラーを誘発
        req = self._request(method="post", user=self.alice, data=data)  # POST実行
        resp = self._view()(req)  # ビュー処理

        # 失敗時はフォーム再表示  # CreateViewの標準動作
        self.assertEqual(resp.status_code, 200)  # 200（form_invalidの再描画）
        self.assertIn("form", resp.context_data)  # コンテキストにformがある
        self.assertTrue(resp.context_data["form"].errors)  # formにエラーが含まれている
