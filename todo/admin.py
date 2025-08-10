from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models.task import Task

@admin.register(Task)
class TaskAdmin(SimpleHistoryAdmin):
    list_display = ("id", "title", "priority", "due_date", "completed", "created_at", "user")
    list_filter = ("completed", "priority", "due_date", "created_at", "user")
    search_fields = ("title", "description")
    date_hierarchy = "due_date"
