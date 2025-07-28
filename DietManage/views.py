from rest_framework import viewsets, permissions
from rest_framework.response import Response
from .models import MealRecord, MealItem, NutritionFood
from .serializers import MealRecordSerializer, MealItemSerializer, NutritionFoodSerializer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

class MealRecordViewSet(viewsets.ModelViewSet):
    serializer_class = MealRecordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return MealRecord.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'code': 0,
            'message': '获取成功',
            'data': serializer.data
        })

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return Response({
            'code': 0,
            'message': '创建成功',
            'data': response.data
        })

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        return Response({
            'code': 0,
            'message': '更新成功',
            'data': response.data
        })

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({
            'code': 0,
            'message': '删除成功',
            'data': None
        })


class MealItemViewSet(viewsets.ModelViewSet):
    serializer_class = MealItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return MealItem.objects.filter(meal_record__user=self.request.user)

    def perform_create(self, serializer):
        serializer.save()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'code': 0,
            'message': '获取成功',
            'data': serializer.data
        })

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return Response({
            'code': 0,
            'message': '创建成功',
            'data': response.data
        })

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        return Response({
            'code': 0,
            'message': '更新成功',
            'data': response.data
        })

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({
            'code': 0,
            'message': '删除成功',
            'data': None
        })
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def food_list(request):
    foods = NutritionFood.objects.all()
    serializer = NutritionFoodSerializer(foods, many=True)
    return Response({
        'code': 0,
        'message': '获取成功',
        'data': serializer.data
    })