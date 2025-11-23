from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
import json

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model for retailer authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=True, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    store_name = db.Column(db.String(120), nullable=True)
    is_first_login = db.Column(db.Boolean, default=True)  # Flag for first-time setup
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    uploads = db.relationship('DataUpload', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    analytics = db.relationship('Analytics', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set password"""
        # Explicitly use pbkdf2 since some environments disable hashlib.scrypt
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class DataUpload(db.Model):
    """Model for tracking data uploads"""
    __tablename__ = 'data_uploads'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    data_type = db.Column(db.String(50), nullable=False)  # 'simple' or 'complex'
    upload_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    file_size = db.Column(db.Integer)  # in bytes
    row_count = db.Column(db.Integer)
    status = db.Column(db.String(20), default='processing')  # processing, completed, failed
    error_message = db.Column(db.Text)
    
    # Threshold configuration
    threshold_suggestions = db.Column(db.JSON)  # Suggested thresholds based on data analysis
    threshold_config = db.Column(db.JSON)  # User-configured thresholds actually used for analysis
    threshold_recommendations = db.Column(db.JSON)  # Recommendations for threshold adjustments
    
    # Relationships
    analytics = db.relationship('Analytics', backref='upload', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<DataUpload {self.filename}>'

class Analytics(db.Model):
    """Model for storing analytics results"""
    __tablename__ = 'analytics'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    upload_id = db.Column(db.Integer, db.ForeignKey('data_uploads.id'), nullable=False, index=True)
    
    # Transaction statistics
    total_transactions = db.Column(db.Integer)
    unique_products = db.Column(db.Integer)
    avg_basket_size = db.Column(db.Float)
    avg_reorder_rate = db.Column(db.Float, default=0.0)  # Average reorder rate across products
    
    # Context distribution (stored as JSON)
    time_distribution = db.Column(db.JSON)  # {morning: x, afternoon: y, evening: z}
    budget_distribution = db.Column(db.JSON)  # {low: x, medium: y, high: z}
    basket_size_distribution = db.Column(db.JSON)  # {small: x, medium: y, large: z}
    age_distribution = db.Column(db.JSON)  # {teen: x, young_adult: y, adult: z, senior: z}
    budget_thresholds = db.Column(db.JSON)  # {low: $value, medium: $value} - calculated percentiles
    
    # Rules statistics
    total_rules_generated = db.Column(db.Integer)
    general_rules_count = db.Column(db.Integer)
    context_rules_count = db.Column(db.Integer)
    
    # Top insights
    top_products = db.Column(db.JSON)  # List of top selling products
    top_associations = db.Column(db.JSON)  # List of top product associations
    
    # Metadata
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f'<Analytics {self.id}>'

class AssociationRule(db.Model):
    """Model for storing association rules"""
    __tablename__ = 'association_rules'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    upload_id = db.Column(db.Integer, db.ForeignKey('data_uploads.id'), nullable=False, index=True)
    
    # Rule components
    antecedents = db.Column(db.JSON, nullable=False)  # List of product IDs
    consequents = db.Column(db.JSON, nullable=False)  # List of product IDs
    
    # Rule metrics
    support = db.Column(db.Float, nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    lift = db.Column(db.Float, nullable=False)
    
    # Context
    context = db.Column(db.String(100))  # 'general', 'time_morning', 'budget_high', etc.
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f'<AssociationRule {self.id}>'

class Product(db.Model):
    """Model for storing product information"""
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    upload_id = db.Column(db.Integer, db.ForeignKey('data_uploads.id'), nullable=False, index=True)
    
    product_id = db.Column(db.String(100), nullable=False)
    product_name = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100))
    
    # Product statistics
    total_orders = db.Column(db.Integer, default=0)
    reorder_rate = db.Column(db.Float, default=0.0)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (db.Index('idx_user_upload_product', 'user_id', 'upload_id', 'product_id'),)
    
    def __repr__(self):
        return f'<Product {self.product_name}>'

class Transaction(db.Model):
    """Model for storing transaction data"""
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    upload_id = db.Column(db.Integer, db.ForeignKey('data_uploads.id'), nullable=False, index=True)
    
    order_id = db.Column(db.String(100), nullable=False)
    products = db.Column(db.JSON, nullable=False)  # List of product IDs
    
    # Context information
    time_of_day = db.Column(db.String(20))  # morning, afternoon, evening, night
    day_of_week = db.Column(db.String(20))
    budget_segment = db.Column(db.String(20))  # low, medium, high
    basket_size = db.Column(db.String(20))  # small, medium, large
    age_group = db.Column(db.String(20))  # teen, young_adult, adult, senior
    
    # Metrics
    total_spent = db.Column(db.Float)
    item_count = db.Column(db.Integer)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (db.Index('idx_user_upload_order', 'user_id', 'upload_id', 'order_id'),)
    
    def __repr__(self):
        return f'<Transaction {self.order_id}>'

class OTP(db.Model):
    """Model for storing OTP verification codes"""
    __tablename__ = 'otp'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False, index=True)
    code = db.Column(db.String(6), nullable=False)
    attempts = db.Column(db.Integer, default=0)
    max_attempts = 5
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<OTP {self.email}>'
