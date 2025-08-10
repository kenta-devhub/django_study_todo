from django import forms
from todo.models.task import Task
from django.core.exceptions import ValidationError
from django.core import validators
from django.utils import timezone

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ["title", "description", "due_date", "priority", "completed"]
        widgets = {
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "completed": forms.CheckboxInput(),
        }
    completed = forms.BooleanField(required=False)
    
    def clean_due_date(self):
        due_date = self.cleaned_data.get("due_date")
        if due_date and due_date < timezone.now().date():
            raise forms.ValidationError("期限は今日以降の日付を指定してください。")
        return due_date