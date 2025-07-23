from rest_framework.routers import DefaultRouter
from .views import SleepRecordViewSet

router = DefaultRouter()
router.register(r'', SleepRecordViewSet, basename='sleep')

urlpatterns = router.urls