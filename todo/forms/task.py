from django import forms
from todo.models.task import Task

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ["title", "description", "due_date", "priority", "completed"]
        widgets = {
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "completed": forms.CheckboxInput(),
        }
    completed = forms.BooleanField(required=False)