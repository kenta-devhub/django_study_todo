from rest_framework import viewsets, permissions  # DRFのViewSetとパーミッション基底クラス
from rest_framework.decorators import action  # 追加のカスタムアクション（@action）を定義するため
from rest_framework.response import Response  # APIレスポンスを返すためのクラス
from rest_framework.exceptions import PermissionDenied  # 権限違反時の例外（本コードでは未使用だが文脈的に妥当）
from django.utils import timezone  # タイムゾーン対応の日時ユーティリティ
from .models.task import Task  # 同アプリのTaskモデル
from .serializers import TaskSerializer  # Task用シリアライザ
from rest_framework.views import APIView  # 汎用APIビュー（ViewSetを使わない単機能APIで使用）

class IsOwner(permissions.BasePermission):  # オブジェクトレベルの所有者チェック用パーミッション
    def has_object_permission(self, request, view, obj):  # 各オブジェクトに対して許可/拒否を判定
        return obj.user_id == request.user.id  # タスクの所有者IDとログインユーザーIDが一致したときのみ許可

class TaskViewSet(viewsets.ModelViewSet):  # CRUD一式を提供するModelViewSet
    serializer_class = TaskSerializer  # 既定のシリアライザ
    permission_classes = [permissions.IsAuthenticated, IsOwner]  # ログイン必須＋オブジェクト所有者のみ操作可

    def get_queryset(self):  # 一覧/取得で使うクエリセットを定義
        qs = Task.objects.filter(user=self.request.user)  # ★ 自分のタスクに限定（IDOR対策）
        status = self.request.query_params.get("status")  # クエリパラメータ ?status=...
        if status:  # statusが指定されていれば
            qs = qs.filter(status=status)  # 状態で絞り込み
        q = (self.request.query_params.get("q") or "").strip()  # フリーテキスト検索語（空なら空文字）
        if q:  # 検索語がある場合のみ
            qs = qs.filter(title__icontains=q) | qs.filter(description__icontains=q)  # タイトル/説明をORで部分一致（QuerySetの和）
            # ※ Qオブジェクトで qs.filter(Q(title__icontains=q) | Q(description__icontains=q)) と同等だが、挙動は変えない
        return qs  # 最終的なクエリセットを返す

    def perform_create(self, serializer):  # POST（create）時の保存フック
        serializer.save(user=self.request.user)  # ★ サーバ側で所有者を強制セット（偽装防止）

    @action(detail=True, methods=["patch"], url_path="status")  # /tasks/{pk}/status/ でPATCHするカスタムアクション
    def set_status(self, request, pk=None):  # ステータスだけを更新する専用エンドポイント
        task = self.get_object()  # pkに対応するTaskを取得（同時にIsOwnerのオブジェクト権限チェックが実行される）
        new_status = request.data.get("status")  # リクエストボディから新しいstatusを取得

        # ★ モデルの choices から許容値を動的取得（将来の追加にも追従）  # 定数直書きを避けて堅牢化
        valid_statuses = {val for val, _ in Task._meta.get_field("status").choices}  # ('todo','ToDo') 形式から値だけを集合化
        if new_status not in valid_statuses:  # 許容外の値なら
            return Response({"detail": "invalid status"}, status=400)  # 400 Bad Requestを返す

        task.status = new_status  # 新しい状態を反映
        # 状態と completed の整合（運用に合わせて調整可）  # doneのときはcompleted=True、それ以外はFalseに寄せる
        if new_status == Task.STATUS_DONE:
            task.completed = True  # 完了状態に同期
        else:
            task.completed = False  # 未完了へ同期
        task.save(update_fields=["status", "completed", "updated_at"])  # 変更されたフィールドのみDB更新
        return Response(TaskSerializer(task).data)  # 更新後の最新タスクを返す（200 OK）

class TaskEventsView(APIView):  # カレンダー用イベントを返す単機能API
    permission_classes = [permissions.IsAuthenticated]  # ログイン必須

    def get(self, request):  # GET /... でイベント一覧を返却
        tasks = Task.objects.filter(user=request.user, due_date__isnull=False)  # 期限日のある自分のタスクのみ
        items = []  # イベント配列
        today = timezone.localdate()  # 今日（ローカル日付）
        for t in tasks:  # 各タスクをイベント形式へ変換
            items.append({
                "id": t.id,  # イベントID（タスクID）
                "title": f"{t.title} ({t.get_priority_display()})",  # タイトル＋優先度ラベル
                "start": t.due_date.isoformat(),  # 開始日（終日イベント想定）
                "allDay": True,  # 終日扱い
                "color": "#dc3545" if (not t.completed and t.due_date < today) else None,  # 期限超過＆未完は赤系ハイライト
                "url": request.build_absolute_uri(f"/todo/detail/{t.id}/"),  # 詳細ページへの絶対URL
            })
        return Response(items)  # JSON配列で返却（200 OK）
