"""
Enhanced Retail Analytics Engine
Handles data processing, context enrichment, and association rule generation
"""

import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import apriori, association_rules
from datetime import datetime
from typing import List, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)

class RetailAnalyticsEngine:
    """Main analytics engine for processing retail data"""
    
    def __init__(self, config):
        self.config = config
        self.contextual_rules = {}
        self.products_df = None
        self.transaction_contexts = []
        
        # User-configurable thresholds
        self.thresholds = {
            'budget': {'low': 25.0, 'medium': 75.0},
            'association_rules': {'min_support': 0.05, 'min_confidence': 0.3, 'min_lift': 1.0},
            'basket_size': {'small': 3, 'medium': 8},
            'age_groups': {'teen': 17, 'young_adult': 24, 'adult': 59}
        }
        
        # Legacy compatibility
        self.budget_thresholds = {'low': 25.0, 'medium': 75.0}
        self.analytics_data = {}
        self.budget_distribution = {}
        self.threshold_config_used = None  # Track which config was used
    
    def set_thresholds(self, threshold_config: Dict[str, Any]) -> None:
        """
        Set user-configured thresholds
        
        Args:
            threshold_config: Dictionary with threshold configurations
        """
        try:
            # Budget thresholds
            if 'budget_thresholds' in threshold_config:
                self.thresholds['budget'] = threshold_config['budget_thresholds']
                self.budget_thresholds = threshold_config['budget_thresholds']
            
            # Association rule thresholds
            if 'association_rules' in threshold_config:
                self.thresholds['association_rules'] = threshold_config['association_rules']
            
            # Basket size thresholds
            if 'basket_size_categories' in threshold_config:
                basket_config = threshold_config['basket_size_categories']
                self.thresholds['basket_size'] = {
                    'small': basket_config.get('small', {}).get('max', 3),
                    'medium': basket_config.get('medium', {}).get('max', 8)
                }
            
            # Age group boundaries
            if 'age_group_boundaries' in threshold_config:
                age_config = threshold_config['age_group_boundaries']
                self.thresholds['age_groups'] = {
                    'teen': age_config.get('teen', {}).get('max', 17),
                    'young_adult': age_config.get('young_adult', {}).get('max', 24),
                    'adult': age_config.get('adult', {}).get('max', 59)
                }
            
            self.threshold_config_used = threshold_config
            logger.info(f"Thresholds configured: {self.thresholds}")
            
        except Exception as e:
            logger.error(f"Error setting thresholds: {e}")
            raise
    
    def get_thresholds(self) -> Dict[str, Any]:
        """Get current threshold configuration"""
        return self.thresholds
    
    def get_threshold_config_summary(self) -> str:
        """Get human-readable summary of threshold configuration"""
        summary = []
        summary.append("Budget Thresholds:")
        summary.append(f"  Low: ${self.thresholds['budget']['low']:.2f}")
        summary.append(f"  Medium: ${self.thresholds['budget']['medium']:.2f}")
        
        summary.append("\nAssociation Rules:")
        summary.append(f"  Min Support: {self.thresholds['association_rules']['min_support']:.2f}")
        summary.append(f"  Min Confidence: {self.thresholds['association_rules']['min_confidence']:.2f}")
        summary.append(f"  Min Lift: {self.thresholds['association_rules']['min_lift']:.2f}")
        
        summary.append("\nBasket Size Categories:")
        summary.append(f"  Small: 1-{self.thresholds['basket_size']['small']} items")
        summary.append(f"  Medium: {self.thresholds['basket_size']['small']+1}-{self.thresholds['basket_size']['medium']} items")
        summary.append(f"  Large: {self.thresholds['basket_size']['medium']+1}+ items")
        
        summary.append("\nAge Groups:")
        summary.append(f"  Teen: 0-{self.thresholds['age_groups']['teen']}")
        summary.append(f"  Young Adult: {self.thresholds['age_groups']['teen']+1}-{self.thresholds['age_groups']['young_adult']}")
        summary.append(f"  Adult: {self.thresholds['age_groups']['young_adult']+1}-{self.thresholds['age_groups']['adult']}")
        summary.append(f"  Senior: {self.thresholds['age_groups']['adult']+1}+")
        
        return "\n".join(summary)
    
    def load_and_validate_data(self, csv_file_path: str) -> pd.DataFrame:
        """Load and validate CSV data"""
        try:
            logger.info(f"Loading data from {csv_file_path}")
            sales_data = pd.read_csv(csv_file_path)
            logger.info(f"Successfully loaded {len(sales_data)} records")
            
            # Validate and normalize data structure (modifies dataframe in place)
            self._validate_data_structure(sales_data)
            
            # Clean data
            sales_data = self._clean_dataframe(sales_data, 'sales_data')
            
            # Extract product information (after normalization, both columns should exist)
            if 'product_id' in sales_data.columns and 'product_name' in sales_data.columns:
                self.products_df = sales_data[['product_id', 'product_name']].drop_duplicates()
                logger.info(f"Found {len(self.products_df)} unique products")
            elif 'product_id' in sales_data.columns:
                # If only product_id exists, create a simple products dataframe
                self.products_df = sales_data[['product_id']].drop_duplicates()
                self.products_df['product_name'] = self.products_df['product_id'].astype(str)
                logger.info(f"Found {len(self.products_df)} unique products (names auto-generated)")
            
            return sales_data
        
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            raise
    
    def _validate_data_structure(self, df: pd.DataFrame) -> None:
        """Validate data structure - supports both formats"""
        logger.info(f"Data shape: {df.shape[0]} rows, {df.shape[1]} columns")
        logger.info(f"Columns: {list(df.columns)}")
        
        # Support two formats:
        # Format 1: order_id + product_id (traditional)
        # Format 2: transaction_id + product_name (transactions)
        
        has_format_1 = 'order_id' in df.columns and 'product_id' in df.columns
        has_format_2 = 'transaction_id' in df.columns and 'product_name' in df.columns
        
        if not (has_format_1 or has_format_2):
            raise ValueError(
                "Missing required columns. Please use one of these formats:\n"
                "Format 1: order_id + product_id + product_name\n"
                "Format 2: transaction_id + product_name"
            )
        
        # Normalize data to Format 1 (order_id + product_id + product_name)
        if has_format_2 and not has_format_1:
            logger.info("Converting from transaction format to order format...")
            df['order_id'] = df['transaction_id']
            # Create numeric product_id from product_name hash
            df['product_id'] = df['product_name'].astype(str).apply(hash) % (10**8)
        
        unique_orders = df['order_id'].nunique()
        unique_products = df['product_id'].nunique()
        avg_items = len(df) / unique_orders if unique_orders > 0 else 0
        
        logger.info(f"Unique orders: {unique_orders}, Unique products: {unique_products}")
        logger.info(f"Average items per order: {avg_items:.2f}")
    
    def _clean_dataframe(self, df: pd.DataFrame, df_name: str) -> pd.DataFrame:
        """Clean dataframe"""
        logger.info(f"Cleaning {df_name}")
        df_clean = df.copy()
        
        # Handle numeric columns
        numeric_cols = df_clean.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if df_clean[col].isnull().sum() > 0:
                df_clean[col] = df_clean[col].fillna(0)
        
        # Handle categorical columns
        categorical_cols = df_clean.select_dtypes(include=['object']).columns
        for col in categorical_cols:
            if df_clean[col].isnull().sum() > 0:
                df_clean[col] = df_clean[col].fillna('unknown')
        
        # Clean string columns
        string_cols = df_clean.select_dtypes(include=['object']).columns
        for col in string_cols:
            df_clean[col] = df_clean[col].astype(str).str.strip().replace(['', 'nan', 'None'], 'unknown')
        
        return df_clean
    
    def _calculate_budget_thresholds(self, total_spent_series: pd.Series) -> None:
        """Calculate budget thresholds dynamically based on data percentiles"""
        logger.info("Calculating budget thresholds based on data distribution")
        
        # Use 33rd and 66th percentiles to divide into low, medium, high budgets
        p33 = total_spent_series.quantile(0.33)
        p66 = total_spent_series.quantile(0.66)
        
        self.budget_thresholds['low'] = float(p33)
        self.budget_thresholds['medium'] = float(p66)
        
        # Calculate distribution counts
        low_count = (total_spent_series <= p33).sum()
        medium_count = ((total_spent_series > p33) & (total_spent_series <= p66)).sum()
        high_count = (total_spent_series > p66).sum()
        
        self.budget_distribution = {
            'low': int(low_count),
            'medium': int(medium_count),
            'high': int(high_count)
        }
        
        logger.info(f"Budget thresholds: Low=${p33:.2f}, Medium=${p66:.2f}")
        logger.info(f"Budget distribution - Low: {low_count}, Medium: {medium_count}, High: {high_count}")
    
    def _attach_order_totals(self, sales_df: pd.DataFrame, order_stats: pd.DataFrame) -> pd.DataFrame:
        """Attach best available order total metric to grouped stats"""
        df = sales_df.copy()
        amount_column = None
        
        if 'total_spent' in df.columns:
            amount_column = 'total_spent'
            agg_method = 'max'
        elif 'total_item_price' in df.columns:
            amount_column = 'total_item_price'
            agg_method = 'sum'
        elif 'quantity' in df.columns and 'unit_price' in df.columns:
            df['__line_total'] = df['quantity'].astype(float) * df['unit_price'].astype(float)
            amount_column = '__line_total'
            agg_method = 'sum'
        
        if amount_column:
            amount_df = df.groupby('order_id')[amount_column].agg(agg_method).reset_index()
            amount_df.rename(columns={amount_column: 'total_spent'}, inplace=True)
            order_stats = order_stats.merge(amount_df, on='order_id', how='left')
        else:
            order_stats['total_spent'] = np.random.uniform(10, 200, len(order_stats))
        
        order_stats['total_spent'] = order_stats['total_spent'].fillna(order_stats['total_spent'].median())
        return order_stats
    
    def _attach_time_context(self, sales_df: pd.DataFrame, order_ids: pd.Series) -> pd.DataFrame:
        """Build time context dataframe"""
        if 'time_of_day' in sales_df.columns:
            time_info = sales_df.groupby('order_id')['time_of_day'].first().reset_index()
            time_info['time_of_day'] = time_info['time_of_day'].fillna('afternoon')
            if 'date' in sales_df.columns:
                order_dates = sales_df.groupby('order_id')['date'].first().reset_index()
                order_dates['day_of_week'] = pd.to_datetime(order_dates['date'], errors='coerce').dt.day_name().fillna('Unknown')
                time_info = time_info.merge(order_dates[['order_id', 'day_of_week']], on='order_id', how='left')
            else:
                time_info['day_of_week'] = 'Unknown'
        elif 'timestamp' in sales_df.columns:
            time_info = sales_df.groupby('order_id')['timestamp'].first().reset_index()
            time_info['timestamp'] = pd.to_datetime(time_info['timestamp'], errors='coerce')
            time_info['hour'] = time_info['timestamp'].dt.hour.fillna(12)
            time_info['time_of_day'] = time_info['hour'].apply(self._categorize_time_of_day)
            time_info['day_of_week'] = time_info['timestamp'].dt.day_name().fillna('Unknown')
        else:
            time_info = pd.DataFrame({'order_id': order_ids})
            time_info['time_of_day'] = np.random.choice(['morning', 'afternoon', 'evening'], len(time_info))
            time_info['day_of_week'] = np.random.choice(
                ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
                len(time_info)
            )
        
        return time_info
    
    def _attach_age_context(self, sales_df: pd.DataFrame, order_ids: pd.Series) -> pd.DataFrame:
        """Create age group context for each order if possible"""
        if 'customer_age' in sales_df.columns:
            age_info = sales_df.groupby('order_id')['customer_age'].median().reset_index()
            age_info['age_group'] = age_info['customer_age'].apply(self._categorize_age)
        else:
            age_info = pd.DataFrame({'order_id': order_ids, 'age_group': 'adult'})
        
        return age_info
    
    def prepare_transactions_with_context(self, sales_df: pd.DataFrame) -> List[Dict]:
        """Prepare transactions with contextual information"""
        logger.info("Preparing transactions with enhanced context")
        
        if len(sales_df) < 5:
            return self._prepare_small_dataset_transactions(sales_df)
        
        # Group products by order
        order_products = sales_df.groupby('order_id')['product_id'].apply(list).reset_index()
        
        # Calculate order statistics
        order_stats = sales_df.groupby('order_id').agg({
            'product_id': 'count'
        }).reset_index()
        order_stats.rename(columns={'product_id': 'item_count'}, inplace=True)
        
        # Calculate order totals when possible, fallback to synthetic data for demos
        order_stats = self._attach_order_totals(sales_df, order_stats)

        # Calculate budget thresholds dynamically
        self._calculate_budget_thresholds(order_stats['total_spent'])
        
        # Add time context
        time_info = self._attach_time_context(sales_df, order_stats['order_id'])

        # Add demographic context
        age_info = self._attach_age_context(sales_df, order_stats['order_id'])
        
        # Merge everything
        context_df = order_products.merge(order_stats, on='order_id')
        context_df = context_df.merge(time_info[['order_id', 'time_of_day', 'day_of_week']], on='order_id')
        context_df = context_df.merge(age_info[['order_id', 'age_group']], on='order_id', how='left')
        context_df['age_group'] = context_df['age_group'].fillna('adult')
        
        # Apply categorization
        context_df['budget_segment'] = context_df['total_spent'].apply(self._categorize_budget)
        context_df['basket_size'] = context_df['item_count'].apply(self._categorize_basket_size)
        
        # Convert to transaction contexts
        self.transaction_contexts = []
        for _, row in context_df.iterrows():
            if isinstance(row['product_id'], list) and len(row['product_id']) > 0:
                self.transaction_contexts.append({
                    'order_id': row['order_id'],
                    'products': row['product_id'],
                    'budget': row['budget_segment'],
                    'time_of_day': row['time_of_day'],
                    'day_of_week': row['day_of_week'],
                    'age_group': row['age_group'],
                    'basket_size': row['basket_size'],
                    'total_spent': row['total_spent'],
                    'item_count': row['item_count']
                })
        
        logger.info(f"Prepared {len(self.transaction_contexts)} transactions")
        return self.transaction_contexts
    
    def _prepare_small_dataset_transactions(self, sales_df: pd.DataFrame) -> List[Dict]:
        """Handle small datasets"""
        logger.info("Using small dataset optimization")
        
        order_products = sales_df.groupby('order_id')['product_id'].apply(list).reset_index()
        
        self.transaction_contexts = []
        for _, row in order_products.iterrows():
            if isinstance(row['product_id'], list) and len(row['product_id']) > 0:
                self.transaction_contexts.append({
                    'order_id': row['order_id'],
                    'products': row['product_id'],
                    'budget': 'medium',
                    'time_of_day': 'afternoon',
                    'day_of_week': 'Unknown',
                    'age_group': 'adult',
                    'basket_size': 'small',
                    'total_spent': 50,
                    'item_count': len(row['product_id'])
                })
        
        logger.info(f"Prepared {len(self.transaction_contexts)} simplified transactions")
        return self.transaction_contexts
    
    def generate_smart_rules(self, adaptive_thresholds: bool = True) -> None:
        """Generate association rules with configured thresholds"""
        logger.info("Generating association rules")
        
        if len(self.transaction_contexts) < 5:
            logger.warning("Too few transactions for meaningful rules")
            return
        
        # Use configured thresholds from self.thresholds
        min_support = self.thresholds['association_rules']['min_support']
        min_confidence = self.thresholds['association_rules']['min_confidence']
        min_lift = self.thresholds['association_rules'].get('min_lift', 1.0)
        
        # Apply adaptive threshold adjustment if enabled and data is loaded
        if adaptive_thresholds:
            data_size = len(self.transaction_contexts)
            if data_size < 20:
                min_support = max(min_support, 0.1)
                min_confidence = max(min_confidence, 0.5)
            elif data_size < 100:
                min_support = max(min_support, 0.05)
                min_confidence = max(min_confidence, 0.4)
            # For large datasets, keep the configured thresholds as they are likely stricter
        
        logger.info(f"Using configured thresholds: support={min_support}, confidence={min_confidence}, lift={min_lift}")
        logger.info(self.get_threshold_config_summary())
        
        # Generate general rules
        all_transactions = [tx['products'] for tx in self.transaction_contexts]
        general_rules = self._generate_rules_with_fallback(all_transactions, min_support, min_confidence, min_lift)
        
        if not general_rules.empty:
            self.contextual_rules['general'] = general_rules
            logger.info(f"Generated {len(general_rules)} general rules")
        
        # Generate context-specific rules
        if len(self.transaction_contexts) >= 20:
            self._generate_context_rules(min_support * 1.5, min_confidence, min_lift)
    
    def _generate_rules_with_fallback(self, transactions_list: List, min_support: float, 
                                     min_confidence: float, min_lift: float = 1.0) -> pd.DataFrame:
        """Generate rules with fallback for small datasets"""
        if len(transactions_list) < 3:
            return pd.DataFrame()
        
        try:
            # Clean transactions
            cleaned_transactions = []
            for transaction in transactions_list:
                cleaned_transaction = [str(int(item)) for item in transaction if pd.notna(item)]
                if cleaned_transaction:
                    cleaned_transactions.append(cleaned_transaction)
            
            if len(cleaned_transactions) < 3:
                return pd.DataFrame()
            
            # Adjust for small datasets
            if len(cleaned_transactions) < 10:
                min_support = max(0.05, min_support)
                max_len = 2
            else:
                max_len = 3
            
            # Encode transactions
            te = TransactionEncoder()
            te_ary = te.fit(cleaned_transactions).transform(cleaned_transactions)
            encoded_df = pd.DataFrame(te_ary, columns=te.columns_)
            
            # Find frequent itemsets
            frequent_itemsets = apriori(
                encoded_df,
                min_support=min_support,
                use_colnames=True,
                low_memory=True,
                max_len=max_len
            )
            
            if frequent_itemsets.empty:
                return pd.DataFrame()
            
            # Generate association rules
            rules = association_rules(
                frequent_itemsets,
                metric="confidence",
                min_threshold=min_confidence
            )
            
            if not rules.empty:
                rules = rules[rules['lift'] >= min_lift]
                rules = rules.sort_values(['confidence', 'support'], ascending=False)
            
            return rules
        
        except Exception as e:
            logger.error(f"Error generating rules: {e}")
            return pd.DataFrame()
    
    def _generate_context_rules(self, min_support: float, min_confidence: float, min_lift: float = 1.0) -> None:
        """Generate context-specific rules with configured thresholds"""
        contexts = [
            ('time_of_day', ['morning', 'afternoon', 'evening', 'night']),
            ('budget', ['low', 'medium', 'high']),
            ('age_group', ['teen', 'young_adult', 'adult', 'senior']),
            ('basket_size', ['small', 'medium', 'large'])
        ]
        
        for context_type, values in contexts:
            for value in values:
                context_key = f"{context_type}_{value}"
                context_transactions = [
                    tx['products'] for tx in self.transaction_contexts
                    if tx[context_type] == value
                ]
                
                if len(context_transactions) >= 5:
                    context_rules = self._generate_rules_with_fallback(
                        context_transactions, min_support, min_confidence, min_lift
                    )
                    
                    if not context_rules.empty:
                        self.contextual_rules[context_key] = context_rules
                        logger.info(f"Generated {len(context_rules)} rules for {context_key}")
    
    def _categorize_time_of_day(self, hour: int) -> str:
        """Categorize hour into time segments"""
        if pd.isna(hour):
            return 'afternoon'
        if 5 <= hour < 12:
            return 'morning'
        elif 12 <= hour < 17:
            return 'afternoon'
        elif 17 <= hour < 22:
            return 'evening'
        else:
            return 'night'
    
    def _categorize_age(self, age: float) -> str:
        """Categorize shopper age into configured age groups"""
        if pd.isna(age):
            return 'adult'
        
        try:
            age = float(age)
        except (ValueError, TypeError):
            return 'adult'
        
        age_limits = self.thresholds['age_groups']
        if age <= age_limits['teen']:
            return 'teen'
        elif age <= age_limits['young_adult']:
            return 'young_adult'
        elif age <= age_limits['adult']:
            return 'adult'
        else:
            return 'senior'
    
    def _categorize_budget(self, total_amount: float) -> str:
        """Categorize total order amount based on configured thresholds"""
        low_threshold = self.thresholds['budget']['low']
        medium_threshold = self.thresholds['budget']['medium']
        
        if total_amount <= low_threshold:
            return 'low'
        elif total_amount <= medium_threshold:
            return 'medium'
        else:
            return 'high'
    
    def _categorize_basket_size(self, item_count: int) -> str:
        """Categorize basket size based on configured thresholds"""
        small_max = self.thresholds['basket_size']['small']
        medium_max = self.thresholds['basket_size']['medium']
        
        if item_count <= small_max:
            return 'small'
        elif item_count <= medium_max:
            return 'medium'
        else:
            return 'large'
    
    def _get_product_name(self, product_id: int) -> str:
        """Get product name from ID"""
        if self.products_df is not None and not self.products_df.empty:
            match = self.products_df[self.products_df['product_id'] == product_id]
            if not match.empty:
                return match['product_name'].iloc[0]
        return f"Product_{product_id}"
    
    def get_recommendations(self, product_id: int, context: Dict = None, top_n: int = 5) -> List[Dict]:
        """Get context-aware recommendations"""
        if context is None:
            context = {'budget': 'medium', 'time_of_day': 'afternoon'}
        
        recommendations = []
        
        # Build context keys
        context_keys = [f"{key}_{value}" for key, value in context.items()]
        
        # Try context-specific rules first
        for context_key in context_keys:
            if context_key in self.contextual_rules:
                rules = self.contextual_rules[context_key]
                recommendations.extend(self._extract_recommendations_from_rules(rules, product_id, context_key))
        
        # Fallback to general rules
        if not recommendations and 'general' in self.contextual_rules:
            rules = self.contextual_rules['general']
            recommendations.extend(self._extract_recommendations_from_rules(rules, product_id, 'general'))
        
        # Final fallback: popular products
        if not recommendations:
            recommendations = self._get_popular_product_fallback(product_id, top_n)
        
        recommendations.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        return recommendations[:top_n]
    
    def _extract_recommendations_from_rules(self, rules: pd.DataFrame, product_id: int, 
                                           context_key: str) -> List[Dict]:
        """Extract recommendations from rules"""
        recommendations = []
        seen_products = set()
        input_product_str = str(product_id)
        
        for _, rule in rules.iterrows():
            antecedents = [str(item) for item in rule['antecedents']]
            if input_product_str in antecedents:
                consequents = [str(item) for item in rule['consequents']]
                for consequent_id in consequents:
                    if consequent_id != input_product_str and consequent_id not in seen_products:
                        consequent_id_int = int(consequent_id)
                        product_name = self._get_product_name(consequent_id_int)
                        recommendations.append({
                            'product_id': consequent_id_int,
                            'product_name': product_name,
                            'confidence': float(rule['confidence']),
                            'lift': float(rule['lift']),
                            'context': context_key,
                            'explanation': f"Frequently bought together (Confidence: {rule['confidence']:.1%})"
                        })
                        seen_products.add(consequent_id)
        
        return recommendations
    
    def _get_popular_product_fallback(self, exclude_product_id: int, top_n: int) -> List[Dict]:
        """Fallback to popular products"""
        if not self.transaction_contexts:
            return []
        
        product_counts = {}
        for tx in self.transaction_contexts:
            for product_id in tx['products']:
                if product_id != exclude_product_id:
                    product_counts[product_id] = product_counts.get(product_id, 0) + 1
        
        popular_products = sorted(product_counts.items(), key=lambda x: x[1], reverse=True)[:top_n]
        
        recommendations = []
        for product_id, count in popular_products:
            recommendations.append({
                'product_id': product_id,
                'product_name': self._get_product_name(product_id),
                'confidence': 0.1,
                'lift': 1.0,
                'context': 'popular_fallback',
                'explanation': f"Popular product (appears in {count} transactions)"
            })
        
        return recommendations
    
    def calculate_reorder_rates(self) -> Dict[int, float]:
        """Calculate reorder rates for each product"""
        reorder_rates = {}
        product_orders = {}
        
        # Track which products appear in which orders
        for tx in self.transaction_contexts:
            for product in tx['products']:
                # Normalize product to int
                try:
                    product_int = int(product)
                except (ValueError, TypeError):
                    logger.warning(f"Could not convert product {product} to int")
                    continue
                    
                if product_int not in product_orders:
                    product_orders[product_int] = []
                product_orders[product_int].append(tx['order_id'])
        
        # Calculate reorder rate: (times bought - 1) / total transactions
        total_transactions = len(self.transaction_contexts)
        for product_id, orders in product_orders.items():
            times_purchased = len(orders)
            unique_orders = len(set(orders))
            # Reorder rate is percentage of repeat purchases (unique orders product appears in)
            reorder_rate = ((unique_orders - 1) / unique_orders * 100) if unique_orders > 1 else 0.0
            reorder_rates[product_id] = reorder_rate
        
        logger.info(f"Calculated reorder rates for {len(reorder_rates)} products: {[f'{k}:{v:.1f}%' for k,v in list(reorder_rates.items())[:5]]}")
        return reorder_rates
    
    def generate_analytics_summary(self) -> Dict:
        """Generate analytics summary"""
        if not self.transaction_contexts:
            return {}
        
        total_products = sum(len(tx['products']) for tx in self.transaction_contexts)
        unique_products = len(set(product for tx in self.transaction_contexts for product in tx['products']))
        
        # Context distribution
        time_dist = {}
        budget_dist = {}
        age_dist = {}
        basket_dist = {}
        
        for tx in self.transaction_contexts:
            time_dist[tx['time_of_day']] = time_dist.get(tx['time_of_day'], 0) + 1
            budget_dist[tx['budget']] = budget_dist.get(tx['budget'], 0) + 1
            age_key = tx.get('age_group', 'unknown')
            age_dist[age_key] = age_dist.get(age_key, 0) + 1
            basket_dist[tx['basket_size']] = basket_dist.get(tx['basket_size'], 0) + 1
        
        # Use calculated budget distribution if available
        if self.budget_distribution:
            budget_dist = self.budget_distribution
        
        # Calculate reorder rates
        reorder_rates = self.calculate_reorder_rates()
        avg_reorder_rate = sum(reorder_rates.values()) / len(reorder_rates) if reorder_rates else 0.0
        
        return {
            'total_transactions': len(self.transaction_contexts),
            'total_products': total_products,
            'unique_products': unique_products,
            'avg_basket_size': total_products / len(self.transaction_contexts),
            'time_distribution': time_dist,
            'budget_distribution': budget_dist,
            'age_distribution': age_dist,
            'basket_size_distribution': basket_dist,
            'total_rules': sum(len(rules) for rules in self.contextual_rules.values()),
            'contexts_available': list(self.contextual_rules.keys()),
            'thresholds_used': self.thresholds,
            'threshold_config_summary': self.get_threshold_config_summary(),
            'reorder_rates': reorder_rates,
            'avg_reorder_rate': avg_reorder_rate
        }
