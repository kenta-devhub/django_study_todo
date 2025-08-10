from django.db import models
from django.utils import timezone
from django.conf import settings
from simple_history.models import HistoricalRecords


class Task(models.Model):
    PRIORITY_CHOICES = [
        (1, 'Low'),
        (2, 'Medium'),
        (3, 'High'),
    ]
    priority = models.IntegerField("優先度",choices=PRIORITY_CHOICES, default=2)
    title = models.CharField("タイトル",max_length=200)
    description = models.TextField("説明",blank=True)
    due_date = models.DateField("期限", null=True, blank=True)
    completed = models.BooleanField("完了",default=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tasks')
    created_at = models.DateTimeField("作成日時",auto_now_add=True)
    updated_at = models.DateTimeField("更新日時",auto_now=True)
    
    # Simple History
    history = HistoricalRecords()

    class Meta:
        ordering = ["completed", "priority", "due_date", "-id"]
        verbose_name = "タスク"
        verbose_name_plural = "タスク"
        indexes = [
            models.Index(fields=["user", "completed", "due_date"]),
            models.Index(fields=["completed", "priority"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(priority__in=[1, 2, 3]),
                name="task_priority_valid",
            )
        ]


    def __str__(self):
        # __str__ は短く安全に
        status = "完了" if self.completed else "未完了"
        return f"{self.title}（{status}）"

    @property
    def priority_label(self) -> str:
        return dict(self.PRIORITY_CHOICES).get(self.priority, "-")