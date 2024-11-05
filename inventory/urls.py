from django.urls import path
from .views import DeviceListView, MetricsAPIView, DeviceActionView, DeviceDetailView

app_name = 'inventory'

urlpatterns = [
    path('', DeviceListView.as_view(), name='device_list'),
    path('device/<uuid:pk>/', DeviceDetailView.as_view(), name='device_detail'),
    path('api/metrics/', MetricsAPIView.as_view(), name='metrics_api'),
    path('api/metrics', MetricsAPIView.as_view()),
    path('api/device/<uuid:device_id>/action/', DeviceActionView.as_view(), name='device_action'),
]