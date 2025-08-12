from django.db import models  # Djangoのモデル定義に必要な基本モジュール
from django.conf import settings  # AUTH_USER_MODELなどの設定値を参照するため
from simple_history.models import HistoricalRecords  # 変更履歴を自動記録するためのモデルミックスイン

class Task(models.Model):  # タスクを表すモデル（1件=1タスク）
    PRIORITY_LOW = 1  # 優先度：低
    PRIORITY_MEDIUM = 2  # 優先度：中
    PRIORITY_HIGH = 3  # 優先度：高
    PRIORITY_CHOICES = [  # フォーム/管理画面で使用する選択肢
        (PRIORITY_LOW, "低"),  # 1 → 「低」
        (PRIORITY_MEDIUM, "中"),  # 2 → 「中」
        (PRIORITY_HIGH, "高"),  # 3 → 「高」
    ]

    STATUS_TODO = "todo"  # 状態：未着手
    STATUS_DOING = "doing"  # 状態：進行中
    STATUS_DONE = "done"  # 状態：完了（UI上のカンバン用）
    STATUS_BLOCKED = "blocked"  # 状態：保留/ブロック
    STATUS_CHOICES = [  # Kanban等UIで使用する状態選択肢
        (STATUS_TODO, "ToDo"),  # "todo" → 「ToDo」
        (STATUS_DOING, "進行中"),  # "doing" → 「進行中」
        (STATUS_DONE, "完了"),  # "done" → 「完了」
        (STATUS_BLOCKED, "保留"),  # "blocked" → 「保留」
    ]

    user = models.ForeignKey(  # タスクの担当者（ユーザー）への外部キー
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,  # ユーザー削除時に紐づくタスクも削除
        related_name="tasks", verbose_name="担当者", db_index=True  # 逆参照名・表示名・検索最適化
    )
    title = models.CharField("タイトル", max_length=200)  # タスクの件名（必須）
    description = models.TextField("説明", blank=True)  # 詳細説明（任意）
    due_date = models.DateField("期限", null=True, blank=True, db_index=True)  # 期限日（空可・検索用に索引付与）
    priority = models.IntegerField(  # 優先度（1〜3の選択）
        "優先度", choices=PRIORITY_CHOICES,
        default=PRIORITY_MEDIUM, db_index=True  # 既定は「中」、並び替え/検索用に索引
    )
    completed = models.BooleanField("完了", default=False, db_index=True)  # 完了フラグ（True=完了）

    # ★ Kanban 用の状態（completed とは別にUI制御で使う）  # 完了フラグと独立して状態管理したい場合に利用
    status = models.CharField(  # カンバン列などの表示状態
        "状態", max_length=10, choices=STATUS_CHOICES,
        default=STATUS_TODO, db_index=True  # 既定はToDo、検索最適化
    )

    created_at = models.DateTimeField("作成日時", auto_now_add=True)  # レコード作成時に自動記録
    updated_at = models.DateTimeField("更新日時", auto_now=True)  # 更新のたびに自動更新

    history = HistoricalRecords()  # simple_history による変更履歴テーブル（<app>_historicaltask）を自動生成

    class Meta:  # メタ情報（デフォルト並びや索引・制約など）
        ordering = ["completed", "priority", "due_date", "-id"]  # 既定の並び順（未完→低優先→期限早い→新しい）
        verbose_name = "タスク"  # 単数表示名（管理サイトなど）
        verbose_name_plural = "タスク"  # 複数表示名
        indexes = [  # DBインデックス（検索・並び替えの高速化）
            models.Index(fields=["user", "status", "due_date"]),  # 担当者×状態×期限に複合索引
            models.Index(fields=["completed", "priority"]),  # 完了フラグ×優先度の複合索引
        ]
        constraints = [  # DBレベルの整合性制約（アプリ外からの書き込みにも強い）
            models.CheckConstraint(
                check=models.Q(priority__in=[1, 2, 3]),  # priorityは1/2/3のみ許可（choicesに対応）
                name="task_priority_valid",  # 制約名（マイグレーションに出力される）
            )
        ]

    def __str__(self):  # 管理画面やシェルでの可読表示
        return f"{self.title}（{'完了' if self.completed else '未完了'}）"  # 例：「資料作成（未完了）」のように表示
