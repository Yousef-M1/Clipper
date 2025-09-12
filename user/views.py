from rest_framework import generics , authentication , permissions
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.settings import api_settings
from user.serializers import (UserSerializer, AuthTokenSerializer , PlanSerializer , UserCreditsSerializer)
from core.models import Plan , UserCredits
# Create your views here.

# fbf9b969c4a9cd7c2e931949d382e42908bd40df

class UserCreateView(generics.CreateAPIView):
    serializer_class = UserSerializer

class AuthTokenView(ObtainAuthToken):
    serializer_class = AuthTokenSerializer
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES


class ManageUserView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

class PlanListView(generics.ListAPIView):
    queryset = Plan.objects.all()
    serializer_class = PlanSerializer
    permission_classes = [permissions.AllowAny]


class UserCreditsView(generics.RetrieveAPIView):
    serializer_class = UserCreditsSerializer
    # authentication_classes = [authentication.TokenAuthentication]  برجعلها بعدين
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return UserCredits.objects.get(user=self.request.user)
