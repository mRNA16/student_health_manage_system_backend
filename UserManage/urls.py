from django.urls import path
from .views import RegisterView, ProfileView, LogoutView, CustomTokenObtainPairView, CodeView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('register/', RegisterView.as_view()),
    path('login/', CustomTokenObtainPairView.as_view()),
    path('token/refresh/', TokenRefreshView.as_view()),
    path('user/profile/', ProfileView.as_view()),
    path('logout/', LogoutView.as_view()),
    path('codes/',CodeView.as_view()),
]