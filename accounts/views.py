from django.views.generic import CreateView
from django.contrib.auth.views import LoginView
from django.contrib import messages
from .forms import UserCreationForm, EmailAuthenticationForm  # type: ignore
from django.urls import reverse_lazy


class Login(LoginView):
    """
    ログインビュー
    """
    template_name = "accounts/login.html"
    authentication_form = EmailAuthenticationForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form_type"] = "login"
        return context

    def form_valid(self, form):
        messages.success(self.request, "ログインしました。")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "エラーでログインできません。やり直してください")
        return super().form_invalid(form)


class SignUp(CreateView):
    form_class = UserCreationForm
    template_name = "accounts/login.html"
    success_url = reverse_lazy("login")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form_type"] = "signup"
        return context

    def form_valid(self, form):
        messages.success(
            self.request, "新規登録が完了しました。続けてログインしてください。"
        )
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "登録内容にエラーがあります。修正してください。")
        print(form.errors)
        return super().form_invalid(form)

login = Login.as_view()
signup = SignUp.as_view()