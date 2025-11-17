#!/usr/bin/env python
"""
SmartCart Flask Application Entry Point
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

from app import create_app
from app.models import db, User, DataUpload, Analytics, AssociationRule, Product, Transaction

# Create application
app = create_app(os.environ.get('FLASK_ENV', 'development'))

@app.shell_context_processor
def make_shell_context():
    """Create shell context for Flask CLI"""
    return {
        'db': db,
        'User': User,
        'DataUpload': DataUpload,
        'Analytics': Analytics,
        'AssociationRule': AssociationRule,
        'Product': Product,
        'Transaction': Transaction
    }

@app.cli.command()
def init_db():
    """Initialize the database"""
    with app.app_context():
        db.create_all()
        print('Database initialized.')

@app.cli.command()
def drop_db():
    """Drop all database tables"""
    if input('Are you sure? (y/n) ').lower() == 'y':
        with app.app_context():
            db.drop_all()
            print('Database dropped.')

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:  # CLI command provided
        pass  # Let Flask CLI handle it
    else:
        app.run(
            host='0.0.0.0',
            port=int(os.environ.get('PORT', 5001)),  # Changed to 5001
            debug=os.environ.get('DEBUG', 'False').lower() == 'true'
        )
