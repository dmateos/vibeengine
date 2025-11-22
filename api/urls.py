from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'node-types', views.NodeTypeViewSet, basename='nodetype')
router.register(r'workflows', views.WorkflowViewSet, basename='workflow')

urlpatterns = [
    path('hello/', views.hello_world, name='hello_world'),
    path('items/', views.get_items, name='get_items'),
    path('', include(router.urls)),
]
