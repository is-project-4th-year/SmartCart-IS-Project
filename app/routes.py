from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify, session, abort
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
import os
import json
from datetime import datetime, timezone
import logging
import pandas as pd
from typing import Dict, Tuple

from app.models import db, User, DataUpload, Analytics, AssociationRule, Product, Transaction, OTP
from app.forms import RegistrationForm, LoginForm, DataUploadForm, ContextFilterForm, OTPVerificationForm, SetupStoreForm, ThresholdConfigForm, UpdateProfileForm
from app.analytics_engine import RetailAnalyticsEngine
from app.email_service import send_otp_email
from app.oauth_helper import create_otp, verify_otp, resend_otp
from app.threshold_handler import ThresholdHandler

logger = logging.getLogger(__name__)


def _normalize_products_list(products_field):
    """Normalize stored products field into a list of string IDs."""
    if isinstance(products_field, list):
        return [str(p) for p in products_field]
    if isinstance(products_field, str):
        try:
            parsed = json.loads(products_field)
            if isinstance(parsed, list):
                return [str(p) for p in parsed]
        except Exception:
            return []
    return []

# Create blueprints
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
main_bp = Blueprint('main', __name__)
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')
api_bp = Blueprint('api', __name__, url_prefix='/api')

# ==================== AUTH ROUTES ====================

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration - email and password only"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            email=form.email.data,
            is_first_login=True
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        logger.info(f"New user registered: {user.email}")
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', form=form)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login with OTP verification - accepts username or email"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.overview'))
    
    form = LoginForm()
    if form.validate_on_submit():
        # Try to find user by username first, then by email
        user = User.query.filter_by(username=form.username.data).first()
        if not user:
            user = User.query.filter_by(email=form.username.data).first()
        
        if user and user.check_password(form.password.data):
            # Generate OTP and send email
            otp_code, success = create_otp(user.email)
            if success:
                # Send OTP email
                email_sent = send_otp_email(user.email, otp_code)
                if email_sent:
                    # Store user email in session for OTP verification
                    session['otp_email'] = user.email
                    session['user_id'] = user.id
                    flash('OTP sent to your email! Please verify to continue.', 'info')
                    return redirect(url_for('auth.verify_otp_page'))
                else:
                    flash('Failed to send OTP email. Please try again.', 'danger')
            else:
                flash('Failed to generate OTP. Please try again.', 'danger')
        else:
            flash('Invalid username/email or password.', 'danger')
    
    return render_template('auth/login.html', form=form)

@auth_bp.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp_page():
    """Verify OTP during login"""
    email = session.get('otp_email')
    user_id = session.get('user_id')
    
    if not email or not user_id:
        flash('Session expired. Please login again.', 'danger')
        return redirect(url_for('auth.login'))
    
    form = OTPVerificationForm()
    if form.validate_on_submit():
        is_valid, error_msg = verify_otp(email, form.otp_code.data)
        
        if is_valid:
            user = db.session.get(User, user_id)
            if user:
                login_user(user)
                logger.info(f"User logged in with OTP: {user.username}")
                
                # Check if first login
                if user.is_first_login:
                    session.pop('otp_email', None)
                    session.pop('user_id', None)
                    flash('Welcome! Please complete your store setup.', 'success')
                    return redirect(url_for('auth.setup_store'))
                
                session.pop('otp_email', None)
                session.pop('user_id', None)
                flash('Login successful!', 'success')
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('dashboard.overview'))
        else:
            flash(error_msg, 'danger')
    
    return render_template('auth/verify_otp.html', form=form, email=email)

@auth_bp.route('/resend-otp', methods=['POST'])
def resend_otp_route():
    """Resend OTP"""
    email = session.get('otp_email')
    
    if not email:
        return jsonify({'success': False, 'message': 'Session expired'}), 400
    
    success, otp_code = resend_otp(email)
    if success:
        email_sent = send_otp_email(email, otp_code)
        if email_sent:
            return jsonify({'success': True, 'message': 'OTP resent successfully'})
    
    return jsonify({'success': False, 'message': 'Failed to resend OTP'}), 500

