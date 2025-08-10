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
    description = models.TextField("説明",blank=True, null=True)
    due_date = models.DateField("期限", null=True, blank=True)
    completed = models.BooleanField("完了",default=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tasks')
    created_at = models.DateTimeField("作成日時",auto_now_add=True)
    updated_at = models.DateTimeField("更新日時",auto_now=True)
    
    # Simple History
    history = HistoricalRecords()

    def __str__(self):
        return f"タイトル:{self.title} - 状態:{'完了' if self.completed else '未完了'} - 期限:{self.due_date} - 投稿者:{self.user.username}"

    class Meta:
        ordering = ['completed', 'priority', 'due_date', "-id"]
        verbose_name = "タスク"
        verbose_name_plural = "タスク"
