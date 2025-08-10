from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from .models import generate_unique_username

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

class UserCreationForm(forms.ModelForm):
    """
    新規ユーザ登録用のカスタムフォーム
    """
    
    email = forms.EmailField(
        label="メールアドレス",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'メールアドレスを入力してください',
        })
    )
    password = forms.CharField(
        label="パスワード",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'パスワードを入力してください',
        })
    )
    password2 = forms.CharField(
        label="確認用パスワード",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '同じパスワードを再入力してください',
        })
    )


    class Meta:
        model = get_user_model()
        fields = ('username', 'email',)
        
    def clean_email(self):
        email = self.cleaned_data['email']
        User = get_user_model()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("このメールアドレスは既に登録されています。")
        return email

    def clean(self):
        """
        フォームの追加バリデーション
        """
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password2 = cleaned_data.get('password2')

        if password != password2:
            raise forms.ValidationError('パスワードが一致しません。')

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if not user.username:
            # ユーザー名を自動生成
            user.username = generate_unique_username()
        if commit:
            user.save()
        return user