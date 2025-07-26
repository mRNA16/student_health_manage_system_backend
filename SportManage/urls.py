from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SportRecordViewSet,sport_list

router = DefaultRouter()
router.register(r'records', SportRecordViewSet, basename='sportrecord')

urlpatterns = [
    path('', include(router.urls)),
    path('list/', sport_list),
]