import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
from typing import List, Optional
from app.core.config import settings

class EmailService:
    def __init__(self):
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.username = settings.SMTP_USERNAME
        self.password = settings.SMTP_PASSWORD
        self.from_email = settings.FROM_EMAIL
        self.from_name = settings.FROM_NAME

    def send_email(
        self,
        to_emails: List[str],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        attachments: Optional[List[str]] = None
    ) -> bool:
        """Send email using Microsoft Outlook SMTP"""
        
        if not settings.SEND_EMAILS:
            print(f"Email sending disabled. Would send: {subject} to {to_emails}")
            return True

        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = ", ".join(to_emails)

            # Add text content
            if text_content:
                text_part = MIMEText(text_content, "plain")
                message.attach(text_part)

            # Add HTML content
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)

            # Add attachments if any
            if attachments:
                for file_path in attachments:
                    if os.path.exists(file_path):
                        with open(file_path, "rb") as attachment:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(attachment.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                'Content-Disposition',
                                f'attachment; filename= {os.path.basename(file_path)}'
                            )
                            message.attach(part)

            # Create secure connection and send email
            context = ssl.create_default_context()
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.username, self.password)
                server.sendmail(self.from_email, to_emails, message.as_string())

            print(f"Email sent successfully to {to_emails}")
            return True

        except Exception as e:
            print(f"Failed to send email: {str(e)}")
            return False

    def send_notification_email(self, to_email: str, user_name: str, title: str, message: str, action_url: str = None, priority: str = "medium", data: dict = None):
        """Send notification email with standard template"""
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{title}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .logo {{ color: #2563eb; font-size: 24px; font-weight: bold; }}
                .title {{ color: #1f2937; font-size: 20px; margin: 20px 0; }}
                .message {{ color: #4b5563; line-height: 1.6; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; color: #6b7280; font-size: 14px; }}
                .button {{ display: inline-block; background-color: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">

                
                <h2 class="title">{title}</h2>
                
                <div class="message">
                    {message}
                </div>
                
                {self._format_data_section(data) if data else ""}
                
                <div class="footer">
                    <p>This is an automated message from Kenya HR Portal - Msafiri System</p>
                    <p>Médecins Sans Frontières (MSF) - Kenya</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        {title}
        
        {message}
        
        {self._format_data_text(data) if data else ""}
        
        ---
        This is an automated message from Kenya HR Portal - Msafiri System
        Médecins Sans Frontières (MSF) - Kenya
        """
        
        return self.send_email([to_email], title, html_content, text_content)

    def _format_data_section(self, data: dict) -> str:
        """Format data dictionary as HTML"""
        if not data:
            return ""
        
        html = "<div style='background-color: #f9fafb; padding: 15px; border-radius: 6px; margin: 20px 0;'>"
        html += "<h3 style='margin-top: 0; color: #374151;'>Details:</h3>"
        
        for key, value in data.items():
            if value is not None:
                formatted_key = key.replace('_', ' ').title()
                html += f"<p style='margin: 5px 0;'><strong>{formatted_key}:</strong> {value}</p>"
        
        html += "</div>"
        return html

    def _format_data_text(self, data: dict) -> str:
        """Format data dictionary as plain text"""
        if not data:
            return ""
        
        text = "\nDetails:\n"
        for key, value in data.items():
            if value is not None:
                formatted_key = key.replace('_', ' ').title()
                text += f"{formatted_key}: {value}\n"
        
        return text

    def send_invitation_email(
        self,
        email: str,
        full_name: str,
        tenant_name: str,
        token: str,
        invited_by: str
    ):
        """Send invitation email to new admin user."""
        invitation_url = f"{settings.FRONTEND_URL}/accept-invitation?token={token}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Invitation to join {tenant_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .logo {{ color: #dc2626; font-size: 24px; font-weight: bold; }}
                .title {{ color: #1f2937; font-size: 20px; margin: 20px 0; }}
                .message {{ color: #4b5563; line-height: 1.6; margin: 20px 0; }}
                .button {{ display: inline-block; background-color: #dc2626; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; color: #6b7280; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">🌍 MSF Msafiri Admin Portal</div>
                </div>
                
                <h2 class="title">You're invited to join {tenant_name}</h2>
                
                <div class="message">
                    <p>Dear {full_name},</p>
                    <p>You have been invited by {invited_by} to join the MSF Msafiri Admin Portal for {tenant_name}.</p>
                    <p>To accept this invitation and set up your account, please click the button below:</p>
                </div>
                
                <div style="text-align: center;">
                    <a href="{invitation_url}" class="button">Accept Invitation</a>
                </div>
                
                <div class="message">
                    <p><strong>Note:</strong> This invitation will expire in 7 days.</p>
                    <p>If you have any questions, please contact your administrator.</p>
                </div>
                
                <div class="footer">
                    <p>This is an automated message from MSF Msafiri Admin Portal</p>
                    <p>Médecins Sans Frontières (MSF)</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        You're invited to join {tenant_name}
        
        Dear {full_name},
        
        You have been invited by {invited_by} to join the MSF Msafiri Admin Portal for {tenant_name}.
        
        To accept this invitation and set up your account, please visit:
        {invitation_url}
        
        This invitation will expire in 7 days.
        
        If you have any questions, please contact your administrator.
        
        Best regards,
        MSF Msafiri Team
        """
        
        return self.send_email([email], f"Invitation to join {tenant_name} - MSF Msafiri Admin Portal", html_content, text_content)

    def send_role_change_notification(
        self,
        email: str,
        full_name: str,
        old_role: str,
        new_role: str,
        changed_by: str
    ):
        """Send notification email when user role is changed."""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Your role has been updated</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .logo {{ color: #dc2626; font-size: 24px; font-weight: bold; }}
                .title {{ color: #1f2937; font-size: 20px; margin: 20px 0; }}
                .message {{ color: #4b5563; line-height: 1.6; margin: 20px 0; }}
                .role-change {{ background-color: #fef3c7; padding: 15px; border-radius: 6px; margin: 20px 0; }}
                .button {{ display: inline-block; background-color: #dc2626; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; color: #6b7280; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">🌍 MSF Msafiri Admin Portal</div>
                </div>
                
                <h2 class="title">Your role has been updated</h2>
                
                <div class="message">
                    <p>Dear {full_name},</p>
                    <p>Your role in the MSF Msafiri Admin Portal has been updated by {changed_by}.</p>
                </div>
                
                <div class="role-change">
                    <p><strong>Previous Role:</strong> {old_role}</p>
                    <p><strong>New Role:</strong> {new_role}</p>
                </div>
                
                <div class="message">
                    <p>You can log in to the portal to see your updated permissions:</p>
                </div>
                
                <div style="text-align: center;">
                    <a href="{settings.FRONTEND_URL}/login" class="button">Login to Portal</a>
                </div>
                
                <div class="message">
                    <p>If you have any questions about this change, please contact your administrator.</p>
                </div>
                
                <div class="footer">
                    <p>This is an automated message from MSF Msafiri Admin Portal</p>
                    <p>Médecins Sans Frontières (MSF)</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Your role has been updated
        
        Dear {full_name},
        
        Your role in the MSF Msafiri Admin Portal has been updated by {changed_by}.
        
        Previous Role: {old_role}
        New Role: {new_role}
        
        You can log in to the portal to see your updated permissions:
        {settings.FRONTEND_URL}/login
        
        If you have any questions about this change, please contact your administrator.
        
        Best regards,
        MSF Msafiri Team
        """
        
        return self.send_email([email], "Your role has been updated - MSF Msafiri Admin Portal", html_content, text_content)

# Global email service instance
email_service = EmailService()