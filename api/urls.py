from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'workflows', views.WorkflowViewSet, basename='workflow')

urlpatterns = [
    path('node-types/', views.node_types_list, name='node_types_list'),
    path('execute-node/', views.execute_node, name='execute_node'),
    path('execute-workflow/', views.execute_workflow, name='execute_workflow'),
    path('execute-workflow-async/', views.execute_workflow_async, name='execute_workflow_async'),
    path('execution/<str:execution_id>/status/', views.execution_status, name='execution_status'),
    path('workflows/<int:workflow_id>/trigger/', views.trigger_workflow, name='trigger_workflow'),
    path('workflows/<int:workflow_id>/regenerate-api-key/', views.regenerate_api_key, name='regenerate_api_key'),
    path('', include(router.urls)),
]
