from django.urls import path
from .views import redir
urlpatterns = [
    path('redirect', redir),
]