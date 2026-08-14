from django.conf import settings
from django.core.mail import send_mail


def send_otp_email(user, otp, purpose_label: str):
    subject = f"Your Ssebbale Stitches verification code"
    message = (
        f"Hi {user.full_name},\n\n"
        f"Your {purpose_label} code is: {otp.code}\n\n"
        f"This code expires in 10 minutes. If you didn't request this, you can ignore this email.\n\n"
        f"— Ssebbale Stitches"
    )
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
