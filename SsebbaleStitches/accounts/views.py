from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import OTP
from .serializers import (
    ForgotPasswordSerializer,
    LoginSerializer,
    ResendOtpSerializer,
    ResetPasswordSerializer,
    SignupSerializer,
    UserSerializer,
    VerifyOtpSerializer,
)
from .utils import send_otp_email

User = get_user_model()


def tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


class SignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        otp = OTP.create_for(user, OTP.PURPOSE_SIGNUP)
        send_otp_email(user, otp, "email verification")

        return Response(
            {"message": "Account created. Check your email for a verification code.", "email": user.email},
            status=status.HTTP_201_CREATED,
        )


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower().strip()
        code = serializer.validated_data["code"]

        try:
            user = User.objects.get(email=email, is_email_verified=False)
        except User.DoesNotExist:
            return Response({"detail": "No pending verification for this email."}, status=400)

        otp = (
            OTP.objects.filter(user=user, purpose=OTP.PURPOSE_SIGNUP, is_used=False)
            .order_by("-created_at")
            .first()
        )
        if not otp or otp.code != code:
            return Response({"detail": "Invalid code."}, status=400)
        if otp.is_expired:
            return Response({"detail": "Code expired. Request a new one."}, status=400)

        otp.is_used = True
        otp.save(update_fields=["is_used"])

        user.is_email_verified = True
        user.save(update_fields=["is_email_verified"])

        return Response({"message": "Email verified.", **tokens_for_user(user), "user": UserSerializer(user).data})


class ResendOtpView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResendOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower().strip()
        purpose = serializer.validated_data["purpose"]

        is_verified_required = purpose == "reset"
        try:
            user = User.objects.get(email=email, is_email_verified=is_verified_required)
        except User.DoesNotExist:
            # don't reveal whether the account exists
            return Response({"message": "If that account exists, a new code has been sent."})

        otp = OTP.create_for(user, purpose)
        label = "email verification" if purpose == "signup" else "password reset"
        send_otp_email(user, otp, label)

        return Response({"message": "If that account exists, a new code has been sent."})


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower().strip()
        password = serializer.validated_data["password"]

        try:
            user = User.objects.get(email=email, is_email_verified=True)
        except User.DoesNotExist:
            return Response({"detail": "Invalid email or password."}, status=401)

        if not user.check_password(password):
            return Response({"detail": "Invalid email or password."}, status=401)
        if not user.is_active:
            return Response({"detail": "This account has been disabled."}, status=403)

        return Response({**tokens_for_user(user), "user": UserSerializer(user).data})


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower().strip()

        try:
            user = User.objects.get(email=email, is_email_verified=True)
        except User.DoesNotExist:
            # don't reveal whether the account exists
            return Response({"message": "If that account exists, a reset code has been sent."})

        otp = OTP.create_for(user, OTP.PURPOSE_RESET)
        send_otp_email(user, otp, "password reset")

        return Response({"message": "If that account exists, a reset code has been sent."})


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower().strip()
        code = serializer.validated_data["code"]
        new_password = serializer.validated_data["new_password"]

        try:
            user = User.objects.get(email=email, is_email_verified=True)
        except User.DoesNotExist:
            return Response({"detail": "Invalid code."}, status=400)

        otp = (
            OTP.objects.filter(user=user, purpose=OTP.PURPOSE_RESET, is_used=False)
            .order_by("-created_at")
            .first()
        )
        if not otp or otp.code != code:
            return Response({"detail": "Invalid code."}, status=400)
        if otp.is_expired:
            return Response({"detail": "Code expired. Request a new one."}, status=400)

        otp.is_used = True
        otp.save(update_fields=["is_used"])

        user.set_password(new_password)
        user.save(update_fields=["password"])

        return Response({"message": "Password reset. You can now sign in."})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)
