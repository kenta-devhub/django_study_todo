import logging
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView
from ..models import Task
from ..forms import TaskForm
from django.contrib import messages

logger = logging.getLogger(__name__)

SORTABLE_FIELDS = {
    "title": "title",
    "due_date": "due_date",
    "priority": "priority",
    "completed": "completed",
    "user": "user__username",  # ユーザー名での並び替え
}

class TaskListView(LoginRequiredMixin, ListView):
    model = Task
    template_name = 'todo/task/list.html'
    context_object_name = 'obj'
    paginate_by = 10
    ordering = ['due_date']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["header_title"] = "タスク一覧"
        context["title"] = "タスク"
        return context
        
    def get_queryset(self):
        qs = super().get_queryset().filter(user=self.request.user).select_related("user")

        sort = self.request.GET.get('sort')
        direction = self.request.GET.get('dir', 'asc').lower()

        if sort in SORTABLE_FIELDS:
            field = SORTABLE_FIELDS[sort]
            if direction == 'desc':
                field = f'-{field}'
            qs = qs.order_by(field)
        # sort指定が無効なら self.ordering が適用される

        return qs

class TaskCreateView(LoginRequiredMixin, CreateView):
    model = Task
    form_class = TaskForm
    template_name = 'todo/task/create.html'
    success_url = reverse_lazy('todo:task_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["header_title"] = "タスク登録"
        context["title"] = "タスク登録"
        return context
    
    def form_invalid(self, form):
        response = super().form_invalid(form)
        print(f"Form error: {form.errors}")
        messages.error(self.request, "タスクの登録に失敗しました。")
        return response

    def form_valid(self, form):
        form.instance.user = self.request.user  # ログインユーザーを設定
        response = super().form_valid(form)        
        logger.info(
            "Task created: %s - %s by %s",
            form.instance.pk,
            form.instance.title,
            getattr(self.request.user, "username", getattr(self.request.user, "email", "unknown")),
        )
        return response

class TaskUpdateView(LoginRequiredMixin, UpdateView):
    model = Task
    form_class = TaskForm
    template_name = 'todo/task/update.html'
    context_object_name = 'obj'
    success_url = reverse_lazy('todo:task_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["header_title"] = "タスク更新"
        context["title"] = "タスク更新"
        return context

    def form_valid(self, form):
        form.instance.user = self.request.user  # ログインユーザーを設定
        response = super().form_valid(form)
        logger.info(
            "Task updated: %s - %s by %s",
            form.instance.pk,
            form.instance.title,
            getattr(self.request.user, "username", getattr(self.request.user, "email", "unknown")),
        )
        return response
    
class TaskDetailView(LoginRequiredMixin, DetailView):
    model = Task
    template_name = 'todo/task/detail.html'
    context_object_name = 'obj'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["header_title"] = "タスク詳細"
        context["title"] = "タスク詳細"
        history = self.object.history.all().order_by("-history_date") #type: ignore
        history_changes = []
        for record in history:
            if record.prev_record:
                diff = record.diff_against(record.prev_record)
                changes = {
                    change.field: {"old": change.old, "new": change.new}
                    for change in diff.changes
                }
                history_changes.append(
                    {
                        "history_date": record.history_date,
                        "history_user": record.history_user,
                        "history_type": record.history_type,
                        "changes": changes,
                    }
                )
            else:
                history_changes.append(
                    {
                        "history_date": record.history_date,
                        "history_user": record.history_user,
                        "history_type": record.history_type,
                        "changes": None,
                    }
                )

        context["history_changes"] = history_changes
        return context


class TaskDeleteView(LoginRequiredMixin, DeleteView):
    model = Task
    template_name = 'todo/task/confirm_delete.html'
    context_object_name = 'obj'
    success_url = reverse_lazy('todo:task_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["header_title"] = "タスク削除"
        context["title"] = "タスク削除"
        return context

task_list = TaskListView.as_view()
task_create = TaskCreateView.as_view()
task_update = TaskUpdateView.as_view()
task_detail = TaskDetailView.as_view()
task_delete = TaskDeleteView.as_view()