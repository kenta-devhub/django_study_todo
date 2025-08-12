from django.urls import path
from . import views

app_name = 'todo'

urlpatterns = [
    path('list/', views.task_list, name='task_list'),
    path('create/', views.task_create, name='task_create'),
    path('detail/<int:pk>/', views.task_detail, name='task_detail'),
    path('update/<int:pk>/', views.task_update, name='task_update'),
    path('delete/<int:pk>/', views.task_delete, name='task_delete'),
    path("kanban/", views.task_kanban, name="task_kanban"),
    path("calendar/", views.task_calendar, name="task_calendar"),
]
