from django.urls import path
from .views import health, ask, neo4j_health

urlpatterns = [
    path('health/', health, name='Health'),
    path('health/neo4j/', neo4j_health, name='Neo4jHealth'),
    path('ask/', ask, name='AskQuestion'),
]
