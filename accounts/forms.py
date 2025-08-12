from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.utils.crypto import get_random_string
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

# 匿名ユーザー名を生成する
def generate_unique_username():
    return f"anonymous_{get_random_string(8)}"

# Email-based Authentication Form
class EmailAuthenticationForm(AuthenticationForm):
    """
    メールアドレスを使用して認証するためのカスタム認証フォーム
    """
    username = forms.EmailField(
        label='メールアドレス',
        max_length=255,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'メールアドレスを入力してください',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        label="パスワード",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'パスワードを入力してください',
        }),
    )

class CustomUserCreationForm(forms.ModelForm):
    """
    新規ユーザ登録フォーム
    - username は任意（未入力なら自動採番）
    - email は大小無視でユニーク
    - password1/password2 をバリデート
    """
    email = forms.EmailField(
        label="メールアドレス",
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "メールアドレスを入力してください",
            "autocomplete": "email",
        })
    )
    username = forms.CharField(
        label="ユーザー名（未入力なら自動）",
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "未入力なら自動採番されます",
            "autocomplete": "nickname",
        })
    )
    password1 = forms.CharField(
        label="パスワード",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "パスワードを入力してください",
            "autocomplete": "new-password",
        })
    )
    password2 = forms.CharField(
        label="確認用パスワード",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "同じパスワードを再入力してください",
            "autocomplete": "new-password",
        })
    )

    class Meta:
        model = get_user_model()
        fields = ("username", "email",)

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        UserModel = get_user_model()
        if UserModel.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("このメールアドレスは既に登録されています。")
        return email

    def clean(self):
        cleaned = super().clean()
        pw1 = cleaned.get("password1")
        pw2 = cleaned.get("password2")
        if pw1 and pw2 and pw1 != pw2:
            # フォーム全体のエラー（non_field_errors）として出す
            raise forms.ValidationError("パスワードが一致しません。")
        if pw1:
            validate_password(pw1)  # Djangoのパスワードバリデータ適用
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        # email正規化
        user.email = user.email.lower()

        # username 未入力なら自動採番（衝突回避付き）
        if not user.username:
            candidate = generate_unique_username()
            UserModel = get_user_model()
            while UserModel.objects.filter(username=candidate).exists():
                candidate = generate_unique_username()
            user.username = candidate

        # パスワード設定
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user
