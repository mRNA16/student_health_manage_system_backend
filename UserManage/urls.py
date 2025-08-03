from django.urls import path
from UserManage.views.UserView import (RegisterView, ProfileView, LogoutView, UserViewSet,
                                        CustomTokenObtainPairView, CodeView)
from UserManage.views.FriendView import FriendViewSet
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'', FriendViewSet, basename='friend')

urlpatterns = [
    path('register/', RegisterView.as_view()),
    path('login/', CustomTokenObtainPairView.as_view()),
    path('token/refresh/', TokenRefreshView.as_view()),
    path('user/profile/', ProfileView.as_view()),
    path('logout/', LogoutView.as_view()),
    path('codes/',CodeView.as_view()),
    path('user/search/', UserViewSet.as_view({'get': 'list'}), name='user-search'),
    path('user/info/',UserViewSet.as_view({'get': 'retrieve'}),name='user-info'),
] + router.urls