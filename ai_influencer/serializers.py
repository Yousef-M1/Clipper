"""
Serializers for AI influencer API
"""
from rest_framework import serializers
from .models import AvatarProject, AvatarCharacter, VoiceProfile


class AvatarCharacterSerializer(serializers.ModelSerializer):
    """Serializer for avatar characters"""

    class Meta:
        model = AvatarCharacter
        fields = [
            'id', 'name', 'description', 'avatar_image', 'gender',
            'voice_style', 'created_at'
        ]


class VoiceProfileSerializer(serializers.ModelSerializer):
    """Serializer for voice profiles"""

    class Meta:
        model = VoiceProfile
        fields = [
            'id', 'name', 'voice_id', 'language', 'gender', 'engine',
            'sample_rate', 'is_premium'
        ]


class AvatarProjectSerializer(serializers.ModelSerializer):
    """Serializer for avatar projects (read operations)"""

    character_name = serializers.CharField(source='character.name', read_only=True)
    voice_name = serializers.CharField(source='voice.name', read_only=True)
    avatar_image_url = serializers.SerializerMethodField()
    estimated_credits_cost = serializers.ReadOnlyField()

    class Meta:
        model = AvatarProject
        fields = [
            'id', 'title', 'script', 'character', 'character_name',
            'custom_avatar_image', 'avatar_image_url', 'voice', 'voice_name',
            'voice_speed', 'voice_pitch', 'aspect_ratio', 'video_quality',
            'background_color', 'background_image', 'lip_sync_model',
            'enable_emotions', 'head_movement_intensity', 'status',
            'progress_percentage', 'error_message', 'generated_audio',
            'final_video', 'thumbnail', 'video_duration', 'file_size_mb',
            'processing_time', 'estimated_credits_cost', 'created_at',
            'updated_at', 'completed_at'
        ]

    def get_avatar_image_url(self, obj):
        """Get the avatar image URL"""
        return obj.avatar_image_url


class CreateAvatarProjectSerializer(serializers.ModelSerializer):
    """Serializer for creating avatar projects"""

    estimated_credits_cost = serializers.SerializerMethodField()

    class Meta:
        model = AvatarProject
        fields = [
            'title', 'script', 'character', 'custom_avatar_image',
            'voice', 'voice_speed', 'voice_pitch', 'aspect_ratio',
            'video_quality', 'background_color', 'background_image',
            'lip_sync_model', 'enable_emotions', 'head_movement_intensity',
            'estimated_credits_cost'
        ]

    def get_estimated_credits_cost(self, obj):
        """Calculate estimated credits cost"""
        return obj.estimated_credits_cost

    def validate(self, data):
        """Validate the avatar project data"""

        # Ensure either character or custom_avatar_image is provided
        if not data.get('character') and not data.get('custom_avatar_image'):
            raise serializers.ValidationError(
                "Either character or custom_avatar_image must be provided"
            )

        # Ensure voice is provided
        if not data.get('voice'):
            raise serializers.ValidationError("Voice profile is required")

        # Validate script length
        script = data.get('script', '')
        if len(script) < 10:
            raise serializers.ValidationError("Script must be at least 10 characters long")
        if len(script) > 5000:
            raise serializers.ValidationError("Script must be less than 5000 characters")

        # Validate voice settings
        voice_speed = data.get('voice_speed', 1.0)
        if not 0.5 <= voice_speed <= 2.0:
            raise serializers.ValidationError("Voice speed must be between 0.5 and 2.0")

        voice_pitch = data.get('voice_pitch', 1.0)
        if not 0.5 <= voice_pitch <= 2.0:
            raise serializers.ValidationError("Voice pitch must be between 0.5 and 2.0")

        # Validate head movement intensity
        head_movement = data.get('head_movement_intensity', 0.5)
        if not 0.0 <= head_movement <= 1.0:
            raise serializers.ValidationError("Head movement intensity must be between 0.0 and 1.0")

        # Validate background color format
        bg_color = data.get('background_color', '#000000')
        if not bg_color.startswith('#') or len(bg_color) != 7:
            raise serializers.ValidationError("Background color must be in hex format (#RRGGBB)")

        return data

    def validate_custom_avatar_image(self, value):
        """Validate custom avatar image"""
        if value:
            # Check file size (max 10MB)
            if value.size > 10 * 1024 * 1024:
                raise serializers.ValidationError("Avatar image must be less than 10MB")

            # Check file type
            if not value.content_type.startswith('image/'):
                raise serializers.ValidationError("File must be an image")

            # Check image format
            allowed_formats = ['image/jpeg', 'image/jpg', 'image/png']
            if value.content_type not in allowed_formats:
                raise serializers.ValidationError("Image must be JPEG or PNG format")

        return value

    def validate_background_image(self, value):
        """Validate background image"""
        if value:
            # Check file size (max 20MB)
            if value.size > 20 * 1024 * 1024:
                raise serializers.ValidationError("Background image must be less than 20MB")

            # Check file type
            if not value.content_type.startswith('image/'):
                raise serializers.ValidationError("File must be an image")

        return value