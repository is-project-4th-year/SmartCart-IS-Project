import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables FIRST before importing config
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

from flask import Flask
from flask_login import LoginManager
from config import config

def create_app(config_name='development'):
    """Application factory"""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Create upload folder
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Initialize extensions
    from app.models import db
    db.init_app(app)
    
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    
    from app.models import User
    
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))
    
    # Add Jinja2 filters for currency formatting
    @app.template_filter('currency')
    def currency_filter(value):
        """Format a value as currency with KES symbol"""
        if value is None:
            return '—'
        try:
            return f"{app.config['CURRENCY_SYMBOL']} {float(value):,.2f}"
        except (ValueError, TypeError):
            return '—'
    
    # Make currency configuration available in templates
    @app.context_processor
    def inject_currency():
        return {
            'currency_symbol': app.config['CURRENCY_SYMBOL'],
            'currency_code': app.config['CURRENCY_CODE']
        }
    
    # Register blueprints
    from app.routes import auth_bp, main_bp, dashboard_bp, api_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp)
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    # Setup logging
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = RotatingFileHandler('logs/smartcart.log', maxBytes=10240000, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('SmartCart startup')
    
    return app
