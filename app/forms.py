from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, SelectField, FloatField, IntegerField, BooleanField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length, Regexp, NumberRange, Optional
from app.models import User

class RegistrationForm(FlaskForm):
    """User registration form"""
    email = StringField('Email', validators=[
        DataRequired(),
        Email()
    ])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Register')
    
    def validate_email(self, email):
        """Check if email already exists"""
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered. Please use a different one.')

class LoginForm(FlaskForm):
    """User login form"""
    username = StringField('Username or Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class DataUploadForm(FlaskForm):
    """CSV data upload form"""
    csv_file = FileField('Upload CSV File', validators=[
        DataRequired(),
        FileAllowed(['csv', 'xlsx'], 'Only CSV and Excel files are allowed')
    ])
    
    submit = SubmitField('Upload and Process')

class ContextFilterForm(FlaskForm):
    """Form for filtering recommendations by context"""
    time_of_day = SelectField('Time of Day', choices=[
        ('', 'All Times'),
        ('morning', 'Morning (5 AM - 12 PM)'),
        ('afternoon', 'Afternoon (12 PM - 5 PM)'),
        ('evening', 'Evening (5 PM - 10 PM)'),
        ('night', 'Night (10 PM - 5 AM)')
    ])
    
    budget_segment = SelectField('Budget Segment', choices=[
        ('', 'All Budgets'),
        ('low', 'Low Budget'),
        ('medium', 'Medium Budget'),
        ('high', 'High Budget')
    ])
    
    basket_size = SelectField('Basket Size', choices=[
        ('', 'All Sizes'),
        ('small', 'Small (1-3 items)'),
        ('medium', 'Medium (4-8 items)'),
        ('large', 'Large (9+ items)')
    ])
    
    submit = SubmitField('Filter')

class OTPVerificationForm(FlaskForm):
    """OTP verification form"""
    otp_code = StringField('OTP Code', validators=[
        DataRequired(),
        Length(min=6, max=6, message='OTP must be 6 digits'),
        Regexp(r'^\d{6}$', message='OTP must contain only digits')
    ])
    submit = SubmitField('Verify OTP')

class SetupStoreForm(FlaskForm):
    """First-time login setup form"""
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=3, max=80, message='Username must be between 3 and 80 characters')
    ])
    store_name = StringField('Store Name', validators=[
        DataRequired(),
        Length(min=2, max=120, message='Store name must be between 2 and 120 characters')
    ])
    submit = SubmitField('Complete Setup')
    
    def validate_username(self, username):
        """Check if username already exists"""
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already taken. Please choose a different one.')


class ThresholdConfigForm(FlaskForm):
    """Form for configuring analytics thresholds"""
    
    # Budget Thresholds
    budget_low = FloatField('Budget Low Threshold', validators=[
        DataRequired(),
        NumberRange(min=0, message='Must be >= 0')
    ], render_kw={"placeholder": "e.g., 25.00"})
    
    budget_medium = FloatField('Budget Medium Threshold', validators=[
        DataRequired(),
        NumberRange(min=0, message='Must be >= 0')
    ], render_kw={"placeholder": "e.g., 75.00"})
    
    # Association Rules Thresholds
    min_support = FloatField('Min Support (0-1)', validators=[
        DataRequired(),
        NumberRange(min=0, max=1, message='Must be between 0 and 1')
    ], render_kw={"placeholder": "e.g., 0.05"})
    
    min_confidence = FloatField('Min Confidence (0-1)', validators=[
        DataRequired(),
        NumberRange(min=0, max=1, message='Must be between 0 and 1')
    ], render_kw={"placeholder": "e.g., 0.3"})
    
    min_lift = FloatField('Min Lift Threshold', validators=[
        DataRequired(),
        NumberRange(min=0, message='Must be >= 0')
    ], render_kw={"placeholder": "e.g., 1.0"})
    
    # Basket Size Categories
    basket_small_max = IntegerField('Small Basket Max Items', validators=[
        DataRequired(),
        NumberRange(min=1, message='Must be >= 1')
    ], render_kw={"placeholder": "e.g., 3"})
    
    basket_medium_max = IntegerField('Medium Basket Max Items', validators=[
        DataRequired(),
        NumberRange(min=1, message='Must be >= 1')
    ], render_kw={"placeholder": "e.g., 8"})
    
    # Age Group Boundaries
    age_teen_max = IntegerField('Teen Max Age', validators=[
        DataRequired(),
        NumberRange(min=1, message='Must be >= 1')
    ], render_kw={"placeholder": "e.g., 17"})
    
    age_young_adult_max = IntegerField('Young Adult Max Age', validators=[
        DataRequired(),
        NumberRange(min=1, message='Must be >= 1')
    ], render_kw={"placeholder": "e.g., 24"})
    
    age_adult_max = IntegerField('Adult Max Age', validators=[
        DataRequired(),
        NumberRange(min=1, message='Must be >= 1')
    ], render_kw={"placeholder": "e.g., 59"})
    
    # Options
    use_suggested = BooleanField('Use Suggested Thresholds (Override Above)', default=False)
    
    submit = SubmitField('Configure & Process')


class UpdateProfileForm(FlaskForm):
    """Form for updating user profile"""
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=3, max=80, message='Username must be between 3 and 80 characters')
    ])
    store_name = StringField('Store Name', validators=[
        DataRequired(),
        Length(min=2, max=120, message='Store name must be between 2 and 120 characters')
    ])
    email = StringField('Email', validators=[
        DataRequired(),
        Email()
    ], render_kw={"readonly": True, "class": "bg-gray-100"})
    submit = SubmitField('Update Profile')
    
    def validate_username(self, username):
        """Check if username is taken by another user"""
        from flask_login import current_user
        user = User.query.filter_by(username=username.data).first()
        if user and user.id != current_user.id:
            raise ValidationError('Username already taken. Please choose a different one.')
