from django.urls import path
from .views import health, ask

urlpatterns = [
    path('health/', health, name='Health'),
    path('ask/', ask, name='AskQuestion'),
]