@auth_bp.route('/setup-store', methods=['GET', 'POST'])
@login_required
def setup_store():
    """First-time login setup - add store name and username"""
    if not current_user.is_first_login:
        return redirect(url_for('dashboard.overview'))
    
    form = SetupStoreForm()
    if form.validate_on_submit():
        try:
            current_user.username = form.username.data
            current_user.store_name = form.store_name.data
            current_user.is_first_login = False
            db.session.commit()
            
            flash('Store setup complete! Welcome to SmartCart!', 'success')
            logger.info(f"User setup completed: {current_user.email}")
            return redirect(url_for('dashboard.overview'))
        except Exception as e:
            db.session.rollback()
            flash('Error completing setup. Please try again.', 'danger')
            logger.error(f"Setup error: {str(e)}")
    
    return render_template('auth/setup_store.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    """User logout"""
    logger.info(f"User logged out: {current_user.username}")
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile update page"""
    form = UpdateProfileForm()
    
    if form.validate_on_submit():
        try:
            current_user.username = form.username.data
            current_user.store_name = form.store_name.data
            db.session.commit()
            
            flash('Profile updated successfully!', 'success')
            logger.info(f"User profile updated: {current_user.email}")
            return redirect(url_for('auth.profile'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating profile. Please try again.', 'danger')
            logger.error(f"Profile update error: {str(e)}")
    elif request.method == 'GET':
        # Pre-populate form with current data
        form.username.data = current_user.username
        form.store_name.data = current_user.store_name
        form.email.data = current_user.email
    
    return render_template('auth/profile.html', form=form, user=current_user)

# ==================== MAIN ROUTES ====================

@main_bp.route('/')
def index():
    """Home page"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.overview'))
    return render_template('index.html')

# ==================== DASHBOARD ROUTES ====================

@dashboard_bp.route('/')
@login_required
def dashboard():
    """Dashboard root - redirect to overview"""
    return redirect(url_for('dashboard.overview'))

@dashboard_bp.route('/glossary')
@login_required
def glossary():
    """Show metric glossary and explanations"""
    return render_template('dashboard/metric_glossary.html')

@dashboard_bp.route('/overview')
@login_required
def overview():
    """Dashboard overview with top rules preview"""
    recent_uploads = DataUpload.query.filter_by(user_id=current_user.id).order_by(
        DataUpload.upload_date.desc()
    ).limit(5).all()
    
    total_uploads = DataUpload.query.filter_by(user_id=current_user.id).count()
    total_rules = AssociationRule.query.filter_by(user_id=current_user.id).count()
    
    # Get top 5 strongest rules for preview
    top_rules = []
    latest_upload = DataUpload.query.filter_by(user_id=current_user.id).order_by(
        DataUpload.upload_date.desc()
    ).first()
    
    if latest_upload:
        rules_data = AssociationRule.query.filter_by(
            user_id=current_user.id,
            upload_id=latest_upload.id
        ).order_by(AssociationRule.confidence.desc()).limit(5).all()
        
        for rule in rules_data:
            try:
                # Get product names
                antecedent_products = []
                for pid in rule.antecedents:
                    product = Product.query.filter_by(user_id=current_user.id, upload_id=latest_upload.id, product_id=str(pid)).first()
                    if product:
                        antecedent_products.append(product.product_name)
                
                consequent_products = []
                for pid in rule.consequents:
                    product = Product.query.filter_by(user_id=current_user.id, upload_id=latest_upload.id, product_id=str(pid)).first()
                    if product:
                        consequent_products.append(product.product_name)
                
                if antecedent_products and consequent_products:
                    top_rules.append({
                        'antecedents_text': ' + '.join(antecedent_products),
                        'consequents_text': ' + '.join(consequent_products),
                        'confidence': rule.confidence,
                        'lift': rule.lift
                    })
            except Exception as e:
                logger.error(f"Error processing rule for overview: {str(e)}")
                continue
    
    return render_template('dashboard/overview.html',
                         recent_uploads=recent_uploads,
                         total_uploads=total_uploads,
                         total_rules=total_rules,
                         top_rules=top_rules,
                         latest_upload=latest_upload)

@dashboard_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_data():
    """Upload CSV or Excel data and redirect to threshold configuration"""
    form = DataUploadForm()
    
    if form.validate_on_submit():
        try:
            file = form.csv_file.data
            original_filename = file.filename
            filename = secure_filename(file.filename)
            timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_')
            
            # Handle Excel files - convert to CSV
            if original_filename.lower().endswith('.xlsx'):
                excel_filename = timestamp + filename
                excel_filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], excel_filename)
                file.save(excel_filepath)
                
                try:
                    df = pd.read_excel(excel_filepath)
                    csv_filename = timestamp + original_filename.rsplit('.', 1)[0] + '.csv'
                    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], csv_filename)
                    df.to_csv(filepath, index=False)
                    os.remove(excel_filepath)
                    filename = csv_filename
                except Exception as e:
                    if os.path.exists(excel_filepath):
                        os.remove(excel_filepath)
                    flash(f'Error converting Excel file: {str(e)}', 'danger')
                    logger.error(f"Excel conversion error: {str(e)}")
                    return render_template('dashboard/upload.html', form=form)
            else:
                filename = timestamp + filename
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
            
            file_size = os.path.getsize(filepath)
            
            # Validate file format and count rows
            try:
                df = pd.read_csv(filepath)
                # Support both traditional format (order_id, product_id) and transaction format (transaction_id, product_name)
                has_traditional = {'order_id', 'product_id'}.issubset(set(df.columns))
                has_transaction = {'transaction_id', 'product_name'}.issubset(set(df.columns))
                
                if not (has_traditional or has_transaction):
                    os.remove(filepath)
                    available_cols = set(df.columns)
                    flash(f'Invalid CSV format. Must include either (order_id, product_id) or (transaction_id, product_name). Found columns: {", ".join(sorted(available_cols))}', 'danger')
                    logger.warning(f"Invalid CSV format uploaded by {current_user.username}")
                    return render_template('dashboard/upload.html', form=form)
                
                row_count = len(df)
            except Exception as e:
                if os.path.exists(filepath):
                    os.remove(filepath)
                flash(f'Error reading file: {str(e)}', 'danger')
                logger.error(f"File read error: {str(e)}")
                return render_template('dashboard/upload.html', form=form)
            
            # Create upload record
            upload = DataUpload(
                user_id=current_user.id,
                filename=original_filename,
                file_path=filepath,
                data_type='simple',
                file_size=file_size,
                row_count=row_count,
                status='awaiting_threshold_config'
            )
            db.session.add(upload)
            db.session.commit()
            
            logger.info(f"File uploaded: {original_filename} (ID: {upload.id})")
            flash('File uploaded successfully! Now configure your analytics thresholds.', 'success')
            
            # Redirect to threshold configuration
            return redirect(url_for('dashboard.configure_thresholds_page', upload_id=upload.id))
        
        except FileNotFoundError:
            flash('Upload folder not found. Please contact support.', 'danger')
            logger.error("Upload folder missing")
        except Exception as e:
            flash(f'Error uploading file: {str(e)}', 'danger')
            logger.error(f"Upload error: {str(e)}")
    
    return render_template('dashboard/upload.html', form=form)


