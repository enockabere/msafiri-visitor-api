"""
Enhanced email service for sending notifications
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional, Dict, Any
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class EmailService:
    
    def __init__(self):
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.FROM_EMAIL
    
    def send_email(
        self,
        to_emails: List[str],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """Send email notification"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = ', '.join(to_emails)
            
            # Add text version
            if text_content:
                text_part = MIMEText(text_content, 'plain')
                msg.attach(text_part)
            else:
                # Create simple text version from HTML if not provided
                import re
                text_content = re.sub(r'<[^>]+>', '', html_content)
                text_part = MIMEText(text_content, 'plain')
                msg.attach(text_part)
            
            # Add HTML version
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_emails}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_emails}: {e}")
            return False
    
    def send_notification_email(
        self, 
        to_email: str, 
        user_name: str, 
        title: str, 
        message: str, 
        action_url: Optional[str] = None,
        priority: str = "medium"
    ) -> bool:
        """Send a notification email"""
        
        # Determine priority styling
        priority_colors = {
            "low": "#28a745",
            "medium": "#007bff", 
            "high": "#fd7e14",
            "urgent": "#dc3545"
        }
        priority_color = priority_colors.get(priority.lower(), "#007bff")
        
        subject = f"[Msafiri] {title}"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="border-left: 4px solid {priority_color}; padding-left: 20px; margin-bottom: 20px;">
                <h2 style="color: {priority_color}; margin: 0;">{title}</h2>
                <span style="background: {priority_color}; color: white; padding: 2px 8px; border-radius: 3px; font-size: 12px; text-transform: uppercase;">
                    {priority} Priority
                </span>
            </div>
            
            <p>Hello {user_name},</p>
            
            <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                {message}
            </div>
            
            {f'<p><a href="{action_url}" style="background: {priority_color}; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Take Action</a></p>' if action_url else ''}
            
            <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
            
            <p style="color: #666; font-size: 14px;">
                This is an automated notification from the Msafiri Visitor System.<br>
                If you have any questions, please contact your administrator.
            </p>
            
            <p style="color: #666; font-size: 12px;">
                Best regards,<br>
                Msafiri Team
            </p>
        </body>
        </html>
        """
        
        return self.send_email([to_email], subject, html_content)
    
    def send_welcome_email(self, user_email: str, user_name: str, role: str, tenant_name: str) -> bool:
        """Send welcome email to new users"""
        subject = "Welcome to Msafiri Visitor System!"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #007bff;">Welcome to Msafiri!</h1>
            </div>
            
            <p>Hello {user_name},</p>
            
            <p>Welcome to the Msafiri Visitor System! Your account has been successfully created.</p>
            
            <div style="background: #e3f2fd; padding: 20px; border-radius: 5px; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #1976d2;">Your Account Details:</h3>
                <ul>
                    <li><strong>Name:</strong> {user_name}</li>
                    <li><strong>Email:</strong> {user_email}</li>
                    <li><strong>Role:</strong> {role}</li>
                    <li><strong>Organization:</strong> {tenant_name}</li>
                </ul>
            </div>
            
            <p>You can now access the system using your credentials. If you have any questions or need assistance, please don't hesitate to contact your administrator.</p>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{settings.FRONTEND_URL}" style="background: #007bff; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px;">
                    Access Msafiri System
                </a>
            </div>
            
            <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
            
            <p style="color: #666; font-size: 14px;">
                This is an automated message from the Msafiri Visitor System.<br>
                If you received this email in error, please contact our support team.
            </p>
            
            <p style="color: #666; font-size: 12px;">
                Best regards,<br>
                Msafiri Team
            </p>
        </body>
        </html>
        """
        
        return self.send_email([user_email], subject, html_content)
    
    def send_tenant_notification_email(
        self, 
        to_emails: List[str], 
        title: str, 
        message: str, 
        tenant_name: str,
        action_type: str = "created"  # created, activated, deactivated
    ) -> bool:
        """Send tenant-related notification emails"""
        subject = f"[Msafiri] Tenant {action_type.title()}: {tenant_name}"
        
        action_colors = {
            "created": "#28a745",
            "activated": "#007bff",
            "deactivated": "#dc3545"
        }
        color = action_colors.get(action_type, "#007bff")
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="border-left: 4px solid {color}; padding-left: 20px; margin-bottom: 20px;">
                <h2 style="color: {color}; margin: 0;">Tenant {action_type.title()}</h2>
            </div>
            
            <p>Dear Administrator,</p>
            
            <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3 style="margin-top: 0;">Tenant: {tenant_name}</h3>
                <p>{message}</p>
            </div>
            
            <p>Please review the tenant management dashboard for more details.</p>
            
            <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
            
            <p style="color: #666; font-size: 14px;">
                This is an automated notification from the Msafiri Visitor System.<br>
                If you have any questions, please contact the system administrator.
            </p>
            
            <p style="color: #666; font-size: 12px;">
                Best regards,<br>
                Msafiri Team
            </p>
        </body>
        </html>
        """
        
        return self.send_email(to_emails, subject, html_content)

# Global email service instance
email_service = EmailService()