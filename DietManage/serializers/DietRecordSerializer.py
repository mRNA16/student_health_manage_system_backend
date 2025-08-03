from rest_framework import serializers
from DietManage.models.MealItem import MealItem
from DietManage.models.MealRecord import MealRecord
from DietManage.models.NutritionFood import NutritionFood

class MealItemSerializer(serializers.ModelSerializer):
    food = serializers.PrimaryKeyRelatedField(
        queryset=NutritionFood.objects.all(),
        required=True 
    )
    class Meta:
        model = MealItem
        fields = '__all__'
        read_only_fields = ['estimated_calories', 'estimated_water', 'meal_record']

class MealRecordSerializer(serializers.ModelSerializer):
    items = MealItemSerializer(many=True)

    class Meta:
        model = MealRecord
        fields = '__all__'
        read_only_fields = ['id', 'user']

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        meal_record = MealRecord.objects.create(**validated_data)
        for item_data in items_data:
            MealItem.objects.create(meal_record=meal_record, **item_data)
            print(item_data)
        return meal_record
    
    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', [])
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        instance.items.all().delete()

        for item_data in items_data:
            MealItem.objects.create(meal_record=instance, **item_data)

        return instance

class NutritionFoodSerializer(serializers.ModelSerializer):
    class Meta:
        model = NutritionFood
        fields = '__all__'