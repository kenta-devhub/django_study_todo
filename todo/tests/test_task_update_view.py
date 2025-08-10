# tests/test_task_update_view.py  # テストモジュールのパス（Django Test Runner/pytestが検出）
import datetime  # 標準ライブラリ：日付計算に使用
from urllib.parse import urlparse, parse_qs  # リダイレクトURL検証のためURL/クエリを分解

from django.test import TestCase, RequestFactory  # Djangoのテスト基底クラスとリクエスト生成ユーティリティ
from django.utils import timezone  # タイムゾーン対応の現在日付/時刻を扱う
from django.contrib.auth import get_user_model  # カスタムUser対応：実行時のUserモデルを取得
from django.contrib.auth.models import AnonymousUser  # 未ログイン（匿名）ユーザーを表すオブジェクト
from django.core.exceptions import FieldDoesNotExist  # モデルにフィールドが無い場合の例外
from django.shortcuts import resolve_url  # URL名/相対/絶対を実URLへ解決
from django.conf import settings  # 設定（LOGIN_URLなど）の参照

# あなたの実際の構成に合わせてインポート  # 実装の配置に合わせて調整すること
from todo.models.task import Task  # テスト対象のTaskモデル
from todo.views.task import TaskUpdateView  # 更新ビュー（CBV）。例: todo/views/task.py に定義

User = get_user_model()  # 実際に使用されるUserモデル（標準/カスタム）を取得


def user_has_username_field() -> bool:  # Userモデルにusernameフィールドが存在するかを返すヘルパ
    try:
        User._meta.get_field("username")  # メタ情報からusernameフィールド定義を取得
        return True  # 取得できれば存在
    except FieldDoesNotExist:  # 無い場合に送出
        return False  # 非存在


def next_weekday(start_date=None):  # 入力日以降で最初の平日（将来日）を返す
    """土日を避けた将来日の平日を返す（独自バリデーションに強くするため）"""  # 関数の説明
    d = (start_date or timezone.now().date()) + datetime.timedelta(days=1)  # デフォルト起点は今日の翌日
    while d.weekday() >= 5:  # 5=土, 6=日 はスキップ
        d += datetime.timedelta(days=1)  # 次の日へ
    return d  # 平日になった日付を返却


