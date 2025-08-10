from django import forms
from django.utils import timezone
from django.core.exceptions import ValidationError
from todo.models.task import Task

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ["title", "description", "due_date", "priority", "completed"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "completed": forms.CheckboxInput(),
        }
        error_messages = {
            "title": {"required": "タイトルは必須です。"},
        }

    def clean_due_date(self):
        due_date = self.cleaned_data.get("due_date")
        # 今日より過去は不可（今日OK）
        if due_date and due_date < timezone.localdate():
            raise ValidationError("期限は今日以降の日付を指定してください。")
        return due_date

    # 業務ルールがあれば（例：完了なら期日必須）
    # def clean(self):
    #     cleaned = super().clean()
    #     if cleaned.get("completed") and not cleaned.get("due_date"):
    #         self.add_error("due_date", "完了にする場合は期限を入力してください。")
    #     return cleaned
