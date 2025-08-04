"""
Email service for sending notifications
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from app.core.config import settings

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
            
            # Add HTML version
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            print(f"Failed to send email: {e}")
            return False
    
    def send_role_change_email(self, user_email: str, user_name: str, old_role: str, new_role: str, changed_by: str):
        """Send role change notification email"""
        subject = "Your Role Has Been Updated - Msafiri"
        
        html_content = f"""
        <html>
        <body>
            <h2>Role Update Notification</h2>
            <p>Hello {user_name},</p>
            
            <p>Your role in the Msafiri Visitor System has been updated:</p>
            
            <ul>
                <li><strong>Previous Role:</strong> {old_role}</li>
                <li><strong>New Role:</strong> {new_role}</li>
                <li><strong>Updated By:</strong> {changed_by}</li>
            </ul>
            
            <p>This change may affect your access permissions in the system.</p>
            
            <p>If you have any questions, please contact your administrator.</p>
            
            <p>Best regards,<br>
            Msafiri Team</p>
        </body>
        </html>
        """
        
        text_content = f"""
        Role Update Notification
        
        Hello {user_name},
        
        Your role in the Msafiri Visitor System has been updated:
        
        Previous Role: {old_role}
        New Role: {new_role}
        Updated By: {changed_by}
        
        This change may affect your access permissions in the system.
        
        If you have any questions, please contact your administrator.
        
        Best regards,
        Msafiri Team
        """
        
        return self.send_email([user_email], subject, html_content, text_content)

email_service = EmailService()