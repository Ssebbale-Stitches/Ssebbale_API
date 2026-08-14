import random
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, full_name, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, full_name=full_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, full_name, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_email_verified", True)
        return self.create_user(email, full_name, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=32, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)

    # true for tailor/admin accounts that should reach the dashboard
    is_tailor = models.BooleanField(default=False)

    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    def __str__(self):
        return self.email


class OTP(models.Model):
    PURPOSE_SIGNUP = "signup"
    PURPOSE_RESET = "reset"
    PURPOSE_CHOICES = [
        (PURPOSE_SIGNUP, "Signup verification"),
        (PURPOSE_RESET, "Password reset"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="otps")
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=16, choices=PURPOSE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        indexes = [models.Index(fields=["user", "purpose", "is_used"])]

    @staticmethod
    def generate_code():
        return f"{random.randint(0, 999999):06d}"

    @classmethod
    def create_for(cls, user, purpose, ttl_minutes=10):
        # invalidate any previous unused codes for this purpose
        cls.objects.filter(user=user, purpose=purpose, is_used=False).update(is_used=True)
        return cls.objects.create(
            user=user,
            code=cls.generate_code(),
            purpose=purpose,
            expires_at=timezone.now() + timedelta(minutes=ttl_minutes),
        )

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"{self.user.email} · {self.purpose} · {self.code}"
