from django.urls import path, include
from rest_framework.routers import DefaultRouter
from ActivityComment.views.ActivityCommentView import ActivityCommentViewSet

router = DefaultRouter()
router.register(r'', ActivityCommentViewSet, basename='comment')

urlpatterns = [
    path('', include(router.urls)),
]