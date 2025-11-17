import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import logging
from flask import current_app

logger = logging.getLogger(__name__)

def log_console_email(email, otp_code):
    """Log OTP when console fallback is enabled."""
    logger.warning("Email fallback active - OTP for %s is %s", email, otp_code)
    print(f"[DEV OTP] Send code {otp_code} to {email}")

def send_otp_email(email, otp_code):
    """Send OTP verification email with beautiful HTML template"""
    try:
        sender_email = current_app.config['EMAIL_USER']
        sender_password = current_app.config['EMAIL_PASSWORD']
        smtp_server = current_app.config['EMAIL_SMTP_SERVER']
        smtp_port = current_app.config['EMAIL_SMTP_PORT']
        allow_console = current_app.config.get('EMAIL_ALLOW_CONSOLE', False)
        
        if not all([sender_email, sender_password, smtp_server]):
            if allow_console:
                log_console_email(email, otp_code)
                return True
            logger.error("Email configuration missing")
            return False
        
        # Create message
        message = MIMEMultipart("alternative")
        message["Subject"] = "SmartCart OTP Verification Code"
        message["From"] = sender_email
        message["To"] = email
        
        # Beautiful HTML template
        html = f"""
        <html>
            <head>
                <style>
                    * {{
                        margin: 0;
                        padding: 0;
                        box-sizing: border-box;
                    }}
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                        background-image: linear-gradient(120deg, #f6d365 0%, #fda085 100%);
                        padding: 20px;
                        min-height: 100vh;
                    }}
                    .container {{
                        max-width: 500px;
                        margin: 0 auto;
                        background: white;
                        border-radius: 12px;
                        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
                        overflow: hidden;
                    }}
                    .header {{
                        background-image: linear-gradient(120deg, #f6d365 0%, #fda085 100%);
                        color: white;
                        padding: 30px 20px;
                        text-align: center;
                    }}
                    .header h1 {{
                        font-size: 28px;
                        margin-bottom: 10px;
                        font-weight: 700;
                    }}
                    .header p {{
                        font-size: 14px;
                        opacity: 0.9;
                    }}
                    .content {{
                        padding: 40px 30px;
                        text-align: center;
                    }}
                    .content p {{
                        color: #555;
                        font-size: 15px;
                        line-height: 1.6;
                        margin-bottom: 30px;
                    }}
                    .otp-box {{
                        background-image: linear-gradient(120deg, #f6d365 0%, #fda085 100%);
                        color: white;
                        padding: 25px;
                        border-radius: 8px;
                        margin-bottom: 30px;
                        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
                    }}
                    .otp-code {{
                        font-size: 42px;
                        font-weight: 800;
                        letter-spacing: 8px;
                        font-family: 'Courier New', monospace;
                        margin: 10px 0;
                        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
                    }}
                    .otp-note {{
                        font-size: 12px;
                        margin-top: 15px;
                        opacity: 0.9;
                    }}
                    .warning {{
                        background: #fff3cd;
                        color: #856404;
                        padding: 15px;
                        border-radius: 6px;
                        font-size: 13px;
                        margin-bottom: 20px;
                        border-left: 4px solid #ffc107;
                    }}
                    .footer {{
                        background: #f8f9fa;
                        padding: 20px;
                        text-align: center;
                        border-top: 1px solid #ddd;
                    }}
                    .footer p {{
                        color: #999;
                        font-size: 12px;
                        margin: 0;
                    }}
                    .footer a {{
                        color: #667eea;
                        text-decoration: none;
                    }}
                    .footer a:hover {{
                        text-decoration: underline;
                    }}
                    .icon {{
                        font-size: 50px;
                        margin-bottom: 15px;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="content">
                        <p>Welcome! Your one-time password for SmartCart login is ready:</p>
                        
                        <div class="otp-box">
                            <div class="otp-code">{otp_code}</div>
                            <div class="otp-note">Valid for 10 minutes</div>
                        </div>
                        
                        
                        <p style="color: #999; font-size: 13px;">
                            Didn't request this code? 
                            <a href="#" style="color: #667eea; text-decoration: none;">Report suspicious activity</a>
                        </p>
                    </div>
                    
                    <div class="footer">
                        <p>This code expires in 10 minutes</p>
                        <p>Need help? <a href="#">Contact Support</a></p>
                        <p style="margin-top: 10px; color: #ccc;">© 2024 SmartCart. All rights reserved.</p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        # Attach HTML
        message.attach(MIMEText(html, "html"))
        
        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, email, message.as_string())
        
        logger.info(f"OTP email sent successfully to {email}")
        return True
        
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP authentication failed. Check EMAIL_USER and EMAIL_PASSWORD")
        if current_app.config.get('EMAIL_ALLOW_CONSOLE', False):
            log_console_email(email, otp_code)
            return True
        return False
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error occurred: {str(e)}")
        if current_app.config.get('EMAIL_ALLOW_CONSOLE', False):
            log_console_email(email, otp_code)
            return True
        return False
    except Exception as e:
        logger.error(f"Error sending OTP email: {str(e)}")
        if current_app.config.get('EMAIL_ALLOW_CONSOLE', False):
            log_console_email(email, otp_code)
            return True
        return False
