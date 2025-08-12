import logging  # ログ出力（info/warning/error）用の標準ライブラリ
from django.conf import settings  # 設定値（LOGIN_URL や独自設定）にアクセスするため
from django.contrib import messages  # 画面にフラッシュメッセージを表示するため
from django.contrib.auth.mixins import LoginRequiredMixin  # 未ログイン時にログイン画面へリダイレクトするミックスイン
from django.urls import reverse_lazy  # URLの遅延解決（import時ではなく実行時に解決）
from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView, TemplateView  # 汎用CBV群
from django.contrib.messages.views import SuccessMessageMixin  # 成功時にメッセージを自動表示するミックスイン
from ..models.task import Task  # 同アプリ内のTaskモデル
from ..forms.task import TaskForm  # 同アプリ内のTask用フォーム
from django.db.models import Q  # OR/ANDなど複合条件検索に使うQオブジェクト
from django.utils import timezone  # タイムゾーン対応の現在日付/時刻取得

logger = logging.getLogger(__name__)  # このモジュール用のロガーを取得（設定ファイルでハンドラを紐付け）

SORTABLE_FIELDS = {  # （未使用の可能性あり）汎用ソート対象フィールドのマップ
    "title": "title",  # クエリ 'title' → ORMフィールド 'title'
    "due_date": "due_date",  # 同上
    "priority": "priority",  # 同上
    "completed": "completed",  # 同上
    # "user": "user__username",  # 全体一覧（他人のタスクも含む）のときに有効化する例
}


class TaskListView(LoginRequiredMixin, ListView):  # ログイン必須のタスク一覧ビュー
    model = Task  # 対象モデル
    template_name = "todo/task/list.html"  # 使用テンプレート
    context_object_name = "obj"  # テンプレ側で参照しやすいように別名を付与
    paginate_by = 10  # 1ページあたりの件数
    ordering = ["due_date"]  # ソート指定がない場合のデフォルト順（期限日昇順）

    SORTABLE_FIELDS = {  # このビューで許可するソートキー → 実フィールド名
        "due_date": "due_date",  # 期限日
        "priority": "priority",  # 優先度
        "created_at": "created_at",  # 作成日時
        "title": "title",  # タイトル
    }

    def get_queryset(self):  # 一覧に出すレコード集合を返す
        qs = (  # ベースのQuerySetを作成
            super()
            .get_queryset()  # まずは model.objects.all()
            .filter(user=self.request.user)  # ★ 自分のタスクのみ（IDOR/情報漏えい対策）
            .select_related("user")  # user 外部キーをJOINで先読み（N+1回避）
        )

        # --- フィルタ ---  # 検索語・状態による絞り込み
        q = (self.request.GET.get("q") or "").strip()  # フリーテキスト検索（空なら空文字）
        status = (self.request.GET.get("status") or "all").lower()  # 状態フィルタ（open/done/all）

        if q:  # 検索語がある場合のみ
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))  # タイトル/説明の部分一致

        if status == "open":   # 未完のみ
            qs = qs.filter(completed=False)
        elif status == "done": # 完了のみ
            qs = qs.filter(completed=True)

        # --- ソート ---  # 許可したキーのみ受け付ける（不正入力対策）
        sort = self.request.GET.get("sort") or "due_date"  # 指定がなければ期限日
        direction = (self.request.GET.get("dir") or "asc").lower()  # 昇順/降順
        if sort in self.SORTABLE_FIELDS:  # 許可されたキーなら
            field = self.SORTABLE_FIELDS[sort]  # 実フィールド名に変換
            if direction == "desc":  # 降順指定なら
                field = f"-{field}"  # ORMの降順表記に変換
            qs = qs.order_by(field)  # ソート適用

        return qs  # 最終的なQuerySetを返す

    def get_context_data(self, **kwargs):  # テンプレートへ渡す追加コンテキスト
        ctx = super().get_context_data(**kwargs)  # 既定の値（object_list, page_obj等）を取得
        # UI反映用に現在値と件数  # タブ/バッジ表示のための集計
        user_qs = Task.objects.filter(user=self.request.user)  # 自分の全タスク
        q = (self.request.GET.get("q") or "").strip()  # 現在の検索語
        status = (self.request.GET.get("status") or "all").lower()  # 現在の状態フィルタ

        ctx["q"] = q  # 再描画時の検索欄保持
        ctx["status"] = status  # 状態タブの選択状態
        ctx["sort"] = self.request.GET.get("sort") or "due_date"  # 現在のソートキー
        ctx["dir"] = (self.request.GET.get("dir") or "asc").lower()  # 現在のソート方向
        ctx["today"] = timezone.localdate()  # 今日の日付（期限ハイライト等に使用）

        ctx["count_all"] = user_qs.count()  # 全件数
        ctx["count_open"] = user_qs.filter(completed=False).count()  # 未完件数
        ctx["count_done"] = user_qs.filter(completed=True).count()  # 完了件数
        return ctx  # 追加コンテキストを返す


class TaskCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):  # ログイン必須＋成功メッセージ付きの作成ビュー
    model = Task  # 対象モデル
    form_class = TaskForm  # 使用するフォーム（ModelForm）
    template_name = "todo/task/create.html"  # 使用テンプレート
    success_url = reverse_lazy("todo:task_list")  # 登録成功後の遷移先
    success_message = "タスクを登録しました。"  # SuccessMessageMixinで表示する文言

    def get_context_data(self, **kwargs):  # 画面の見出しなど追加
        ctx = super().get_context_data(**kwargs)  # 既定のコンテキストを取得
        ctx["header_title"] = "タスク登録"  # ページ上部の見出し用
        ctx["title"] = "タスク登録"  # ページタイトル用
        return ctx  # 返却

    def form_valid(self, form):  # バリデーションOK時の保存ロジック
        form.instance.user = self.request.user  # ★ セキュリティ：ownerをサーバ側で強制
        resp = super().form_valid(form)  # 通常の保存処理
        logger.info(  # 登録ログ（監査用）
            "Task created id=%s title=%s by=%s",
            self.object.pk,
            self.object.title,
            getattr(self.request.user, "username", getattr(self.request.user, "email", "unknown")),  # username→emailの順に取得
        )
        return resp  # リダイレクトレスポンスを返却

    def form_invalid(self, form):  # バリデーションNG時
        logger.error("Task create form invalid errors=%s", dict(form.errors))  # エラー内容をログに出力
        messages.error(self.request, "タスクの登録に失敗しました。")  # 画面にエラーメッセージを表示
        return super().form_invalid(form)  # フォーム再表示


class TaskUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):  # ログイン必須＋成功メッセージ付きの更新ビュー
    model = Task  # 対象モデル
    form_class = TaskForm  # 使用フォーム
    template_name = "todo/task/update.html"  # 使用テンプレート
    context_object_name = "obj"  # テンプレ上の参照名
    success_url = reverse_lazy("todo:task_list")  # 更新成功後の遷移先
    success_message = "タスクを更新しました。"  # 成功メッセージ

    # ★ IDOR対策：自分のタスクだけを取得  # URLのpkを直接いじられても他人のデータは触れない
    def get_queryset(self):
        return Task.objects.filter(user=self.request.user)  # 所有者でフィルタ

    def get_context_data(self, **kwargs):  # 画面用の追加文言
        ctx = super().get_context_data(**kwargs)  # 既定コンテキスト
        ctx["header_title"] = "タスク更新"  # 見出し
        ctx["title"] = "タスク更新"  # ページタイトル
        return ctx  # 返却

    def form_valid(self, form):  # バリデーションOK時
        # 念のため上書き（owner固定）  # クライアント側偽装の無効化
        form.instance.user = self.request.user  # ★ サーバ側で所有者を固定
        resp = super().form_valid(form)  # 保存
        logger.info(  # 更新ログ
            "Task updated id=%s title=%s by=%s",
            self.object.pk,
            self.object.title,
            getattr(self.request.user, "username", getattr(self.request.user, "email", "unknown")),  # 操作者識別
        )
        return resp  # リダイレクトレスポンス