@dashboard_bp.route('/threshold-config/<int:upload_id>', methods=['GET', 'POST'])
@login_required
def configure_thresholds_page(upload_id):
    """Show threshold configuration page with suggestions and data analysis"""
    upload = db.session.get(DataUpload, upload_id)
    if not upload:
        abort(404)
    
    if upload.user_id != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('dashboard.overview'))
    
    # Check if file still exists
    if not os.path.exists(upload.file_path):
        flash('Upload file not found.', 'danger')
        return redirect(url_for('dashboard.upload_history'))
    
    form = ThresholdConfigForm()
    
    # On first load, analyze data and generate suggestions
    try:
        df = pd.read_csv(upload.file_path)
        
        # Normalize data format: support both transaction and traditional formats
        has_format_1 = 'order_id' in df.columns and 'product_id' in df.columns
        has_format_2 = 'transaction_id' in df.columns and 'product_name' in df.columns
        
        if has_format_2 and not has_format_1:
            logger.info("Converting transaction format to order format for threshold configuration...")
            df['order_id'] = df['transaction_id']
            # Create numeric product_id from product_name hash
            df['product_id'] = df['product_name'].astype(str).apply(hash) % (10**8)
        
        # Only generate suggestions if not already done
        if not upload.threshold_suggestions:
            handler = ThresholdHandler()
            result = handler.analyze_and_suggest(df)
            
            # Store suggestions
            upload.threshold_suggestions = result.get('suggestions', {})
            upload.threshold_recommendations = handler.generate_recommendations(
                result.get('analysis', {}),
                result.get('suggestions', {})
            )
            db.session.commit()
            
            # Get display suggestions
            display_suggestions = handler.get_display_suggestions(result)
        else:
            handler = ThresholdHandler()
            display_suggestions = handler.get_display_suggestions({
                'suggestions': upload.threshold_suggestions
            })
        
        # Pre-fill form with suggestions on GET request
        if request.method == 'GET':
            form.budget_low.data = display_suggestions['budget_low']
            form.budget_medium.data = display_suggestions['budget_medium']
            form.min_support.data = display_suggestions['min_support']
            form.min_confidence.data = display_suggestions['min_confidence']
            form.min_lift.data = display_suggestions['min_lift']
            form.basket_small_max.data = display_suggestions['basket_small_max']
            form.basket_medium_max.data = display_suggestions['basket_medium_max']
            form.age_teen_max.data = display_suggestions['age_teen_max']
            form.age_young_adult_max.data = display_suggestions['age_young_adult_max']
            form.age_adult_max.data = display_suggestions['age_adult_max']
        
        # Get data analysis for display
        data_analysis = {
            'total_records': len(df),
            'total_transactions': df['order_id'].nunique() if 'order_id' in df.columns else 0,
            'unique_products': df['product_id'].nunique() if 'product_id' in df.columns else 0,
            'data_quality_score': 0.8  # Placeholder - will be enhanced
        }
        
        if form.validate_on_submit():
            # Convert form data to threshold config
            handler = ThresholdHandler()
            threshold_config = handler.form_to_config(form.data)
            
            # Store configured thresholds in upload
            upload.threshold_config = threshold_config
            upload.status = 'processing'
            db.session.commit()
            
            logger.info(f"Thresholds configured for upload {upload_id}: {threshold_config}")
            flash('Thresholds configured! Processing analytics...', 'success')
            
            # Process analytics with configured thresholds
            return redirect(url_for('dashboard.process_analytics', upload_id=upload_id))
        
    except Exception as e:
        logger.error(f"Error in threshold configuration: {str(e)}")
        flash(f'Error loading data: {str(e)}', 'danger')
        return redirect(url_for('dashboard.upload_history'))
    
    return render_template('dashboard/threshold_config.html',
                         form=form,
                         upload=upload,
                         data_analysis=data_analysis,
                         suggested_thresholds=upload.threshold_suggestions or {},
                         recommendations=upload.threshold_recommendations or {})


