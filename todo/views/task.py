import logging
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView
from django.contrib.messages.views import SuccessMessageMixin

from ..models.task import Task
from ..forms.task import TaskForm
from django.db.models import Q
from django.utils import timezone

logger = logging.getLogger(__name__)

SORTABLE_FIELDS = {
    "title": "title",
    "due_date": "due_date",
    "priority": "priority",
    "completed": "completed",
    # "user": "user__username",  # 全体一覧を作るときに有効化
}


class TaskListView(LoginRequiredMixin, ListView):
    model = Task
    template_name = "todo/task/list.html"
    context_object_name = "obj"
    paginate_by = 10
    ordering = ["due_date"]  # ソート未指定時のデフォルト

    SORTABLE_FIELDS = {
        "due_date": "due_date",
        "priority": "priority",
        "created_at": "created_at",
        "title": "title",
    }

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .filter(user=self.request.user)
            .select_related("user")
        )

        # --- フィルタ ---
        q = (self.request.GET.get("q") or "").strip()
        status = (self.request.GET.get("status") or "all").lower()

        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))

        if status == "open":   # 未完
            qs = qs.filter(completed=False)
        elif status == "done": # 完了
            qs = qs.filter(completed=True)

        # --- ソート ---
        sort = self.request.GET.get("sort") or "due_date"
        direction = (self.request.GET.get("dir") or "asc").lower()
        if sort in self.SORTABLE_FIELDS:
            field = self.SORTABLE_FIELDS[sort]
            if direction == "desc":
                field = f"-{field}"
            qs = qs.order_by(field)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # UI反映用に現在値と件数
        user_qs = Task.objects.filter(user=self.request.user)
        q = (self.request.GET.get("q") or "").strip()
        status = (self.request.GET.get("status") or "all").lower()

        ctx["q"] = q
        ctx["status"] = status
        ctx["sort"] = self.request.GET.get("sort") or "due_date"
        ctx["dir"] = (self.request.GET.get("dir") or "asc").lower()
        ctx["today"] = timezone.localdate()

        ctx["count_all"] = user_qs.count()
        ctx["count_open"] = user_qs.filter(completed=False).count()
        ctx["count_done"] = user_qs.filter(completed=True).count()
        return ctx



class TaskCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Task
    form_class = TaskForm
    template_name = "todo/task/create.html"
    success_url = reverse_lazy("todo:task_list")
    success_message = "タスクを登録しました。"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["header_title"] = "タスク登録"
        ctx["title"] = "タスク登録"
        return ctx

    def form_valid(self, form):
        form.instance.user = self.request.user
        resp = super().form_valid(form)
        logger.info(
            "Task created id=%s title=%s by=%s",
            self.object.pk,
            self.object.title,
            getattr(self.request.user, "username", getattr(self.request.user, "email", "unknown")),
        )
        return resp

    def form_invalid(self, form):
        logger.error("Task create form invalid errors=%s", dict(form.errors))
        messages.error(self.request, "タスクの登録に失敗しました。")
        return super().form_invalid(form)


class TaskUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Task
    form_class = TaskForm
    template_name = "todo/task/update.html"
    context_object_name = "obj"
    success_url = reverse_lazy("todo:task_list")
    success_message = "タスクを更新しました。"

    # ★ IDOR対策：自分のタスクだけを取得
    def get_queryset(self):
        return Task.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["header_title"] = "タスク更新"
        ctx["title"] = "タスク更新"
        return ctx

    def form_valid(self, form):
        # 念のため上書き（owner固定）
        form.instance.user = self.request.user
        resp = super().form_valid(form)
        logger.info(
            "Task updated id=%s title=%s by=%s",
            self.object.pk,
            self.object.title,
            getattr(self.request.user, "username", getattr(self.request.user, "email", "unknown")),
        )
        return resp


class TaskDetailView(LoginRequiredMixin, DetailView):
    model = Task
    template_name = "todo/task/detail.html"
    context_object_name = "obj"

    # ★ IDOR対策
    def get_queryset(self):
        return Task.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["header_title"] = "タスク詳細"
        ctx["title"] = "タスク詳細"

        # 履歴は重くなりがちなのでユーザーをまとめて取得し、件数も適度に制限
        history_qs = (
            self.object.history.select_related("history_user")
            .order_by("-history_date")[:50]
        )

        history_changes = []
        for record in history_qs:
            prev = record.prev_record
            if prev:
                diff = record.diff_against(prev)
                changes = {c.field: {"old": c.old, "new": c.new} for c in diff.changes}
            else:
                changes = None
            history_changes.append(
                {
                    "history_date": record.history_date,
                    "history_user": record.history_user,
                    "history_type": record.history_type,
                    "changes": changes,
                }
            )

        ctx["history_changes"] = history_changes
        return ctx


class TaskDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Task
    template_name = "todo/task/confirm_delete.html"
    context_object_name = "obj"
    success_url = reverse_lazy("todo:task_list")
    success_message = "タスクを削除しました。"

    # ★ IDOR対策
    def get_queryset(self):
        return Task.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        logger.warning("Task deleted id=%s title=%s by=%s", obj.id, obj.title, request.user)
        messages.success(request, self.success_message)
        return super().delete(request, *args, **kwargs)


# 関数エイリアス（URL confで使うならそのままでもOK）
task_list = TaskListView.as_view()
task_create = TaskCreateView.as_view()
task_update = TaskUpdateView.as_view()
task_detail = TaskDetailView.as_view()
task_delete = TaskDeleteView.as_view()
