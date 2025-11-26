from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'workflows', views.WorkflowViewSet, basename='workflow')

urlpatterns = [
    # Authentication endpoints
    path('auth/register/', views.register_user, name='register_user'),
    path('auth/login/', views.login_user, name='login_user'),
    path('auth/logout/', views.logout_user, name='logout_user'),
    path('auth/user/', views.current_user, name='current_user'),

    # Node and workflow endpoints
    path('node-types/', views.node_types_list, name='node_types_list'),
    path('execute-node/', views.execute_node, name='execute_node'),
    path('execute-workflow/', views.execute_workflow, name='execute_workflow'),
    path('execute-workflow-async/', views.execute_workflow_async, name='execute_workflow_async'),
    path('execution/<str:execution_id>/status/', views.execution_status, name='execution_status'),
    path('workflows/<int:workflow_id>/trigger/', views.trigger_workflow, name='trigger_workflow'),
    path('workflows/<int:workflow_id>/regenerate-api-key/', views.regenerate_api_key, name='regenerate_api_key'),
    path('workflows/<int:workflow_id>/executions/', views.workflow_executions, name='workflow_executions'),
    path('', include(router.urls)),
]