@dashboard_bp.route('/process-analytics/<int:upload_id>')
@login_required
def process_analytics(upload_id):
    """Process analytics with configured thresholds"""
    upload = db.session.get(DataUpload, upload_id)
    if not upload:
        abort(404)
    
    if upload.user_id != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('dashboard.overview'))
    
    if not os.path.exists(upload.file_path):
        flash('Upload file not found.', 'danger')
        return redirect(url_for('dashboard.upload_history'))
    
    try:
        # Initialize analytics engine with configured thresholds
        engine = RetailAnalyticsEngine(config=getattr(current_app, 'config', {}))
        
        # Set thresholds from upload configuration
        if upload.threshold_config:
            engine.set_thresholds(upload.threshold_config)
            logger.info(f"Applied stored thresholds: {upload.threshold_config}")
        else:
            logger.warning(f"No threshold config found for upload {upload_id}, using defaults")
        
        # Process data
        sales_df = engine.load_and_validate_data(upload.file_path)
        engine.prepare_transactions_with_context(sales_df)
        engine.generate_smart_rules()
        summary = engine.generate_analytics_summary()
        
        # Count total_orders for each product from transactions
        product_order_counts = {}
        
        # Persist Transactions
        for tx in engine.transaction_contexts:
            db.session.add(Transaction(
                user_id=current_user.id,
                upload_id=upload.id,
                order_id=str(tx.get('order_id')),
                products=[int(p) for p in tx.get('products', []) if p is not None],
                time_of_day=tx.get('time_of_day'),
                day_of_week=tx.get('day_of_week'),
                budget_segment=tx.get('budget'),
                basket_size=tx.get('basket_size'),
                age_group=tx.get('age_group'),
                total_spent=float(tx.get('total_spent', 0) or 0),
                item_count=int(tx.get('item_count', 0) or 0)
            ))
            
            # Count product occurrences in this transaction
            for product_id in tx.get('products', []):
                if product_id is not None:
                    pid = int(product_id)
                    product_order_counts[pid] = product_order_counts.get(pid, 0) + 1
        
        # Persist Products
        if engine.products_df is not None and not engine.products_df.empty:
            unique_products = engine.products_df.drop_duplicates()
            reorder_rates = summary.get('reorder_rates', {})
            for _, row in unique_products.iterrows():
                product_id = int(row['product_id'])
                db.session.add(Product(
                    user_id=current_user.id,
                    upload_id=upload.id,
                    product_id=str(product_id),
                    product_name=str(row['product_name']),
                    total_orders=product_order_counts.get(product_id, 0),
                    reorder_rate=reorder_rates.get(product_id, 0.0)
                ))
        
        # Persist Rules
        def save_rules(rules_df, context_label):
            if rules_df is None or getattr(rules_df, 'empty', True):
                return
            for _, r in rules_df.iterrows():
                antecedents = [int(x) for x in list(r['antecedents'])]
                consequents = [int(x) for x in list(r['consequents'])]
                db.session.add(AssociationRule(
                    user_id=current_user.id,
                    upload_id=upload.id,
                    antecedents=antecedents,
                    consequents=consequents,
                    support=float(r.get('support', 0)),
                    confidence=float(r.get('confidence', 0)),
                    lift=float(r.get('lift', 0)),
                    context=context_label
                ))
        
        if 'general' in engine.contextual_rules:
            save_rules(engine.contextual_rules['general'], 'general')
        for key, df_rules in engine.contextual_rules.items():
            if key == 'general':
                continue
            save_rules(df_rules, key)
        
        # Persist Analytics summary with thresholds
        analytics = Analytics(
            user_id=current_user.id,
            upload_id=upload.id,
            total_transactions=int(summary.get('total_transactions', 0) or 0),
            unique_products=int(summary.get('unique_products', 0) or 0),
            avg_basket_size=float(summary.get('avg_basket_size', 0) or 0),
            avg_reorder_rate=float(summary.get('avg_reorder_rate', 0) or 0),
            time_distribution=summary.get('time_distribution') or {},
            budget_distribution=summary.get('budget_distribution') or {},
            basket_size_distribution=summary.get('basket_size_distribution') or {},
            age_distribution=summary.get('age_distribution') or {},
            budget_thresholds=upload.threshold_config.get('budget_thresholds') if upload.threshold_config else {},
            total_rules_generated=int(summary.get('total_rules', 0) or 0),
            general_rules_count=int(len(engine.contextual_rules.get('general', [])) if 'general' in engine.contextual_rules else 0),
            context_rules_count=int(sum(len(v) for k, v in engine.contextual_rules.items() if k != 'general')),
            top_products=[],
            top_associations=[]
        )
        db.session.add(analytics)
        
        # Mark upload complete
        upload.status = 'completed'
        db.session.commit()
        
        flash('Analytics processing completed successfully!', 'success')
        logger.info(f"Analytics processed for upload {upload.id}")
        return redirect(url_for('dashboard.analytics_detail', upload_id=upload.id))
        
    except Exception as e:
        upload.status = 'failed'
        upload.error_message = str(e)
        db.session.commit()
        logger.error(f"Analytics processing failed: {str(e)}")
        flash(f'Analytics processing failed: {str(e)}', 'danger')
        return redirect(url_for('dashboard.upload_history'))

@dashboard_bp.route('/upload-success/<int:upload_id>')
@login_required
def upload_success(upload_id):
    """Show upload success with file details"""
    upload = db.session.get(DataUpload, upload_id)
    
    if not upload:
        flash('Upload not found.', 'danger')
        return redirect(url_for('dashboard.overview'))
    
    if upload.user_id != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('dashboard.overview'))
    
    # Get analytics if available (safe query)
    analytics = None
    try:
        analytics = Analytics.query.filter_by(upload_id=upload_id).first()
    except Exception as e:
        logger.warning(f"Could not load analytics: {str(e)}")
        analytics = None
    
    return render_template('dashboard/upload_success.html',
                         upload=upload,
                         analytics=analytics)

@dashboard_bp.route('/upload-history')
@login_required
def upload_history():
    """View upload history"""
    page = request.args.get('page', 1, type=int)
    upload_id = request.args.get('upload_id', None, type=int)  # For tracking newly uploaded file
    uploads = DataUpload.query.filter_by(user_id=current_user.id).order_by(
        DataUpload.upload_date.desc()  # Descending: newest uploads first
    ).paginate(page=page, per_page=10)
    
    # If there's a specific upload being tracked, pass it separately
    tracked_upload = None
    if upload_id:
        tracked_upload = db.session.get(DataUpload, upload_id)
        if tracked_upload and tracked_upload.user_id != current_user.id:
            tracked_upload = None
    
    return render_template('dashboard/upload_history.html', uploads=uploads, tracked_upload=tracked_upload)

