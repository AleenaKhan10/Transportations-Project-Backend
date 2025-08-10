import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from config import settings

class EmailService:
    @staticmethod
    def send_otp_email(to_email: str, otp_code: str, full_name: str) -> bool:
        """Send OTP verification email"""
        try:
            # Email configuration - using settings
            smtp_server = settings.SMTP_SERVER
            smtp_port = settings.SMTP_PORT
            sender_email = settings.SENDER_EMAIL
            sender_password = settings.SENDER_PASSWORD
            
            print(f"📧 Email Configuration:")
            print(f"   SMTP Server: {smtp_server}")
            print(f"   SMTP Port: {smtp_port}")
            print(f"   Sender Email: {sender_email}")
            print(f"   Password Value: {sender_password}")  # Temporarily showing for debug
            print(f"   Password Configured: {'Yes' if sender_password else 'No'}")
            print(f"   Sending to: {to_email}")
            
            if not sender_password:
                print(f"\n❌ NO PASSWORD CONFIGURED - MOCK EMAIL to {to_email}:")
                print(f"Your verification code is: {otp_code}")
                print(f"Code expires in 10 minutes")
                return False
            
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = "AGY Logistics - Email Verification Code"
            message["From"] = f"AGY Logistics <{sender_email}>"
            message["To"] = to_email
            
            # Create HTML content
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Email Verification</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                    .container {{ max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                    .header {{ text-align: center; margin-bottom: 30px; }}
                    .logo {{ color: #2563eb; font-size: 24px; font-weight: bold; }}
                    .otp-code {{ font-size: 32px; font-weight: bold; color: #2563eb; text-align: center; background-color: #f0f9ff; padding: 20px; border-radius: 8px; margin: 20px 0; letter-spacing: 4px; }}
                    .content {{ color: #374151; line-height: 1.6; }}
                    .footer {{ text-align: center; margin-top: 30px; color: #6b7280; font-size: 14px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <div class="logo">AGY Logistics</div>
                    </div>
                    
                    <div class="content">
                        <h2>Welcome to AGY Logistics, {full_name}!</h2>
                        <p>Thank you for registering with AGY Logistics. To complete your registration and verify your email address, please use the verification code below:</p>
                        
                        <div class="otp-code">{otp_code}</div>
                        
                        <p><strong>Important:</strong> This verification code will expire in 10 minutes for security reasons.</p>
                        
                        <p>If you didn't request this verification code, please ignore this email.</p>
                        
                        <p>Best regards,<br>
                        The AGY Logistics Team</p>
                    </div>
                    
                    <div class="footer">
                        <p>This is an automated message. Please do not reply to this email.</p>
                        <p>&copy; 2025 AGY Logistics. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Create plain text content
            text_content = f"""
            Welcome to AGY Logistics, {full_name}!
            
            Thank you for registering with AGY Logistics. To complete your registration and verify your email address, please use the verification code below:
            
            Verification Code: {otp_code}
            
            Important: This verification code will expire in 10 minutes for security reasons.
            
            If you didn't request this verification code, please ignore this email.
            
            Best regards,
            The AGY Logistics Team
            
            This is an automated message. Please do not reply to this email.
            © 2025 AGY Logistics. All rights reserved.
            """
            
            # Attach parts
            part1 = MIMEText(text_content, "plain")
            part2 = MIMEText(html_content, "html")
            message.attach(part1)
            message.attach(part2)
            
            # Send email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(message)
            
            print(f"✅ OTP email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send email to {to_email}: {str(e)}")
            print(f"FALLBACK - Mock email to {to_email}:")
            print(f"Your verification code is: {otp_code}")
            print(f"Code expires in 10 minutes")
            return False
    
    @staticmethod
    def send_welcome_email(to_email: str, full_name: str) -> bool:
        """Send welcome email after user approval"""
        # Implementation for welcome email after approval
        # This can be implemented later
        pass