from rest_framework import generics , authentication , permissions
from core.models import VideoRequest , CaptionSettings , Clip
from clipper.serializers import VideoRequestSerializer , CaptionSettingsSerializer , ClipSerializer
from .tasks.tasks import process_video_request
# Create your views here.

class VideoRequestCreateView(generics.CreateAPIView):
    serializer_class = VideoRequestSerializer
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        video_request = serializer.save(user=self.request.user)
        process_video_request.delay(video_request.id)


class VideoRequestListView(generics.ListAPIView):
    serializer_class = VideoRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return VideoRequest.objects.filter(user=self.request.user)


class CaptionSettingsUpdateView(generics.RetrieveUpdateAPIView):
    queryset = CaptionSettings.objects.all()
    serializer_class = CaptionSettingsSerializer
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(video_request__user=self.request.user)

class ClipListView(generics.ListAPIView):
    serializer_class = ClipSerializer
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        video_request_id = self.kwargs['video_request_id']
        return Clip.objects.filter(video_request__id=video_request_id, video_request__user=self.request.user)