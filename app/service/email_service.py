
import logging
from app.config.settings import settings

logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    def send_password_reset_email(recipient_email: str, reset_token: str, user_name: str = "User"):
        """
        Simulates sending a password reset email by logging to the console.
        """
        reset_link = f"http://localhost:3000/reset-password?token={reset_token}"
        
        logger.info("-" * 60)
        logger.info("📧 EMAIL SENDING SIMULATION")
        logger.info(f"To: {recipient_email}")
        logger.info("Subject: Password Reset Request")
        logger.info(f"Hi {user_name},")
        logger.info(f"Use this link to reset your password: {reset_link}")
        logger.info("-" * 60)
        
        # In a real implementation, you would use smtplib or an email provider API here.
        return True

email_service = EmailService()
