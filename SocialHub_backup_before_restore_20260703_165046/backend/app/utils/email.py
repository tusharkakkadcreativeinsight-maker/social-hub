import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from ..config import settings


# Push notification service placeholder
# Integrate with Firebase Cloud Messaging / OneSignal in production
PUSH_NOTIFICATION_ENABLED: bool = False


def send_push_notification(
    device_token: str,
    title: str,
    body: str,
    data: Optional[dict] = None
) -> bool:
    """Send a push notification to a device."""
    if not PUSH_NOTIFICATION_ENABLED:
        return False
    # TODO: integrate with FCM / OneSignal / Expo Push
    return False


def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    from_email: Optional[str] = None
) -> bool:
    """Send an HTML email."""
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = from_email or settings.EMAIL_FROM
        msg["To"] = to_email
        msg["Subject"] = subject

        part = MIMEText(html_content, "html")
        msg.attach(part)

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)

        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


def send_verification_email(to_email: str, verification_token: str) -> bool:
    """Send email verification link."""
    verification_url = f"http://localhost:8000/api/auth/verify-email?token={verification_token}"
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
            <h1 style="color: white; margin: 0;">SocialHub</h1>
        </div>
        <div style="background: #ffffff; padding: 30px; border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 10px 10px;">
            <h2 style="color: #333; margin-top: 0;">Verify Your Email</h2>
            <p style="color: #666; line-height: 1.6;">Thank you for registering! Please click the button below to verify your email address.</p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{verification_url}" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 14px 30px; text-decoration: none; border-radius: 25px; font-size: 16px; display: inline-block;">Verify Email</a>
            </div>
            <p style="color: #999; font-size: 12px;">This link will expire in 24 hours.</p>
            <p style="color: #999; font-size: 12px;">If you didn't create an account, please ignore this email.</p>
        </div>
    </body>
    </html>
    """
    return send_email(to_email, "Verify Your Email - SocialHub", html)


def send_password_reset_email(to_email: str, reset_token: str) -> bool:
    """Send password reset link."""
    reset_url = f"http://localhost:8000/reset-password?token={reset_token}"
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
            <h1 style="color: white; margin: 0;">SocialHub</h1>
        </div>
        <div style="background: #ffffff; padding: 30px; border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 10px 10px;">
            <h2 style="color: #333; margin-top: 0;">Reset Your Password</h2>
            <p style="color: #666; line-height: 1.6;">We received a request to reset your password. Click the button below to set a new password.</p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{reset_url}" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 14px 30px; text-decoration: none; border-radius: 25px; font-size: 16px; display: inline-block;">Reset Password</a>
            </div>
            <p style="color: #999; font-size: 12px;">This link will expire in 1 hour.</p>
            <p style="color: #999; font-size: 12px;">If you didn't request a password reset, please ignore this email.</p>
        </div>
    </body>
    </html>
    """
    return send_email(to_email, "Reset Your Password - SocialHub", html)


def send_welcome_email(to_email: str, username: str) -> bool:
    """Send welcome email after successful registration."""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
            <h1 style="color: white; margin: 0;">SocialHub</h1>
        </div>
        <div style="background: #ffffff; padding: 30px; border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 10px 10px;">
            <h2 style="color: #333; margin-top: 0;">Welcome to SocialHub, {username}!</h2>
            <p style="color: #666; line-height: 1.6;">We're excited to have you on board! Start exploring content, sharing posts, and connecting with people.</p>
            <p style="color: #666; line-height: 1.6;">Here are some things you can do:</p>
            <ul style="color: #666; line-height: 1.8;">
                <li>Complete your profile with a photo and bio</li>
                <li>Discover and follow people</li>
                <li>Share posts, stories, and reels</li>
                <li>Chat with others in real-time</li>
            </ul>
            <div style="text-align: center; margin: 30px 0;">
                <a href="http://localhost:8000/" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 14px 30px; text-decoration: none; border-radius: 25px; font-size: 16px; display: inline-block;">Get Started</a>
            </div>
        </div>
    </body>
    </html>
    """
    return send_email(to_email, "Welcome to SocialHub!", html)