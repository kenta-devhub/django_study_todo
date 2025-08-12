from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from accounts import views
from django.contrib.auth.views import LogoutView
from django.views.generic import RedirectView
from rest_framework.routers import DefaultRouter
from todo.api_views import TaskViewSet, TaskEventsView


router = DefaultRouter()
router.register(r"tasks", TaskViewSet, basename="task")

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", RedirectView.as_view(pattern_name="todo:task_list", permanent=False)),
    path("login/", views.login, name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("signup/", views.signup, name="signup"),
    path('todo/', include('todo.urls')),
    # API
    path("api/tasks/events/", TaskEventsView.as_view(), name="task_events"),
    path("api/", include(router.urls)),
    
]
