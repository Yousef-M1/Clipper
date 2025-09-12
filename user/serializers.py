from django.contrib.auth import (get_user_model,authenticate)
from rest_framework import serializers
from django.utils.translation import gettext as _
from core.models import UserCredits , Plan


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ('id', 'email', 'password')
        extra_kwargs = {
            'password': {'write_only': True , 'min_length': 8, 'max_length': 128}
        }

    def create(self, validated_data):
        user = get_user_model().objects.create_user(**validated_data)
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user

class AuthTokenSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(
        style={'input_type': 'password'}, write_only=True, min_length=6, max_length=128, trim_whitespace=True
    )

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        user = authenticate(request=self.context.get('request'), email=email, password=password)
        if not user:
            raise serializers.ValidationError(_('Unable to log in with provided credentials.'))

        attrs['user'] = user
        return attrs


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = ['id', 'name', 'monthly_credits', 'credit_per_clip']

class UserCreditsSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)
    remaining_credits = serializers.IntegerField(read_only=True)

    class Meta:
        model = UserCredits
        fields = ['id',  'plan', 'used_credits', 'remaining_credits', 'last_reset']
        read_only_fields = ['user', 'remaining_credits', 'last_reset']