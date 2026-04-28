from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, ServiceViewSet, ProductViewSet, 
    AppointmentViewSet, PaymentViewSet, ExpenseViewSet
)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'services', ServiceViewSet)
router.register(r'products', ProductViewSet)
router.register(r'appointments', AppointmentViewSet)
router.register(r'payments', PaymentViewSet)
router.register(r'expenses', ExpenseViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
