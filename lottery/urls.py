from django.urls import path
from . import views

urlpatterns = [
    path('rent/<str:bike_id>/', views.rent_bike_view, name='rent_bike'),
    path('webhook/payment/', views.payment_webhook, name='payment_webhook'),
    path('api/sync/<str:bike_id>/', views.esp32_sync_api, name='esp32_sync_api'),
    path('api/status/<str:bike_id>/', views.bike_status_api, name='bike_status_api'),
]