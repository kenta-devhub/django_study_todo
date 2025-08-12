
from pathlib import Path
import os
import environ
from django.contrib.messages import constants as msg

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')

env = environ.Env()
root = environ.Path(str(BASE_DIR / 'secrets'))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

DEBUG = True

if DEBUG:
    env.read_env(root('.env.dev'))
else:
    env.read_env(root('.env.prod'))

SECRET_KEY = env.str('SECRET_KEY')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts',
    'todo',
    'simple_history',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    "simple_history.middleware.HistoryRequestMiddleware",
    
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [TEMPLATE_DIR, ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME':  env.str("MYSQL_NAME"),         
        'USER': env.str("MYSQL_USER"),
        'PASSWORD': env.str("MYSQL_PASSWORD"),
        'HOST': env.str("MYSQL_HOST"),
        'PORT': env.str("MYSQL_PORT"),
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
         "TEST": {"NAME": "test_mydb"},
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'ja'

TIME_ZONE = 'Asia/Tokyo'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = '/static/'
# STATICFILES_DIRS = [os.path.join(BASE_DIR, 'staticfiles'),]
STATICFILES_DIRS = [BASE_DIR / "static"]  # プロジェクト直下staticを使う場合
STATIC_ROOT = BASE_DIR / "staticfiles"    # collectstatic 先（本番で使用）

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# カスタムユーザーモデル
AUTH_USER_MODEL = "accounts.User"

# session維持時間　1ヵ月
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30

# ブラウザを閉じたらsession終了
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "todo:task_list"
# LOGIN_REDIRECT_URL = "login"
LOGOUT_REDIRECT_URL = "login"

MESSAGE_TAGS = {
    msg.DEBUG: "secondary",  # Bootstrap相当
    msg.INFO: "info",
    msg.SUCCESS: "success",
    msg.WARNING: "warning",
    msg.ERROR: "danger",     # ← ここが重要
}

LOGGING = {
    'version': 1,  # 設定のバージョン（固定値）
    'disable_existing_loggers': False,  # 既存のロガーを無効にしない
    'formatters': {
        'simple': {  # ログの書式を定義
            'format': '[{levelname}] {asctime} {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {  # 画面（コンソール）に出力
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'info_file': {
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/info.log'),
            'formatter': 'simple',
            'level': 'INFO',
        },
        'error_file': {
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/error.log'),
            'formatter': 'simple',
            'level': 'ERROR',
        },
    },
    'root': {
        'handlers': ['console', 'info_file', 'error_file'],
        'level': 'INFO',
    },
}

INSTALLED_APPS += [
    "rest_framework",
]

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
}


KANBAN_COLUMNS = [
    ("todo", "ToDo"),
    ("doing", "進行中"),
    ("blocked", "保留"),  # ← 追加
    ("done", "完了"),
]
