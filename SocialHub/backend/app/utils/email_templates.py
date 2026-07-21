from dataclasses import dataclass
from html import escape
from typing import Optional


@dataclass(frozen=True)
class EmailContent:
    subject: str
    html: str
    text: str


BRAND = "SocialHub"


def _button(label: str, url: str) -> str:
    return f"""
    <table role="presentation" cellspacing="0" cellpadding="0" border="0" align="center" style="margin:28px auto;">
      <tr><td style="border-radius:999px;background:linear-gradient(135deg,#6366f1,#a855f7);">
        <a href="{escape(url)}" style="display:inline-block;padding:14px 26px;color:#ffffff;text-decoration:none;font-weight:700;font-size:15px;border-radius:999px;">{escape(label)}</a>
      </td></tr>
    </table>
    """


def _otp_box(otp: str) -> str:
    spaced = " ".join(str(otp))
    return f"""
    <div style="margin:26px auto 10px;text-align:center;">
      <div style="display:inline-block;letter-spacing:10px;font-size:34px;line-height:1;font-weight:800;color:#111827;background:#f8fafc;border:1px solid #e5e7eb;border-radius:18px;padding:18px 18px 18px 28px;">{escape(spaced)}</div>
    </div>
    """


def _layout(title: str, preheader: str, body_html: str, support_email: str) -> str:
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light dark"><meta name="supported-color-schemes" content="light dark">
<title>{escape(title)}</title>
<style>
@media (max-width:620px){{.container{{width:100%!important}}.card{{padding:24px!important;border-radius:18px!important}}.logo{{font-size:24px!important}}}}
@media (prefers-color-scheme:dark){{body{{background:#0f172a!important}}.card{{background:#111827!important;color:#e5e7eb!important;border-color:#273449!important}}.muted{{color:#cbd5e1!important}}}}
</style></head>
<body style="margin:0;padding:0;background:#eef2ff;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;color:#111827;">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;">{escape(preheader)}</div>
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#eef2ff;padding:28px 12px;"><tr><td align="center">
<table role="presentation" class="container" width="600" cellspacing="0" cellpadding="0" border="0" style="width:600px;max-width:600px;">
<tr><td style="background:linear-gradient(135deg,#4f46e5 0%,#7c3aed 48%,#ec4899 100%);padding:34px 28px;text-align:center;border-radius:24px 24px 0 0;">
<div class="logo" style="color:#fff;font-size:30px;font-weight:900;letter-spacing:-.5px;">● SocialHub</div>
<div style="color:#ede9fe;font-size:14px;margin-top:8px;">Secure social connections, built for creators</div>
</td></tr>
<tr><td class="card" style="background:#ffffff;border:1px solid #e5e7eb;border-top:0;border-radius:0 0 24px 24px;padding:34px;box-shadow:0 18px 45px rgba(79,70,229,.13);">
{body_html}
<hr style="border:0;border-top:1px solid #e5e7eb;margin:32px 0 22px;">
<p class="muted" style="margin:0;color:#64748b;font-size:13px;line-height:1.7;text-align:center;">Need help? Contact <a href="mailto:{escape(support_email)}" style="color:#4f46e5;text-decoration:none;">Support</a></p>
<p class="muted" style="margin:10px 0 0;color:#94a3b8;font-size:12px;line-height:1.6;text-align:center;">© 2026 SocialHub. You received this email because you use SocialHub.</p>
</td></tr></table></td></tr></table></body></html>"""


def create_account_email(username: str, otp: str, support_email: str, app_url: str) -> EmailContent:
    """Combined welcome + verification email sent after registration.

    This is the ONLY email sent during registration. It includes:
    - Welcome message
    - 6-digit verification OTP
    - Verification link
    """
    name = escape(username or "there")
    subject = "Welcome to SocialHub - Verify Your Email"
    text = (
        f"Hi {username},\n\n"
        f"Welcome to SocialHub! Your account has been created.\n\n"
        f"Your verification code is: {otp}\n\n"
        f"This code expires in 10 minutes.\n\n"
        f"Enter this code at: {app_url}/verify-email\n\n"
        f"Thank you,\nThe SocialHub Team"
    )
    html = _layout(subject, "Welcome to SocialHub. Verify your email.", f"""
    <h1 style="margin:0 0 12px;font-size:26px;line-height:1.25;">Welcome to SocialHub</h1>
    <p class="muted" style="color:#475569;line-height:1.7;font-size:16px;">Hi {name}, your account has been created. Please verify your email address using the code below. This code expires in 10 minutes and can only be used once.</p>
    {_otp_box(otp)}
    <p style="text-align:center;margin:14px 0 0;color:#64748b;font-size:14px;">Or click the button below to verify:</p>
    {_button("Verify Email", f"{app_url}/verify-email")}
    """, support_email)
    return EmailContent(subject, html, text)


def welcome_email(username: str, otp: str, app_url: str, support_email: str) -> EmailContent:
    """Welcome email - kept for backward compatibility."""
    subject = "Welcome to SocialHub"
    text = f"Welcome to SocialHub, {username}."
    html = _layout(subject, "Welcome to SocialHub.", f"""
    <h1 style="margin:0 0 12px;font-size:28px;line-height:1.25;">Welcome, {escape(username)}.</h1>
    <p class="muted" style="color:#475569;line-height:1.7;font-size:16px;">Your profile has been created. Start discovering creators, sharing posts, and building your community.</p>
    {_button("Get Started", app_url)}
    """, support_email)
    return EmailContent(subject, html, text)


def verify_email_otp(otp: str, app_url: str, support_email: str) -> EmailContent:
    subject = "Verify Your Email Address"
    text = f"Use this SocialHub verification code: {otp}. It expires in 10 minutes. Verify here: {app_url}/verify-email"
    html = _layout(subject, "Use your 6-digit code to verify your email.", f"""
    <h1 style="margin:0 0 12px;font-size:26px;line-height:1.25;">Verify your email address</h1>
    <p class="muted" style="color:#475569;line-height:1.7;font-size:16px;">Enter this one-time code in SocialHub. The code expires in 10 minutes and can only be used once.</p>
    {_otp_box(otp)}
    {_button("Verify Email", f"{app_url}/verify-email")}
    """, support_email)
    return EmailContent(subject, html, text)


def forgot_password_otp(otp: str, app_url: str, support_email: str) -> EmailContent:
    subject = "Reset Your SocialHub Password"
    text = f"Use this SocialHub password reset code: {otp}. It expires in 10 minutes. Reset here: {app_url}/reset-password"
    html = _layout(subject, "Use your 6-digit code to reset your password.", f"""
    <h1 style="margin:0 0 12px;font-size:26px;line-height:1.25;">Reset your password</h1>
    <p class="muted" style="color:#475569;line-height:1.7;font-size:16px;">We received a request to reset your password. Use this single-use code within 10 minutes.</p>
    {_otp_box(otp)}
    {_button("Reset Password", f"{app_url}/reset-password")}
    <p class="muted" style="color:#64748b;font-size:13px;line-height:1.7;">If you did not request this, you can safely ignore this email.</p>
    """, support_email)
    return EmailContent(subject, html, text)


def password_reset_success(support_email: str) -> EmailContent:
    subject = "Your SocialHub Password Was Changed"
    text = f"Your SocialHub password has been updated. If this wasn't you, contact support immediately: {support_email}"
    html = _layout(subject, "Your password has been updated.", f"""
    <h1 style="margin:0 0 12px;font-size:26px;line-height:1.25;">Password changed successfully</h1>
    <p class="muted" style="color:#475569;line-height:1.7;font-size:16px;">Your password has been updated and existing sessions were signed out for your protection.</p>
    <p style="background:#fff7ed;border:1px solid #fed7aa;border-radius:14px;padding:14px;color:#9a3412;line-height:1.6;">If this wasn't you, contact support immediately at {escape(support_email)}.</p>
    """, support_email)
    return EmailContent(subject, html, text)


def login_alert(time: str, device: str, browser: str, ip: Optional[str], location: Optional[str], support_email: str) -> EmailContent:
    subject = "New login to your SocialHub account"
    rows = [("Time", time), ("Device", device), ("Browser", browser), ("IP address", ip or "Not available"), ("Location", location or "Not available")]
    text = "New SocialHub login\n" + "\n".join(f"{k}: {v}" for k, v in rows)
    html_rows = "".join(f"<tr><td style='padding:10px 0;color:#64748b'>{escape(k)}</td><td style='padding:10px 0;text-align:right;font-weight:700'>{escape(str(v))}</td></tr>" for k, v in rows)
    html = _layout(subject, "A new login was detected on your account.", f"""
    <h1 style="margin:0 0 12px;font-size:26px;line-height:1.25;">New login detected</h1>
    <p class="muted" style="color:#475569;line-height:1.7;font-size:16px;">We noticed a successful login to your SocialHub account.</p>
    <table role="presentation" width="100%" style="border-collapse:collapse;margin-top:18px;">{html_rows}</table>
    <p class="muted" style="color:#64748b;font-size:13px;line-height:1.7;">If this was you, no action is needed. If not, change your password and contact support.</p>
    """, support_email)
    return EmailContent(subject, html, text)


def security_alert(title: str, message: str, support_email: str) -> EmailContent:
    subject = "Security alert for your SocialHub account"
    text = f"{title}\n\n{message}\n\nSupport: {support_email}"
    html = _layout(subject, "Important security information for your account.", f"""
    <h1 style="margin:0 0 12px;font-size:26px;line-height:1.25;">{escape(title)}</h1>
    <p class="muted" style="color:#475569;line-height:1.7;font-size:16px;">{escape(message)}</p>
    """, support_email)
    return EmailContent(subject, html, text)