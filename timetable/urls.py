from django.urls import path
from . import views

urlpatterns = [
    path('', views.schedule_view, name='schedule'),
    path('<str:group_name>/', views.group_schedule_view, name='group_schedule'),
]
