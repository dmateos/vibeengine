from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'node-types', views.NodeTypeViewSet, basename='nodetype')
router.register(r'workflows', views.WorkflowViewSet, basename='workflow')

urlpatterns = [
    path('execute-node/', views.execute_node, name='execute_node'),
    path('execute-workflow/', views.execute_workflow, name='execute_workflow'),
    path('execute-workflow-async/', views.execute_workflow_async, name='execute_workflow_async'),
    path('execution/<str:execution_id>/status/', views.execution_status, name='execution_status'),
    path('', include(router.urls)),
]
