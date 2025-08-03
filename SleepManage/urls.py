from rest_framework.routers import DefaultRouter
from .views.SleepRecordView import SleepRecordViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'', SleepRecordViewSet, basename='sleep')

urlpatterns = router.urls