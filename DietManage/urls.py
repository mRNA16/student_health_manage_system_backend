from rest_framework.routers import DefaultRouter
from django.urls import path, include
from DietManage.views.DietRecordView import MealRecordViewSet, food_list
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'records', MealRecordViewSet, basename='mealrecord')

urlpatterns = [
    path('', include(router.urls)),
    path('list/', food_list),
]