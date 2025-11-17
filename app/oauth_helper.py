import random
import string
from datetime import datetime, timedelta, timezone
from flask import current_app
from app.models import db, OTP
import logging

logger = logging.getLogger(__name__)

def generate_otp():
    """Generate a 6-digit OTP code"""
    return ''.join(random.choices(string.digits, k=6))

def create_otp(email):
    """Create and store OTP for email"""
    try:
        # Delete previous OTPs for this email
        OTP.query.filter_by(email=email).delete()
        
        # Generate new OTP
        otp_code = generate_otp()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        
        otp = OTP(
            email=email,
            code=otp_code,
            expires_at=expires_at
        )
        db.session.add(otp)
        db.session.commit()
        
        return otp_code, True
    except Exception as e:
        logger.error(f"Error creating OTP: {str(e)}")
        return None, False

def verify_otp(email, otp_code):
    """Verify OTP and return (is_valid, error_message)"""
    try:
        otp = OTP.query.filter_by(email=email).order_by(OTP.created_at.desc()).first()
        
        if not otp:
            return False, "OTP not found. Request a new one."
        
        # Check if expired - ensure expires_at is timezone-aware
        expires_at = otp.expires_at
        if expires_at and expires_at.tzinfo is None:
            # Convert naive datetime to timezone-aware
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        
        if datetime.now(timezone.utc) > expires_at:
            db.session.delete(otp)
            db.session.commit()
            return False, "OTP has expired. Please request a new one."
        
        # Check attempts
        if otp.attempts >= otp.max_attempts:
            db.session.delete(otp)
            db.session.commit()
            return False, "Maximum verification attempts exceeded. Request a new OTP."
        
        # Check code
        if otp.code != otp_code:
            otp.attempts += 1
            db.session.commit()
            remaining = otp.max_attempts - otp.attempts
            return False, f"Invalid OTP. {remaining} attempts remaining."
        
        # Mark as verified
        otp.is_verified = True
        db.session.commit()
        
        return True, None
        
    except Exception as e:
        logger.error(f"Error verifying OTP: {str(e)}")
        return False, "An error occurred. Please try again."

def resend_otp(email):
    """Clear previous OTP and generate new one"""
    try:
        OTP.query.filter_by(email=email).delete()
        db.session.commit()
        
        otp_code, success = create_otp(email)
        return success, otp_code
    except Exception as e:
        logger.error(f"Error resending OTP: {str(e)}")
        return False, None