@dashboard_bp.route('/analytics/<int:upload_id>')
@login_required
def analytics_detail(upload_id):
    """View analytics for specific upload"""
    upload = db.session.get(DataUpload, upload_id)
    if not upload:
        abort(404)
    
    if upload.user_id != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('dashboard.overview'))
    
    # Get analytics (safe query)
    analytics = None
    try:
        analytics = Analytics.query.filter_by(upload_id=upload_id).first()
    except Exception as e:
        logger.warning(f"Could not load analytics: {str(e)}")
        analytics = None
    
    if not analytics:
        flash('Analytics not yet available for this upload.', 'info')
        return redirect(url_for('dashboard.upload_history'))
    
    return render_template('dashboard/analytics_detail.html',
                         upload=upload,
                         analytics=analytics)

@dashboard_bp.route('/market-basket')
@login_required
def market_basket():
    """Retired contextual factors page - redirect to recommendations."""
    flash('Contextual Factors has been retired. Use Recommendations for rule insights.', 'info')
    return redirect(url_for('dashboard.recommendations'))

@dashboard_bp.route('/recommendations')
@login_required
def recommendations():
    """Product recommendations interface with association rules and filtering"""
    import pandas as pd
    
    # Get latest upload
    latest_upload = DataUpload.query.filter_by(user_id=current_user.id).order_by(
        DataUpload.upload_date.desc()
    ).first()
    
    if not latest_upload:
        flash('Please upload data first.', 'info')
        return redirect(url_for('dashboard.upload_data'))
    
    # Get filter parameters from request with safe conversion
    try:
        min_confidence_pct = request.args.get('min_confidence', default='0', type=str).strip()
        min_confidence = float(min_confidence_pct) / 100 if min_confidence_pct else 0
    except (ValueError, TypeError):
        min_confidence = 0
    
    try:
        min_support_pct = request.args.get('min_support', default='0', type=str).strip()
        min_support = float(min_support_pct) / 100 if min_support_pct else 0
    except (ValueError, TypeError):
        min_support = 0
    
    try:
        min_lift_str = request.args.get('min_lift', default='0', type=str).strip()
        min_lift = float(min_lift_str) if min_lift_str else 0
    except (ValueError, TypeError):
        min_lift = 0
    
    context_filter = request.args.get('context', default='all', type=str)
    
    # Get all association rules for this upload
    rules_data = AssociationRule.query.filter_by(
        user_id=current_user.id,
        upload_id=latest_upload.id
    ).order_by(AssociationRule.confidence.desc()).all()
    
    # Apply filters
    filtered_rules = []
    for rule in rules_data:
        # Apply numeric filters
        if rule.confidence < min_confidence or rule.support < min_support or rule.lift < min_lift:
            continue
        
        # Apply context filter
        if context_filter != 'all':
            if context_filter == 'general' and rule.context != 'general':
                continue
            elif context_filter == 'time' and (not rule.context or not rule.context.startswith('time_')):
                continue
            elif context_filter == 'budget' and (not rule.context or not rule.context.startswith('budget_')):
                continue
            elif context_filter == 'basket' and (not rule.context or not rule.context.startswith('basket_')):
                continue
            elif context_filter == 'age' and (not rule.context or not rule.context.startswith('age_group_')):
                continue
        
        filtered_rules.append(rule)
    
    rules_data = filtered_rules
    
    # Count rules by context
    general_rules_count = len([r for r in rules_data if r.context == 'general'])
    time_rules_count = len([r for r in rules_data if r.context and r.context.startswith('time_')])
    budget_rules_count = len([r for r in rules_data if r.context and r.context.startswith('budget_')])
    age_rules_count = len([r for r in rules_data if r.context and r.context.startswith('age_group_')])
    basket_size_rules_count = len([r for r in rules_data if r.context and r.context.startswith('basket_')])
    
    # Product lookup for friendly names
    product_lookup = {}
    products = Product.query.filter_by(user_id=current_user.id, upload_id=latest_upload.id).all()
    for product in products:
        product_lookup[str(product.product_id)] = product.product_name

    # Cache transactions once for explainability and sampling
    transactions = Transaction.query.filter_by(
        user_id=current_user.id,
        upload_id=latest_upload.id
    ).all()
    transaction_cache = []
    for txn in transactions:
        transaction_cache.append({
            'txn': txn,
            'products': _normalize_products_list(txn.products)
        })
    total_transactions = len(transaction_cache)
    
    def get_product_names(product_ids):
        names = []
        for pid in product_ids:
            pid_str = str(pid)
            name = product_lookup.get(pid_str)
            if name:
                names.append(name)
            else:
                names.append(f"Product {pid_str}")
        return names
    
    def context_descriptor(context_key):
        if not context_key or context_key == 'general':
            return 'all shoppers'
        if context_key.startswith('time_'):
            label = context_key.split('_', 1)[1].replace('_', ' ')
            return f"{label} shoppers"
        if context_key.startswith('budget_'):
            label = context_key.split('_', 1)[1].replace('_', ' ')
            return f"{label} budget baskets"
        if context_key.startswith('basket_'):
            label = context_key.split('_', 1)[1].replace('_', ' ')
            return f"{label} baskets"
        if context_key.startswith('age_group_'):
            label = context_key.split('_', 2)[2].replace('_', ' ')
            return f"{label} shoppers"
        return 'your shoppers'
    
    def context_type(context_key):
        if not context_key or context_key == 'general':
            return 'general'
        if context_key.startswith('time_'):
            return 'time'
        if context_key.startswith('budget_'):
            return 'budget'
        if context_key.startswith('basket_'):
            return 'basket'
        if context_key.startswith('age_group_'):
            return 'age'
        return 'other'
    
    def build_tip(antecedents_text, consequents_text, context_desc):
        audience = 'all shoppers' if context_desc == 'all shoppers' else context_desc
        return f"Place {consequents_text} near {antecedents_text} for {audience} to boost attachment rate."
    
    # Capture highlight rules per context type
    highlight_map = {}
    for rule in rules_data:
        ctype = context_type(rule.context)
        if ctype == 'other':
            continue
        if ctype not in highlight_map:
            highlight_map[ctype] = rule
    
    # Prepare rule details with product names and sample transactions
    rules = []
    for rule in rules_data[:20]:  # Top 20 rules
        try:
            # Get product names for antecedents and consequents
            antecedent_products = get_product_names(rule.antecedents)
            consequent_products = get_product_names(rule.consequents)
            
            if not antecedent_products or not consequent_products:
                continue
            
            antecedents_text = ' + '.join(antecedent_products)
            consequents_text = ' + '.join(consequent_products)
            context_desc = context_descriptor(rule.context)
            retailer_tip = build_tip(antecedents_text, consequents_text, context_desc)

            # Match transactions once per rule for explanations and examples
            matched_transactions = []
            for entry in transaction_cache:
                products = entry['products']
                if not products:
                    continue
                has_antecedent = any(str(a) in products for a in rule.antecedents)
                has_consequent = any(str(c) in products for c in rule.consequents)
                if has_antecedent and has_consequent:
                    matched_transactions.append(entry)
            
            transaction_count = len(matched_transactions)
            
            # Build sample transactions (up to 3) with friendly product names
            sample_transactions = []
            for entry in matched_transactions[:3]:
                txn = entry['txn']
                txn_product_names = [product_lookup.get(pid, pid) for pid in entry['products'] if product_lookup.get(pid)]
                sample_transactions.append({
                    'order_id': txn.order_id,
                    'products_text': ', '.join(txn_product_names),
                    'time_of_day': txn.time_of_day or 'Unknown',
                    'budget_segment': txn.budget_segment or 'Unknown',
                    'basket_size': txn.basket_size or 'Unknown',
                    'total_spent': txn.total_spent or 0
                })
            
            # Explainability: compare rule confidence to baseline add rate for consequents
            base_hits = 0
            if total_transactions > 0:
                conseq_set = {str(c) for c in rule.consequents}
                base_hits = sum(1 for entry in transaction_cache if any(pid in conseq_set for pid in entry['products']))
            baseline_rate = (base_hits / total_transactions) if total_transactions else 0
            uplift_pct = max((rule.confidence - baseline_rate) * 100, 0.0)
            explanation = {
                'narrative': (
                    f"{consequents_text} shows up {rule.lift:.1f}x more often when shoppers already have "
                    f"{antecedents_text} ({rule.confidence:.1%} vs {baseline_rate:.1%} baseline). "
                    f"Backed by {transaction_count} matching orders."
                ),
                'baseline': baseline_rate,
                'uplift_pct': uplift_pct,
                'evidence': transaction_count,
                'confidence': rule.confidence,
                'lift': rule.lift
            }
            
            rules.append({
                'antecedents_text': antecedents_text,
                'consequents_text': consequents_text,
                'support': rule.support,
                'confidence': rule.confidence,
                'lift': rule.lift,
                'transaction_count': transaction_count,
                'sample_transactions': sample_transactions,
                'context_description': context_desc.title(),
                'retailer_tip': retailer_tip,
                'explanation': explanation
            })
        except Exception as e:
            logger.error(f"Error processing rule: {str(e)}")
            continue
    
    # Build highlight cards for retailer-friendly summary
    highlight_labels = {
        'general': 'All Shoppers',
        'time': 'Time of Day',
        'budget': 'Budget Tier',
        'age': 'Age Group',
        'basket': 'Basket Size'
    }
    context_highlights = []
    for key, label in highlight_labels.items():
        rule = highlight_map.get(key)
        if not rule:
            continue
        antecedent_products = get_product_names(rule.antecedents)
        consequent_products = get_product_names(rule.consequents)
        if not antecedent_products or not consequent_products:
            continue
        antecedents_text = ' + '.join(antecedent_products)
        consequents_text = ' + '.join(consequent_products)
        context_desc = context_descriptor(rule.context)
        context_highlights.append({
            'label': label,
            'context_description': context_desc.title(),
            'antecedents_text': antecedents_text,
            'consequents_text': consequents_text,
            'confidence': round(rule.confidence * 100),
            'support': round(rule.support * 100, 1),
            'tip': build_tip(antecedents_text, consequents_text, context_desc)
        })
    
    return render_template('dashboard/recommendations.html',
                         upload=latest_upload,
                         rules=rules,
                         general_rules_count=general_rules_count,
                         time_rules_count=time_rules_count,
                         budget_rules_count=budget_rules_count,
                         age_rules_count=age_rules_count,
                         basket_size_rules_count=basket_size_rules_count,
                         context_highlights=context_highlights,
                         min_confidence=round(min_confidence * 100),
                         min_support=round(min_support * 100),
                         min_lift=round(min_lift, 1) if min_lift > 0 else 0,
                         context_filter=context_filter)

