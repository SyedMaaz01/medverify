"""Email service for sending verification, password reset, and notification emails."""
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import aiosmtplib

from .config import (
    EMAIL_FROM,
    EMAIL_FROM_NAME,
    FRONTEND_URL,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USE_TLS,
    SMTP_USERNAME,
)


class EmailService:
    """Service for sending emails via SMTP."""

    def __init__(
        self,
        host: str = SMTP_HOST,
        port: int = SMTP_PORT,
        username: Optional[str] = SMTP_USERNAME,
        password: Optional[str] = SMTP_PASSWORD,
        use_tls: bool = SMTP_USE_TLS,
        from_email: str = EMAIL_FROM,
        from_name: str = EMAIL_FROM_NAME,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.from_email = from_email
        self.from_name = from_name

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> bool:
        """Send an email."""
        if not self.username or not self.password:
            # Log but don't fail in development
            print(f"EMAIL (dev mode): To={to_email}, Subject={subject}")
            return True

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{self.from_name} <{self.from_email}>"
        message["To"] = to_email

        if text_content:
            message.attach(MIMEText(text_content, "plain"))
        message.attach(MIMEText(html_content, "html"))

        try:
            await aiosmtplib.send(
                message,
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                use_tls=self.use_tls,
            )
            return True
        except Exception as e:
            print(f"Failed to send email: {e}")
            return False

    async def send_verification_email(
        self,
        to_email: str,
        verification_token: str,
        user_name: str,
    ) -> bool:
        """Send email verification link."""
        verification_url = f"{FRONTEND_URL}/verify-email?token={verification_token}"

        subject = "Verify your MedVerify account"
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2563eb;">Welcome to MedVerify, {user_name}!</h2>
                <p>Thank you for registering. Please verify your email address by clicking the button below:</p>
                <p style="text-align: center; margin: 30px 0;">
                    <a href="{verification_url}"
                       style="background-color: #2563eb; color: white; padding: 14px 28px;
                              text-decoration: none; border-radius: 6px; display: inline-block;">
                        Verify Email Address
                    </a>
                </p>
                <p>Or copy this link into your browser:</p>
                <p style="word-break: break-all; color: #666; font-size: 14px;">
                    {verification_url}
                </p>
                <p>This link will expire in 24 hours.</p>
                <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
                <p style="color: #999; font-size: 12px;">
                    If you didn't create an account, please ignore this email.
                </p>
            </div>
        </body>
        </html>
        """
        text_content = f"""
        Welcome to MedVerify, {user_name}!

        Please verify your email: {verification_url}

        This link expires in 24 hours.
        """
        return await self.send_email(to_email, subject, html_content, text_content)

    async def send_password_reset_email(
        self,
        to_email: str,
        reset_token: str,
        user_name: str,
    ) -> bool:
        """Send password reset link."""
        reset_url = f"{FRONTEND_URL}/reset-password?token={reset_token}"

        subject = "Reset your MedVerify password"
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2563eb;">Password Reset Request</h2>
                <p>Hi {user_name},</p>
                <p>We received a request to reset your password. Click the button below to create a new password:</p>
                <p style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}"
                       style="background-color: #dc2626; color: white; padding: 14px 28px;
                              text-decoration: none; border-radius: 6px; display: inline-block;">
                        Reset Password
                    </a>
                </p>
                <p>Or copy this link:</p>
                <p style="word-break: break-all; color: #666; font-size: 14px;">
                    {reset_url}
                </p>
                <p>This link will expire in 1 hour.</p>
                <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
                <p style="color: #999; font-size: 12px;">
                    If you didn't request this, please ignore this email or contact support.
                </p>
            </div>
        </body>
        </html>
        """
        text_content = f"""
        Password Reset Request for {user_name}

        Reset your password: {reset_url}

        This link expires in 1 hour.
        """
        return await self.send_email(to_email, subject, html_content, text_content)

    async def send_2fa_setup_email(
        self,
        to_email: str,
        user_name: str,
        backup_codes: list[str],
    ) -> bool:
        """Send 2FA setup confirmation with backup codes."""
        subject = "Two-Factor Authentication Enabled"
        codes_text = ", ".join(backup_codes)

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #059669;">2FA Enabled Successfully</h2>
                <p>Hi {user_name},</p>
                <p>Two-factor authentication has been enabled for your account.</p>
                <p><strong>Your backup codes (store these securely):</strong></p>
                <div style="background: #f3f4f6; padding: 15px; border-radius: 6px; font-family: monospace; word-break: break-all;">
                    {codes_text}
                </div>
                <p>Each code can only be used once. Keep these in a safe place.</p>
                <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
                <p style="color: #999; font-size: 12px;">
                    If you didn't enable 2FA, please contact support immediately.
                </p>
            </div>
        </body>
        </html>
        """
        text_content = f"""
        2FA Enabled for {user_name}

        Backup codes: {codes_text}
        """
        return await self.send_email(to_email, subject, html_content, text_content)

    async def send_batch_recall_notification(
        self,
        to_email: str,
        drug_name: str,
        batch_number: str,
        recall_reason: str,
        manufacturer_name: str,
    ) -> bool:
        """Send batch recall notification."""
        subject = f"URGENT: Batch Recall - {drug_name} (Batch: {batch_number})"

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                    <h2 style="color: #dc2626; margin: 0;">⚠️ BATCH RECALL NOTICE</h2>
                </div>
                <p><strong>Drug:</strong> {drug_name}</p>
                <p><strong>Batch Number:</strong> {batch_number}</p>
                <p><strong>Manufacturer:</strong> {manufacturer_name}</p>
                <p><strong>Reason:</strong> {recall_reason}</p>
                <p style="color: #dc2626;"><strong>Action Required:</strong> Immediately stop distribution and quarantine remaining stock.</p>
                <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
                <p style="color: #999; font-size: 12px;">
                    This is an automated notification from MedVerify.
                </p>
            </div>
        </body>
        </html>
        """
        text_content = f"""
        BATCH RECALL NOTICE

        Drug: {drug_name}
        Batch: {batch_number}
        Manufacturer: {manufacturer_name}
        Reason: {recall_reason}

        Immediately stop distribution and quarantine remaining stock.
        """
        return await self.send_email(to_email, subject, html_content, text_content)


# Singleton instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get or create the global email service."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