class TaskDetailView(LoginRequiredMixin, DetailView):  # ログイン必須の詳細ビュー
    model = Task  # 対象モデル
    template_name = "todo/task/detail.html"  # 使用テンプレート
    context_object_name = "obj"  # テンプレ参照名

    # ★ IDOR対策  # 詳細も所有者でフィルタリング
    def get_queryset(self):
        return Task.objects.filter(user=self.request.user)  # 自分のタスクのみ

    def get_context_data(self, **kwargs):  # 詳細画面に履歴情報を付加
        ctx = super().get_context_data(**kwargs)  # 既定のコンテキスト
        ctx["header_title"] = "タスク詳細"  # 見出し
        ctx["title"] = "タスク詳細"  # ページタイトル

        # 履歴は重くなりがちなのでユーザーをまとめて取得し、件数も適度に制限  # simple_historyの最適化
        history_qs = (
            self.object.history.select_related("history_user")  # 履歴の操作者をJOINで先読み
            .order_by("-history_date")[:50]  # 新しい順に最大50件
        )

        history_changes = []  # 差分の見やすい構造に整形してテンプレに渡す
        for record in history_qs:  # 各履歴を走査
            prev = record.prev_record  # 直前の履歴（なければNone）
            if prev:
                diff = record.diff_against(prev)  # 前後差分を計算
                changes = {c.field: {"old": c.old, "new": c.new} for c in diff.changes}  # 変更フィールドごとに旧値/新値を抽出
            else:
                changes = None  # 最初の履歴など、比較対象なし
            history_changes.append(  # テンプレで扱いやすい辞書にまとめる
                {
                    "history_date": record.history_date,  # 変更日時
                    "history_user": record.history_user,  # 操作者（Noneのこともある）
                    "history_type": record.history_type,  # 変更種別（+追加, ~更新, -削除 など）
                    "changes": changes,  # 差分詳細
                }
            )

        ctx["history_changes"] = history_changes  # テンプレ用コンテキストに差分一覧を格納
        return ctx  # 返却


class TaskDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):  # ログイン必須＋成功メッセージ付きの削除ビュー
    model = Task  # 対象モデル
    template_name = "todo/task/confirm_delete.html"  # 確認ダイアログ用テンプレート
    context_object_name = "obj"  # テンプレ参照名
    success_url = reverse_lazy("todo:task_list")  # 削除後の遷移先
    success_message = "タスクを削除しました。"  # 成功メッセージ

    # ★ IDOR対策  # 他人のタスクは取得できないようにする
    def get_queryset(self):
        return Task.objects.filter(user=self.request.user)  # 所有者でフィルタ

    def delete(self, request, *args, **kwargs):  # DELETE処理のフック（ログ＋メッセージ）
        obj = self.get_object()  # 削除対象を先に取得（ログに使う）
        logger.warning("Task deleted id=%s title=%s by=%s", obj.id, obj.title, request.user)  # 重要操作なのでwarningで記録
        messages.success(request, self.success_message)  # 画面に成功メッセージ
        return super().delete(request, *args, **kwargs)  # 通常の削除処理を実行


class TaskKanbanView(LoginRequiredMixin, TemplateView):  # ログイン必須のカンバン表示
    template_name = "todo/task/kanban.html"  # カンバン用テンプレート

    def get_context_data(self, **kwargs):  # カンバン列と各列のタスクを用意
        ctx = super().get_context_data(**kwargs)  # 既定コンテキスト
        # 設定からカラム定義を取得（なければモデルのchoices順で代用）
        columns = getattr(settings, "KANBAN_COLUMNS", None)  # 例: [("todo","ToDo"), ("doing","進行中"), ...]
        if not columns:  # 未設定なら
            # モデルchoices → [("todo","ToDo"), ...]  # Task.statusのchoicesを利用
            columns = list(Task._meta.get_field("status").choices)

        # 各カラムに絞り込んだQuerySetを付与  # 並び順は「優先度高い→期限早い→新しい」の優先
        qs_base = Task.objects.filter(user=self.request.user).order_by("-priority", "due_date", "-id")  # 自分のタスクのみ
        ctx["columns"] = [  # テンプレで繰り返しやすい形式（key, 表示名, QuerySet）
            (key, label, qs_base.filter(status=key))  # 列ごとにstatusでフィルタ
            for key, label in columns
        ]
        return ctx  # 返却


class TaskCalendarView(LoginRequiredMixin, TemplateView):  # ログイン必須のカレンダー表示（一覧をカレンダーUIで出す想定）
    template_name = "todo/task/calendar.html"  # カレンダー用テンプレート
    # 追加のコンテキストが必要なら get_context_data を実装  # 現状はテンプレ側でAPI/表示を完結させる想定


# 関数エイリアス（URL confで使うならそのままでもOK）  # URLパターンから直接呼び出せるようにするショートカット
task_list = TaskListView.as_view()  # 一覧
task_create = TaskCreateView.as_view()  # 作成
task_update = TaskUpdateView.as_view()  # 更新
task_detail = TaskDetailView.as_view()  # 詳細
task_delete = TaskDeleteView.as_view()  # 削除
task_kanban = TaskKanbanView.as_view()  # カンバン
task_calendar = TaskCalendarView.as_view()  # カレンダー