@dashboard_bp.route('/network/<int:upload_id>')
@login_required
def network_visualization(upload_id):
    """Visualize product association network"""
    upload = db.session.get(DataUpload, upload_id)
    if not upload:
        abort(404)
    
    if upload.user_id != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('dashboard.overview'))
    
    # Get association rules
    rules = AssociationRule.query.filter_by(
        user_id=current_user.id,
        upload_id=upload_id
    ).all()
    
    # Format rules for Plotly
    import json
    rules_json = []
    for rule in rules:
        rules_json.append({
            'antecedents': rule.antecedents,
            'consequents': rule.consequents,
            'support': float(rule.support),
            'confidence': float(rule.confidence),
            'lift': float(rule.lift),
            'context': rule.context,
            'antecedent_names': ['Product ' + str(a) for a in rule.antecedents],
            'consequent_names': ['Product ' + str(c) for c in rule.consequents]
        })
    
    return render_template('dashboard/network_visualization.html',
                         upload=upload,
                         rules=rules,
                         rules_json=json.dumps(rules_json))

@dashboard_bp.route('/retailer-dashboard')
@login_required
def retailer_dashboard():
    """Complete retailer dashboard with all metrics"""
    # Get latest upload
    latest_upload = DataUpload.query.filter_by(user_id=current_user.id).order_by(
        DataUpload.upload_date.desc()
    ).first()
    
    if not latest_upload:
        flash('Please upload data first to view the dashboard.', 'info')
        return redirect(url_for('dashboard.upload_data'))
    
    # Get analytics (skip if not available - file-based storage model)
    analytics = None
    try:
        analytics = Analytics.query.filter_by(upload_id=latest_upload.id).first()
    except Exception as e:
        logger.warning(f"Could not load analytics: {str(e)}")
        analytics = None
    
    # Get top products (safe query)
    top_products = []
    try:
        top_products = Product.query.filter_by(
            user_id=current_user.id,
            upload_id=latest_upload.id
        ).order_by(Product.total_orders.desc()).limit(10).all()
        # Serialize a small slice for JSON payloads
        top_products_payload = [
            {
                'product_name': p.product_name,
                'total_orders': p.total_orders or 0
            } for p in top_products[:5]
        ]
    except Exception as e:
        logger.warning(f"Could not load products: {str(e)}")
        top_products = []
        top_products_payload = []
    
    # Get top rules (safe query)
    top_rules = []
    try:
        rules = AssociationRule.query.filter_by(
            user_id=current_user.id,
            upload_id=latest_upload.id,
            context='general'
        ).order_by(AssociationRule.confidence.desc()).limit(10).all()
        
        # Create product ID to name mapping (handle both string and int keys)
        product_map = {}
        all_products = Product.query.filter_by(
            user_id=current_user.id,
            upload_id=latest_upload.id
        ).all()
        for product in all_products:
            product_map[product.product_id] = product.product_name
            product_map[str(product.product_id)] = product.product_name
            product_map[int(product.product_id)] = product.product_name
        
        # Transform rules to include product names
        for rule in rules:
            antecedent_names = []
            for pid in (rule.antecedents or []):
                name = product_map.get(pid) or product_map.get(str(pid)) or product_map.get(int(pid) if isinstance(pid, str) and pid.isdigit() else pid) or pid
                antecedent_names.append(name)
            
            consequent_names = []
            for cid in (rule.consequents or []):
                name = product_map.get(cid) or product_map.get(str(cid)) or product_map.get(int(cid) if isinstance(cid, str) and cid.isdigit() else cid) or cid
                consequent_names.append(name)
            
            top_rules.append({
                'antecedents': antecedent_names,
                'consequents': consequent_names,
                'support': rule.support,
                'confidence': rule.confidence,
                'lift': rule.lift,
                'context': rule.context
            })
    except Exception as e:
        logger.warning(f"Could not load association rules: {str(e)}")
        top_rules = []
    
    # Get transaction statistics (safe query)
    transactions = []
    try:
        transactions = Transaction.query.filter_by(
            user_id=current_user.id,
            upload_id=latest_upload.id
        ).all()
    except Exception as e:
        logger.warning(f"Could not load transactions: {str(e)}")
        transactions = []
    
    # Calculate additional metrics
    total_revenue = sum(getattr(t, 'total_spent', 0) for t in transactions) if transactions else 0
    avg_transaction_value = total_revenue / len(transactions) if transactions else 0
    
    def top_slice(distribution):
        """Return the leading label/count/percent from a distribution map"""
        if not distribution or not isinstance(distribution, dict):
            return None
        safe_dist = {k: v for k, v in distribution.items() if isinstance(v, (int, float))}
        if not safe_dist:
            return None
        label = max(safe_dist, key=safe_dist.get)
        count = safe_dist.get(label, 0)
        total = sum(safe_dist.values()) or 1
        return {
            'label': label.replace('_', ' ').title(),
            'count': count,
            'percent': (count / total) * 100
        }
    
    busiest_moment = None
    common_budget_range = None
    leading_shopper_group = None
    budget_thresholds = {}
    
    if analytics:
        try:
            time_dist = analytics.time_distribution if isinstance(getattr(analytics, 'time_distribution', {}), dict) else {}
            budget_dist = analytics.budget_distribution if isinstance(getattr(analytics, 'budget_distribution', {}), dict) else {}
            age_dist = getattr(analytics, 'age_distribution', {}) if isinstance(getattr(analytics, 'age_distribution', {}), dict) else {}
            
            busiest_moment = top_slice(time_dist)
            common_budget_range = top_slice(budget_dist)
            leading_shopper_group = top_slice(age_dist)
            budget_thresholds = analytics.budget_thresholds or {}
        except Exception as e:
            logger.warning(f"Could not build dashboard insights: {str(e)}")
    
    # Fallback: derive leading shopper group from stored transactions if analytics lacked age distribution
    if not leading_shopper_group and transactions:
        try:
            age_counts = {}
            for tx in transactions:
                key = (tx.age_group or '').strip() or 'Unknown'
                age_counts[key] = age_counts.get(key, 0) + 1
            leading_shopper_group = top_slice(age_counts)
        except Exception as e:
            logger.warning(f"Could not derive age mix from transactions: {str(e)}")
    
    return render_template('dashboard/retailer_dashboard.html',
                         upload=latest_upload,
                         analytics=analytics,
                         top_products=top_products,
                         top_products_payload=top_products_payload,
                         top_rules=top_rules,
                         transactions=transactions,
                         total_revenue=total_revenue,
                         avg_transaction_value=avg_transaction_value,
                         busiest_moment=busiest_moment,
                         common_budget_range=common_budget_range,
                         leading_shopper_group=leading_shopper_group,
                         budget_thresholds=budget_thresholds)

