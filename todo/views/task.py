import logging
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView
from ..models import Task
from ..forms import TaskForm

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

task_list = TaskListView.as_view()
task_create = TaskCreateView.as_view()