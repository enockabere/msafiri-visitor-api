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
        attachments: Optional[List[str]] = None,
        cc_emails: Optional[List[str]] = None
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
            
            # Add CC if provided
            if cc_emails:
                message["Cc"] = ", ".join(cc_emails)

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
                
                # Include CC recipients in the actual recipient list
                all_recipients = to_emails + (cc_emails or [])
                server.sendmail(self.from_email, all_recipients, message.as_string())

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
        invited_by: str,
        role: str = None
    ):
        """Send invitation email to new admin user."""
        invitation_url = f"{settings.FRONTEND_URL}/accept-invitation?token={token}"
        
        print(f"\n📧 INVITATION EMAIL DEBUG:")
        print(f"📧 Frontend URL: {settings.FRONTEND_URL}")
        print(f"📧 Full invitation URL: {invitation_url}")
        print(f"📧 Token: {token[:10]}...")
        print(f"📧 Recipient: {email}")
        print(f"📧 " + "="*50)
        
        # Format role for display
        role_display = ""
        if role:
            role_map = {
                "mt_admin": "MT Administrator",
                "hr_admin": "HR Administrator", 
                "event_admin": "Event Administrator",
                "finance_admin": "Finance Administrator",
                "staff": "Staff",
                "guest": "Guest"
            }
            role_display = role_map.get(role.lower(), role.replace('_', ' ').title())
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Invitation to join {tenant_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .title {{ color: #1f2937; font-size: 20px; margin: 20px 0; }}
                .message {{ color: #4b5563; line-height: 1.6; margin: 20px 0; }}
                .button {{ display: inline-block; background-color: #dc2626; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
                .role-info {{ background-color: #f3f4f6; padding: 15px; border-radius: 6px; margin: 20px 0; border-left: 4px solid #dc2626; }}
                .footer {{ text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; color: #6b7280; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2 class="title">You're invited to join {tenant_name}</h2>
                
                <div class="message">
                    <p>Dear {full_name},</p>
                    <p>You have been invited by {invited_by} to join the MSF Msafiri Admin Portal for {tenant_name}.</p>
                    {f'<div class="role-info"><p><strong>Your assigned role:</strong> {role_display}</p></div>' if role_display else ''}
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
        
        {f'Your assigned role: {role_display}' if role_display else ''}
        
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

    def send_password_reset_email(
        self,
        to_email: str,
        user_name: str,
        reset_url: str,
        expires_in_hours: int = 1
    ):
        """Send password reset email to super admin users."""
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Password Reset Request</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .logo {{ color: #dc2626; font-size: 24px; font-weight: bold; }}
                .title {{ color: #1f2937; font-size: 20px; margin: 20px 0; }}
                .message {{ color: #4b5563; line-height: 1.6; margin: 20px 0; }}
                .button {{ display: inline-block; background-color: #dc2626; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
                .warning {{ background-color: #fef3c7; padding: 15px; border-radius: 6px; margin: 20px 0; border-left: 4px solid #f59e0b; }}
                .footer {{ text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; color: #6b7280; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2 class="title">Password Reset Request</h2>
                
                <div class="message">
                    <p>Dear {user_name},</p>
                    <p>We received a request to reset your password for the MSF Msafiri Admin Portal.</p>
                    <p>To reset your password, please click the button below:</p>
                </div>
                
                <div style="text-align: center;">
                    <a href="{reset_url}" class="button" style="color: white;">Reset Password</a>
                </div>
                
                <div class="warning">
                    <p><strong>⚠️ Important Security Information:</strong></p>
                    <ul>
                        <li>This link will expire in {expires_in_hours} hour(s)</li>
                        <li>If you didn't request this reset, please ignore this email</li>
                        <li>For security, this link can only be used once</li>
                        <li>Never share this link with anyone</li>
                    </ul>
                </div>
                
                <div class="message">
                    <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; background-color: #f3f4f6; padding: 10px; border-radius: 4px; font-family: monospace; font-size: 12px;">{reset_url}</p>
                </div>
                
                <div class="footer">
                    <p>This is an automated security message from MSF Msafiri Admin Portal</p>
                    <p>Médecins Sans Frontières (MSF)</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Password Reset Request - MSF Msafiri Admin Portal
        
        Dear {user_name},
        
        We received a request to reset your password for the MSF Msafiri Admin Portal.
        
        To reset your password, please visit the following link:
        {reset_url}
        
        IMPORTANT SECURITY INFORMATION:
        - This link will expire in {expires_in_hours} hour(s)
        - If you didn't request this reset, please ignore this email
        - For security, this link can only be used once
        - Never share this link with anyone
        
        If you have any questions, please contact your system administrator.
        
        Best regards,
        MSF Msafiri Team
        """
        
        return self.send_email([to_email], "Password Reset Request - MSF Msafiri Admin Portal", html_content, text_content)

    def send_certificate_notification_email(
        self,
        to_email: str,
        participant_name: str,
        event_title: str,
        certificate_url: str
    ):
        """Send certificate availability notification email."""
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Your Event Certificate is Ready</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; margin-bottom: 30px; background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%); padding: 30px; border-radius: 10px; }}
                .logo {{ color: white; font-size: 28px; font-weight: bold; }}
                .title {{ color: #1f2937; font-size: 22px; margin: 20px 0; text-align: center; }}
                .message {{ color: #4b5563; line-height: 1.8; margin: 20px 0; }}
                .button {{ display: inline-block; background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%); color: white; padding: 14px 32px; text-decoration: none; border-radius: 8px; margin: 20px 0; font-weight: bold; box-shadow: 0 4px 12px rgba(220, 38, 38, 0.3); }}
                .certificate-icon {{ font-size: 64px; text-align: center; margin: 20px 0; }}
                .info-box {{ background-color: #fef3c7; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #f59e0b; }}
                .footer {{ text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; color: #6b7280; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">🎓 MSF Msafiri</div>
                </div>
                
                <div class="certificate-icon">🏆</div>
                
                <h2 class="title">Your Certificate is Ready!</h2>
                
                <div class="message">
                    <p>Dear {participant_name},</p>
                    <p>Congratulations! Your certificate for <strong>{event_title}</strong> is now available.</p>
                    <p>You can view and download your certificate from the MSF Msafiri mobile app.</p>
                </div>
                
                <div style="text-align: center;">
                    <a href="{certificate_url}" class="button" style="color: white;">View Certificate</a>
                </div>
                
                <div class="info-box">
                    <p><strong>📱 How to access your certificate:</strong></p>
                    <ul style="margin: 10px 0; padding-left: 20px;">
                        <li>Open the MSF Msafiri mobile app</li>
                        <li>Go to your event details</li>
                        <li>Navigate to the "Event Files" section</li>
                        <li>Your certificate will be available for download</li>
                    </ul>
                </div>
                
                <div class="message">
                    <p>If you have any questions, please contact your event coordinator.</p>
                    <p>Thank you for your participation!</p>
                </div>
                
                <div class="footer">
                    <p>This is an automated message from MSF Msafiri</p>
                    <p>Médecins Sans Frontières (MSF) - Kenya</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Your Certificate is Ready! - MSF Msafiri
        
        Dear {participant_name},
        
        Congratulations! Your certificate for {event_title} is now available.
        
        You can view and download your certificate from the MSF Msafiri mobile app.
        
        View your certificate: {certificate_url}
        
        How to access your certificate:
        1. Open the MSF Msafiri mobile app
        2. Go to your event details
        3. Navigate to the "Event Files" section
        4. Your certificate will be available for download
        
        If you have any questions, please contact your event coordinator.
        
        Thank you for your participation!
        
        Best regards,
        MSF Msafiri Team
        """
        
        return self.send_email([to_email], f"Your Certificate is Ready - {event_title}", html_content, text_content)

    def send_password_reset_otp_email(
        self,
        to_email: str,
        user_name: str,
        otp: str,
        expires_in_minutes: int = 10
    ):
        """Send password reset OTP email to non-MSF users."""
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Password Reset OTP</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .title {{ color: #1f2937; font-size: 20px; margin: 20px 0; }}
                .message {{ color: #4b5563; line-height: 1.6; margin: 20px 0; }}
                .otp-box {{ background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%); color: white; padding: 20px; border-radius: 8px; text-align: center; margin: 30px 0; }}
                .otp-code {{ font-size: 36px; font-weight: bold; letter-spacing: 8px; margin: 10px 0; }}
                .warning {{ background-color: #fef3c7; padding: 15px; border-radius: 6px; margin: 20px 0; border-left: 4px solid #f59e0b; }}
                .footer {{ text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; color: #6b7280; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2 class="title">Password Reset OTP</h2>
                
                <div class="message">
                    <p>Dear {user_name},</p>
                    <p>We received a request to reset your password for the MSF Msafiri app.</p>
                    <p>Please use the following One-Time Password (OTP) to reset your password:</p>
                </div>
                
                <div class="otp-box">
                    <p style="margin: 0; font-size: 14px;">Your OTP Code</p>
                    <div class="otp-code">{otp}</div>
                    <p style="margin: 0; font-size: 12px;">Valid for {expires_in_minutes} minutes</p>
                </div>
                
                <div class="warning">
                    <p><strong>⚠️ Important Security Information:</strong></p>
                    <ul>
                        <li>This OTP will expire in {expires_in_minutes} minutes</li>
                        <li>If you didn't request this reset, please ignore this email</li>
                        <li>Never share this OTP with anyone</li>
                        <li>MSF staff will never ask for your OTP</li>
                    </ul>
                </div>
                
                <div class="footer">
                    <p>This is an automated security message from MSF Msafiri</p>
                    <p>Médecins Sans Frontières (MSF) - Kenya</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Password Reset OTP - MSF Msafiri
        
        Dear {user_name},
        
        We received a request to reset your password for the MSF Msafiri app.
        
        Your One-Time Password (OTP): {otp}
        
        This OTP is valid for {expires_in_minutes} minutes.
        
        IMPORTANT SECURITY INFORMATION:
        - This OTP will expire in {expires_in_minutes} minutes
        - If you didn't request this reset, please ignore this email
        - Never share this OTP with anyone
        - MSF staff will never ask for your OTP
        
        Best regards,
        MSF Msafiri Team
        """
        
        return self.send_email([to_email], "Password Reset OTP - MSF Msafiri", html_content, text_content)

    async def send_account_creation_otp_email(
        self,
        to_email: str,
        recipient_name: str,
        otp_code: str
    ):
        """Send account creation OTP email to selected participants."""
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Create Your MSF Msafiri Account</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .title {{ color: #1f2937; font-size: 20px; margin: 20px 0; }}
                .message {{ color: #4b5563; line-height: 1.6; margin: 20px 0; }}
                .otp-box {{ background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%); color: white; padding: 20px; border-radius: 8px; text-align: center; margin: 30px 0; }}
                .otp-code {{ font-size: 36px; font-weight: bold; letter-spacing: 8px; margin: 10px 0; }}
                .footer {{ text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; color: #6b7280; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2 class="title">Create Your MSF Msafiri Account</h2>
                
                <div class="message">
                    <p>Dear {recipient_name},</p>
                    <p>Welcome! You have been selected to attend an MSF event.</p>
                    <p>Please use the following One-Time Password (OTP) to create your account:</p>
                </div>
                
                <div class="otp-box">
                    <p style="margin: 0; font-size: 14px;">Your OTP Code</p>
                    <div class="otp-code">{otp_code}</div>
                    <p style="margin: 0; font-size: 12px;">Valid for 10 minutes</p>
                </div>
                
                <div class="message">
                    <p>Enter this OTP in the MSF Msafiri app to complete your account creation.</p>
                </div>
                
                <div class="footer">
                    <p>This is an automated message from MSF Msafiri</p>
                    <p>Médecins Sans Frontières (MSF) - Kenya</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email([to_email], "Create Your MSF Msafiri Account", html_content)

# Global email service instance
email_service = EmailService()