# ==================== API ROUTES ====================

@api_bp.route('/recommendations/<int:product_id>', methods=['GET'])
@login_required
def get_recommendations(product_id):
    """Get recommendations for a product"""
    try:
        # Get context from query parameters
        context = {
            'time_of_day': request.args.get('time_of_day', 'afternoon'),
            'budget': request.args.get('budget', 'medium'),
            'basket_size': request.args.get('basket_size', 'medium')
        }
        
        # Get latest upload
        latest_upload = DataUpload.query.filter_by(user_id=current_user.id).order_by(
            DataUpload.upload_date.desc()
        ).first()
        
        if not latest_upload:
            return jsonify({'error': 'No data available'}), 404
        
        # Product lookup for explanations
        product_lookup = {}
        products = Product.query.filter_by(user_id=current_user.id, upload_id=latest_upload.id).all()
        for product in products:
            product_lookup[str(product.product_id)] = product.product_name
        
        # Cache transactions for baseline rates
        transactions = Transaction.query.filter_by(
            user_id=current_user.id,
            upload_id=latest_upload.id
        ).all()
        transaction_cache = [{'products': _normalize_products_list(txn.products)} for txn in transactions]
        total_txns = len(transaction_cache)
        
        def baseline_rate_for_consequents(consequents):
            if total_txns == 0:
                return 0
            conseq_set = {str(c) for c in consequents}
            hits = sum(1 for entry in transaction_cache if any(pid in conseq_set for pid in entry['products']))
            return hits / total_txns
        
        # Get rules from database
        rules = AssociationRule.query.filter_by(
            user_id=current_user.id,
            upload_id=latest_upload.id
        ).all()
        
        recommendations = []
        for rule in rules:
            antecedent_ids = [str(a) for a in rule.antecedents]
            if str(product_id) in antecedent_ids:
                for consequent_id in rule.consequents:
                    if consequent_id != product_id:
                        target_name = product_lookup.get(str(consequent_id))
                        source_name = product_lookup.get(str(product_id), f"Product {product_id}")
                        if target_name:
                            baseline = baseline_rate_for_consequents(rule.consequents)
                            recommendations.append({
                                'product_id': consequent_id,
                                'product_name': target_name,
                                'confidence': rule.confidence,
                                'lift': rule.lift,
                                'context': rule.context,
                                'explanation': {
                                    'narrative': (
                                        f"When carts include {source_name}, shoppers add {target_name} "
                                        f"{rule.lift:.1f}x more often than average "
                                        f"({rule.confidence:.1%} vs {baseline:.1%} baseline)."
                                    ),
                                    'baseline': baseline,
                                    'confidence': rule.confidence,
                                    'lift': rule.lift
                                }
                            })
        
        # Sort by confidence
        recommendations.sort(key=lambda x: x['confidence'], reverse=True)
        
        return jsonify(recommendations[:5])
    
    except Exception as e:
        logger.error(f"Error getting recommendations: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/analytics/<int:upload_id>', methods=['GET'])
@login_required
def get_analytics(upload_id):
    """Get analytics data for charts"""
    try:
        upload = db.session.get(DataUpload, upload_id)
        
        if not upload:
            return jsonify({'error': 'Upload not found'}), 404
        
        if upload.user_id != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        analytics = Analytics.query.filter_by(upload_id=upload_id).first()
        
        if not analytics:
            return jsonify({'error': 'Analytics not available'}), 404
        
        return jsonify({
            'total_transactions': analytics.total_transactions,
            'unique_products': analytics.unique_products,
            'avg_basket_size': analytics.avg_basket_size,
            'time_distribution': analytics.time_distribution,
            'budget_distribution': analytics.budget_distribution,
            'age_distribution': getattr(analytics, 'age_distribution', None),
            'basket_size_distribution': analytics.basket_size_distribution,
            'total_rules': analytics.total_rules_generated,
            'top_products': analytics.top_products,
            'top_associations': analytics.top_associations
        })
    
    except Exception as e:
        logger.error(f"Error getting analytics: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/upload-status/<int:upload_id>', methods=['GET'])
@login_required
def get_upload_status(upload_id):
    """Get upload processing status"""
    try:
        upload = db.session.get(DataUpload, upload_id)
        
        if not upload or upload.user_id != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Check if analytics is ready
        analytics = Analytics.query.filter_by(upload_id=upload_id).first()
        
        return jsonify({
            'status': upload.status,
            'filename': upload.filename,
            'upload_date': upload.upload_date.isoformat(),
            'error_message': upload.error_message,
            'analytics_ready': analytics is not None
        })
    
    except Exception as e:
        logger.error(f"Error getting upload status: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ==================== HELPER FUNCTIONS ====================

def process_upload(upload_id):
    """Process uploaded CSV file - DISABLED
    
    Storage is now file-based only. No data stored in database.
    The CSV/Excel file is saved to the uploads folder for direct access.
    """
    pass  # Disabled - files are stored directly, not processed into database