class TaskUpdateViewTests(TestCase):  # DBを隔離するDjangoテストケース
    @classmethod
    def setUpTestData(cls):  # クラス全体で一度だけ実行される初期データ作成
        cls.factory = RequestFactory()  # 疑似HTTPリクエスト生成器

        # email必須のカスタムユーザーにも対応  # username有無で作成パラメータを切替
        extra_alice = {}  # alice作成時の追加引数（usernameなど）
        extra_bob = {}  # bob作成時の追加引数
        if user_has_username_field():  # Userにusernameがある場合のみ設定
            extra_alice["username"] = "alice"  # aliceのusername
            extra_bob["username"] = "bob"  # bobのusername

        cls.alice = User.objects.create_user(  # 認証可能ユーザーaliceを作成
            email="alice@example.com", password="pass1234", **extra_alice  # メール/パス/必要ならusername
        )
        cls.bob = User.objects.create_user(  # 認証可能ユーザーbobを作成
            email="bob@example.com", password="pass1234", **extra_bob  # 同上
        )

        # 既存タスクを2件作成（所有者違い）  # 更新対象とアクセス制御の検証用
        cls.alice_task = Task.objects.create(  # alice所有のタスク
            user=cls.alice,
            title="Alice Task",
            description="desc A",
            due_date=next_weekday(),  # 将来の平日
            priority=1,
            completed=False,
        )
        cls.bob_task = Task.objects.create(  # bob所有のタスク
            user=cls.bob,
            title="Bob Task",
            description="desc B",
            due_date=next_weekday(),  # 将来の平日
            priority=2,
            completed=True,
        )

    # ------------- helpers -------------  # テスト内で使い回すユーティリティ

    def _view(self):  # テスト対象のビュー（as_view）を返す
        # URL名に依存しないため、ここで success_url を固定
        return TaskUpdateView.as_view(success_url="/tasks/")  # 成功後は /tasks/ にリダイレクト

    def _path(self, pk):  # pkからテスト用のURLパスを生成
        return f"/tasks/{pk}/update/"  # 例：/tasks/1/update/

    def _request(self, method="get", user=None, data=None, *, pk):  # 疑似リクエスト生成
        req = getattr(self.factory, method)(self._path(pk), data=data or {})  # GET/POSTを動的に選択
        req.user = user if user is not None else AnonymousUser()  # 認証ユーザーまたは匿名を割当
        return req  # リクエスト返却

    def _valid_post_data(self, **overrides):  # 正常系のPOSTデータ（必要に応じて上書き）
        """フォーム仕様（title/description/due_date/priority/completed[任意]）に合わせた正常値"""  # 方針説明
        data = {
            "title": "Updated Title",  # 更新後タイトル
            "description": "updated description",  # 更新後説明
            "due_date": next_weekday().isoformat(),  # 'YYYY-MM-DD' 形式の将来平日
            "priority": 3,  # 更新後の優先度
            # completed は任意。未指定なら False になる  # チェックボックス未送信時の既定動作
        }
        data.update(overrides)  # 呼び出し側の上書きを反映
        return data  # データ返却

    def _assert_redirect_or_show_form_errors(self, resp):  # 302期待の場面で200だったらformエラーを表示してfail
        """期待が302のとき200だった場合、form.errors を表示して即特定"""  # 説明
        if resp.status_code == 302:  # 期待通りリダイレクトなら
            return  # 何もしない
        form = getattr(resp, "context_data", {}).get("form")  # コンテキストからformを取得（無ければNone）
        errors = getattr(form, "errors", None)  # フォームエラー
        # errors は dict or ErrorDict。as_json が無ければそのまま文字列化
        err_txt = errors.as_json() if hasattr(errors, "as_json") else str(errors)  # 表示用に整形
        self.fail(f"Expected redirect(302) but got {resp.status_code}. form.errors={err_txt}")  # 詳細付でテスト失敗

    # ------------- tests -------------  # ここから個別テスト

    def test_login_required_redirects_anonymous(self):  # 未ログインはログイン画面へリダイレクト＋next付与
        """未ログインはログイン画面へリダイレクトされ、next に元URLが付与される"""  # テスト意図
        req = self._request(method="get", user=None, pk=self.alice_task.pk)  # 匿名でGET
        resp = self._view()(req, pk=self.alice_task.pk)  # ビュー実行（URL引数pkを渡す）
        self.assertEqual(resp.status_code, 302)  # リダイレクトであること

        loc = resp["Location"]  # リダイレクト先（例: /accounts/login/?next=/tasks/<pk>/update/）
        parsed = urlparse(loc)  # URLを構造体に分解
        qs = parse_qs(parsed.query)  # クエリを辞書に変換（値はリスト）
        expected_path = urlparse(resolve_url(getattr(settings, "LOGIN_URL", "/accounts/login/"))).path  # LOGIN_URLを正規化してパスのみ抽出
        self.assertEqual(parsed.path, expected_path)  # ログインURLのパスが一致
        self.assertEqual(qs.get("next"), [self._path(self.alice_task.pk)])  # nextが元のURLであること

    def test_get_authenticated_returns_200_and_context(self):  # 認証済みGETでフォーム表示とコンテキスト確認
        """ログイン済みのGETでフォーム表示・コンテキストが適切に設定される"""  # テスト意図
        req = self._request(method="get", user=self.alice, pk=self.alice_task.pk)  # aliceでGET
        resp = self._view()(req, pk=self.alice_task.pk)  # ビュー実行
        self.assertEqual(resp.status_code, 200)  # 正常表示
        ctx = resp.context_data  # テンプレートコンテキスト
        self.assertIn("form", ctx)  # formが含まれている
        self.assertEqual(ctx.get("header_title"), "タスク更新")  # ヘッダタイトル検証
        self.assertEqual(ctx.get("title"), "タスク更新")  # ページタイトル検証
        # context_object_name='obj'  # View側で設定されている想定
        self.assertIn("obj", ctx)  # 'obj' が存在
        self.assertEqual(ctx["obj"].pk, self.alice_task.pk)  # 表示対象がalice_taskであること

    def test_post_updates_fields_and_sets_user(self):  # POSTで更新＆user再設定、success_urlへリダイレクト
        """
        正常POSTでフィールドが更新され、success_url にリダイレクト。
        user は request.user に（再）設定される。
        """  # 複数行Docstringでテストの狙いを明記
        req = self._request(  # 疑似POSTを作成
            method="post",
            user=self.alice,
            data=self._valid_post_data(completed="on"),  # True に更新（チェックボックスは"on"）
            pk=self.alice_task.pk,
        )
        resp = self._view()(req, pk=self.alice_task.pk)  # ビュー実行

        self._assert_redirect_or_show_form_errors(resp)  # 302でなければformエラーを表示してfail
        self.assertTrue(resp["Location"].endswith("/tasks/"))  # success_urlへリダイレクト

        self.alice_task.refresh_from_db()  # DBから再読込（更新内容を反映）
        self.assertEqual(self.alice_task.title, "Updated Title")  # タイトル更新確認
        self.assertEqual(self.alice_task.description, "updated description")  # 説明更新確認
        self.assertEqual(self.alice_task.priority, 3)  # 優先度更新確認
        self.assertTrue(self.alice_task.completed)  # completed=Trueに更新されたこと
        self.assertEqual(self.alice_task.user, self.alice)  # userがrequest.user（alice）であること

    def test_post_unchecked_completed_becomes_false(self):  # completed未送信→Falseで保存されるか
        """completed を送らない場合は False で保存される"""  # テスト意図
        # まず True にしておく  # 状態遷移確認のため事前にTrueにセット
        self.alice_task.completed = True
        self.alice_task.save(update_fields=["completed"])  # completedのみ更新

        req = self._request(  # completed未指定のPOST
            method="post",
            user=self.alice,
            data=self._valid_post_data(),  # completed 未送信 → False
            pk=self.alice_task.pk,
        )
        resp = self._view()(req, pk=self.alice_task.pk)  # ビュー実行

        self._assert_redirect_or_show_form_errors(resp)  # 302であることを期待
        self.alice_task.refresh_from_db()  # 再読込
        self.assertFalse(self.alice_task.completed)  # Falseに反転して保存されていること

    def test_post_cannot_spoof_user_field(self):  # userフィールドの偽装は無視されるか
        """
        POST に 'user' を混ぜてもフォームには user フィールドが無いため無視され、
        保存される user は request.user（alice）になる
        """  # セキュリティ観点の検証
        req = self._request(  # 悪意あるクライアントを想定してuserを混入
            method="post",
            user=self.alice,
            data=self._valid_post_data(user=self.bob.pk),  # フォーム外フィールドは無視される前提
            pk=self.alice_task.pk,
        )
        resp = self._view()(req, pk=self.alice_task.pk)  # ビュー実行

        self._assert_redirect_or_show_form_errors(resp)  # 302であることを確認

        self.alice_task.refresh_from_db()  # 再読込
        self.assertEqual(self.alice_task.user, self.alice)  # DB上のuserはaliceのまま

    def test_post_invalid_shows_errors(self):  # 無効POST時はフォーム再表示（200）とエラーを含むか
        """必須欠落（title 空）でバリデーションエラー → 200でフォーム再表示"""  # テスト意図
        bad = self._valid_post_data()  # 正常値を基に
        bad["title"] = ""  # 必須のtitleを空にしてエラーを誘発
        req = self._request(method="post", user=self.alice, data=bad, pk=self.alice_task.pk)  # POST
        resp = self._view()(req, pk=self.alice_task.pk)  # ビュー実行

        self.assertEqual(resp.status_code, 200)  # form_invalidにより再描画
        self.assertIn("form", resp.context_data)  # コンテキストにformが含まれる
        self.assertTrue(resp.context_data["form"].errors)  # formにエラーが載っている
