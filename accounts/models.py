from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
from django.utils.crypto import get_random_string
import uuid

# ユーザーIDを生成する
def create_id():
    return get_random_string(22)

# 匿名ユーザー名を生成する
def generate_unique_username():
    return f"anonymous_{get_random_string(8)}"


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, username=None,**extra_fields):
        if not email:
            raise ValueError('メールアドレスは必須です!')
        email = self.normalize_email(email)
        if not username:
            username = generate_unique_username()
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('スーパーユーザーはis_staff=Trueでなければなりません。')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('スーパーユーザーはis_superuser=Trueでなければなりません。')

        return self.create_user(email=email, password=password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    """カスタムユーザーモデル"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, max_length=255)
    username = models.CharField(max_length=150, unique=True, default=generate_unique_username)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email
    
    def has_perm(self, perm, obj=None):
        return self.is_superuser
    
    def has_module_perms(self, app_label):
        return self.is_superuser
