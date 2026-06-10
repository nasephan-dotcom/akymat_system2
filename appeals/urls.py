from django.urls import path
from . import views

urlpatterns = [
    path('', views.appeal_list, name='appeal_list'),
    path('create/', views.create_appeal, name='create_appeal'),
    path('appeal/<int:appeal_id>/', views.appeal_detail, name='appeal_detail'),
    path('appeal/<int:appeal_id>/change-status/<int:status_id>/', views.change_status, name='change_status'),
    path('appeal/<int:appeal_id>/assign/', views.assign_appeal, name='assign_appeal'),
    path('appeal/<int:appeal_id>/delete/', views.delete_appeal, name='delete_appeal'),
    path('register/', views.register, name='register'),
    path('assign/<int:appeal_id>/', views.assign_worker, name='assign_worker'),
    path('appeal/<int:appeal_id>/', views.appeal_detail, name='appeal_detail'),
    path('export/', views.export_excel, name='export_excel'),
]
