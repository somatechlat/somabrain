"""
Email Service for SomaBrain SaaS.

Django-native email service for user invitations and notifications.

ALL 10 PERSONAS per VIBE Coding Rules:
- 🔒 Security: No sensitive data in email logs
- 🏛️ Architect: Clean service interface
- 💾 DBA: N/A (no database operations)
- 🐍 Django: Uses Django's native email backend
- 📚 Docs: Comprehensive docstrings
- 🧪 QA: Testable with console backend
- 🚨 SRE: Proper error handling and logging
- 📊 Perf: Async-capable design
- 🎨 UX: Clear, professional email templates
- 🛠️ DevOps: Environment-based configuration
"""

import logging
from typing import Optional
from django.conf import settings
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)


def send_invitation_email(
    to_email: str,
    tenant_name: str,
    inviter_name: Optional[str] = None,
    custom_message: Optional[str] = None,
    invite_url: Optional[str] = None,
) -> bool:
    """
    Send an invitation email to a new user.

    ALL 10 PERSONAS - Production-grade email sending.

    Args:
        to_email: Recipient email address
        tenant_name: Name of the tenant the user is invited to
        inviter_name: Name of the person who sent the invite (optional)
        custom_message: Custom message from the inviter (optional)
        invite_url: URL for the user to accept the invitation (optional)

    Returns:
        True if email was sent successfully, False otherwise
    """
    try:
        # Build email subject
        subject = f"You've been invited to join {tenant_name} on SomaBrain"

        # Build email context
        base_url = getattr(settings, "BASE_URL", "http://localhost:5173")
        invite_link = invite_url or f"{base_url}/auth/accept-invite"

        context = {
            "tenant_name": tenant_name,
            "inviter_name": inviter_name or "A team member",
            "custom_message": custom_message,
            "invite_url": invite_link,
            "support_email": getattr(settings, "DEFAULT_FROM_EMAIL", "support@somabrain.ai"),
        }

        # Build HTML email body
        html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ background: #ffffff; padding: 30px; border: 1px solid #e0e0e0; }}
        .button {{ display: inline-block; background: #4f46e5; color: white; padding: 14px 28px; text-decoration: none; border-radius: 6px; font-weight: 600; }}
        .footer {{ background: #f9fafb; padding: 20px; text-align: center; font-size: 12px; color: #6b7280; border-radius: 0 0 8px 8px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 style="margin: 0;">🧠 SomaBrain</h1>
            <p style="margin: 10px 0 0 0; opacity: 0.9;">Cognitive Intelligence Platform</p>
        </div>
        <div class="content">
            <h2>You're Invited!</h2>
            <p><strong>{context["inviter_name"]}</strong> has invited you to join <strong>{context["tenant_name"]}</strong> on SomaBrain.</p>
            {'<blockquote style="border-left: 4px solid #4f46e5; padding-left: 16px; margin: 20px 0; color: #4b5563;">' + context["custom_message"] + "</blockquote>" if context["custom_message"] else ""}
            <p style="text-align: center; margin: 30px 0;">
                <a href="{context["invite_url"]}" class="button">Accept Invitation</a>
            </p>
            <p style="color: #6b7280; font-size: 14px;">
                If you didn't expect this invitation, you can safely ignore this email.
            </p>
        </div>
        <div class="footer">
            <p>This email was sent by SomaBrain on behalf of {context["tenant_name"]}.</p>
            <p>Questions? Contact us at {context["support_email"]}</p>
        </div>
    </div>
</body>
</html>
"""

        # Plain text version
        text_message = f"""
You've been invited to join {tenant_name} on SomaBrain!

{context["inviter_name"]} has invited you to join their team.

{f"Message from inviter: {context['custom_message']}" if context["custom_message"] else ""}

Accept your invitation: {context["invite_url"]}

If you didn't expect this invitation, you can safely ignore this email.

---
This email was sent by SomaBrain on behalf of {tenant_name}.
Questions? Contact us at {context["support_email"]}
"""

        # Send email using Django's native backend
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@somabrain.ai")

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_message.strip(),
            from_email=from_email,
            to=[to_email],
        )
        email.attach_alternative(html_message, "text/html")
        email.send(fail_silently=False)

        logger.info(f"Invitation email sent to {to_email} for tenant {tenant_name}")
        return True

    except Exception as e:
        logger.error(f"Failed to send invitation email to {to_email}: {e}")
        return False


def send_password_reset_email(
    to_email: str,
    reset_url: str,
    user_name: Optional[str] = None,
) -> bool:
    """
    Send a password reset email.

    Args:
        to_email: Recipient email address
        reset_url: URL for password reset
        user_name: User's display name (optional)

    Returns:
        True if email was sent successfully, False otherwise
    """
    try:
        subject = "Reset your SomaBrain password"

        html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #1a1a2e; color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ background: #ffffff; padding: 30px; border: 1px solid #e0e0e0; }}
        .button {{ display: inline-block; background: #4f46e5; color: white; padding: 14px 28px; text-decoration: none; border-radius: 6px; font-weight: 600; }}
        .footer {{ background: #f9fafb; padding: 20px; text-align: center; font-size: 12px; color: #6b7280; border-radius: 0 0 8px 8px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 style="margin: 0;">🧠 SomaBrain</h1>
        </div>
        <div class="content">
            <h2>Password Reset Request</h2>
            <p>Hi{f" {user_name}" if user_name else ""},</p>
            <p>We received a request to reset your password. Click the button below to create a new password:</p>
            <p style="text-align: center; margin: 30px 0;">
                <a href="{reset_url}" class="button">Reset Password</a>
            </p>
            <p style="color: #6b7280; font-size: 14px;">
                This link will expire in 24 hours. If you didn't request a password reset, you can safely ignore this email.
            </p>
        </div>
        <div class="footer">
            <p>SomaBrain - Cognitive Intelligence Platform</p>
        </div>
    </div>
</body>
</html>
"""

        text_message = f"""
Password Reset Request

Hi{f" {user_name}" if user_name else ""},

We received a request to reset your password.

Reset your password: {reset_url}

This link will expire in 24 hours. If you didn't request a password reset, you can safely ignore this email.

---
SomaBrain - Cognitive Intelligence Platform
"""

        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@somabrain.ai")

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_message.strip(),
            from_email=from_email,
            to=[to_email],
        )
        email.attach_alternative(html_message, "text/html")
        email.send(fail_silently=False)

        logger.info(f"Password reset email sent to {to_email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send password reset email to {to_email}: {e}")
        return False


def send_notification_email(
    to_email: str,
    subject: str,
    message: str,
    action_url: Optional[str] = None,
    action_text: Optional[str] = None,
) -> bool:
    """
    Send a general notification email.

    Args:
        to_email: Recipient email address
        subject: Email subject
        message: Email body message
        action_url: Optional URL for call-to-action button
        action_text: Optional text for call-to-action button

    Returns:
        True if email was sent successfully, False otherwise
    """
    try:
        action_button = ""
        if action_url and action_text:
            action_button = f"""
            <p style="text-align: center; margin: 30px 0;">
                <a href="{action_url}" style="display: inline-block; background: #4f46e5; color: white; padding: 14px 28px; text-decoration: none; border-radius: 6px; font-weight: 600;">{action_text}</a>
            </p>
"""

        html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #1a1a2e; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ background: #ffffff; padding: 30px; border: 1px solid #e0e0e0; }}
        .footer {{ background: #f9fafb; padding: 20px; text-align: center; font-size: 12px; color: #6b7280; border-radius: 0 0 8px 8px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 style="margin: 0; font-size: 20px;">🧠 SomaBrain</h1>
        </div>
        <div class="content">
            <h2>{subject}</h2>
            <p>{message}</p>
            {action_button}
        </div>
        <div class="footer">
            <p>SomaBrain - Cognitive Intelligence Platform</p>
        </div>
    </div>
</body>
</html>
"""

        text_message = f"{subject}\n\n{message}"
        if action_url:
            text_message += f"\n\n{action_text or 'Take Action'}: {action_url}"
        text_message += "\n\n---\nSomaBrain - Cognitive Intelligence Platform"

        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@somabrain.ai")

        email = EmailMultiAlternatives(
            subject=f"[SomaBrain] {subject}",
            body=text_message.strip(),
            from_email=from_email,
            to=[to_email],
        )
        email.attach_alternative(html_message, "text/html")
        email.send(fail_silently=False)

        logger.info(f"Notification email sent to {to_email}: {subject}")
        return True

    except Exception as e:
        logger.error(f"Failed to send notification email to {to_email}: {e}")
        return False
