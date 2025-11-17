"""
Threshold Configurator
Analyzes data and suggests optimal thresholds for analytics
Allows users to override suggestions with custom values
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)


class ThresholdConfigurator:
    """Analyzes data and suggests optimal thresholds"""
    
    def __init__(self):
        self.data_analysis = {}
        self.suggested_thresholds = {}
        self.user_thresholds = {}
    
    def analyze_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze uploaded data and provide insights for threshold suggestions
        
        Args:
            df: DataFrame with sales/transaction data
            
        Returns:
            Dictionary with data analysis results
        """
        self.data_analysis = {
            'total_records': len(df),
            'total_transactions': df['order_id'].nunique() if 'order_id' in df.columns else 0,
            'unique_products': df['product_id'].nunique() if 'product_id' in df.columns else 0,
            'date_range': self._get_date_range(df),
            'spending_analysis': self._analyze_spending(df),
            'basket_analysis': self._analyze_baskets(df),
            'demographic_coverage': self._analyze_demographics(df),
            'data_quality_score': self._calculate_quality_score(df)
        }
        
        logger.info(f"Data analysis complete. Quality score: {self.data_analysis['data_quality_score']}")
        return self.data_analysis
    
    def suggest_thresholds(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Suggest optimal thresholds based on data analysis
        
        Args:
            df: DataFrame with sales/transaction data
            
        Returns:
            Dictionary with suggested threshold values
        """
        # Analyze data first
        self.analyze_data(df)
        
        # Calculate thresholds based on data characteristics
        self.suggested_thresholds = {
            'budget_thresholds': self._suggest_budget_thresholds(df),
            'association_rules': self._suggest_association_thresholds(df),
            'basket_size_categories': self._suggest_basket_categories(df),
            'age_group_boundaries': self._suggest_age_boundaries(),
            'lift_threshold': self._suggest_lift_threshold(df),
            'data_quality_threshold': 0.7
        }
        
        logger.info(f"Thresholds suggested for data with {len(df)} records")
        return {
            'analysis': self.data_analysis,
            'suggestions': self.suggested_thresholds
        }
    
    def _get_date_range(self, df: pd.DataFrame) -> Dict[str, str]:
        """Get date range from data"""
        if 'date' in df.columns:
            try:
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
                min_date = df['date'].min()
                max_date = df['date'].max()
                days_span = (max_date - min_date).days
                return {
                    'start_date': str(min_date),
                    'end_date': str(max_date),
                    'days_span': days_span
                }
            except:
                return {'start_date': 'Unknown', 'end_date': 'Unknown', 'days_span': 0}
        return {'start_date': 'Unknown', 'end_date': 'Unknown', 'days_span': 0}
    
    def _analyze_spending(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze spending patterns"""
        if 'order_value' in df.columns or 'total_spent' in df.columns:
            spend_col = 'order_value' if 'order_value' in df.columns else 'total_spent'
            spending = df.groupby('order_id')[spend_col].sum() if 'order_id' in df.columns else df[spend_col]
            
            return {
                'min': float(spending.min()),
                'max': float(spending.max()),
                'mean': float(spending.mean()),
                'median': float(spending.median()),
                'std': float(spending.std()),
                'percentile_33': float(spending.quantile(0.33)),
                'percentile_66': float(spending.quantile(0.66)),
                'percentile_75': float(spending.quantile(0.75))
            }
        return {}
    
    def _analyze_baskets(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze basket size patterns"""
        if 'order_id' in df.columns:
            basket_sizes = df.groupby('order_id').size()
            
            return {
                'min_items': int(basket_sizes.min()),
                'max_items': int(basket_sizes.max()),
                'avg_items': float(basket_sizes.mean()),
                'median_items': int(basket_sizes.median()),
                'percentile_33': int(basket_sizes.quantile(0.33)),
                'percentile_66': int(basket_sizes.quantile(0.66))
            }
        return {}
    
    def _analyze_demographics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze available demographic data"""
        demographics = {}
        
        demographic_cols = {
            'customer_age': 'age',
            'customer_gender': 'gender',
            'occasion': 'occasion',
            'time_of_day': 'time_of_day'
        }
        
        for col, name in demographic_cols.items():
            if col in df.columns:
                unique_vals = df[col].nunique()
                demographics[name] = {
                    'available': True,
                    'unique_values': int(unique_vals),
                    'missing_pct': float((df[col].isnull().sum() / len(df)) * 100)
                }
            else:
                demographics[name] = {'available': False}
        
        return demographics
    
    def _calculate_quality_score(self, df: pd.DataFrame) -> float:
        """
        Calculate data quality score (0-1)
        
        Factors:
        - Data completeness
        - Required columns presence
        - Data variety
        """
        score = 0.0
        
        # Check for required columns
        required_cols = ['order_id', 'product_id']
        present_required = sum(1 for col in required_cols if col in df.columns)
        score += (present_required / len(required_cols)) * 0.3
        
        # Check for optional/demographic columns
        optional_cols = ['order_value', 'customer_age', 'customer_gender', 'occasion', 'time_of_day', 'date']
        present_optional = sum(1 for col in optional_cols if col in df.columns)
        score += (present_optional / len(optional_cols)) * 0.4
        
        # Check data completeness
        completeness = 1 - (df.isnull().sum().sum() / (len(df) * len(df.columns)))
        score += completeness * 0.3
        
        return round(score, 2)
    
    def _suggest_budget_thresholds(self, df: pd.DataFrame) -> Dict[str, float]:
        """Suggest budget category thresholds"""
        if 'order_value' in df.columns or 'total_spent' in df.columns:
            spend_col = 'order_value' if 'order_value' in df.columns else 'total_spent'
            if 'order_id' in df.columns:
                spending = df.groupby('order_id')[spend_col].sum()
            else:
                spending = df[spend_col]
            
            return {
                'low': round(float(spending.quantile(0.33)), 2),
                'medium': round(float(spending.quantile(0.66)), 2),
                'high': round(float(spending.max()), 2)
            }
        
        # Default thresholds if no spending data
        return {'low': 25.0, 'medium': 75.0, 'high': 500.0}
    
    def _suggest_association_thresholds(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        Suggest association rule thresholds based on data size
        
        Rules:
        - Smaller datasets need more lenient thresholds
        - Larger datasets can use stricter thresholds
        """
        num_transactions = df['order_id'].nunique() if 'order_id' in df.columns else len(df)
        num_products = df['product_id'].nunique() if 'product_id' in df.columns else 0
        
        if num_transactions < 20:
            # Very small dataset - be very lenient
            return {
                'min_support': 0.10,
                'min_confidence': 0.40,
                'recommended_support': 0.10,
                'recommended_confidence': 0.40
            }
        elif num_transactions < 50:
            # Small dataset
            return {
                'min_support': 0.05,
                'min_confidence': 0.35,
                'recommended_support': 0.05,
                'recommended_confidence': 0.35
            }
        elif num_transactions < 100:
            # Medium dataset
            return {
                'min_support': 0.03,
                'min_confidence': 0.30,
                'recommended_support': 0.03,
                'recommended_confidence': 0.30
            }
        elif num_transactions < 500:
            # Larger dataset
            return {
                'min_support': 0.02,
                'min_confidence': 0.25,
                'recommended_support': 0.02,
                'recommended_confidence': 0.25
            }
        else:
            # Very large dataset
            return {
                'min_support': 0.01,
                'min_confidence': 0.20,
                'recommended_support': 0.01,
                'recommended_confidence': 0.20
            }
    
    def _suggest_basket_categories(self, df: pd.DataFrame) -> Dict[str, Dict[str, int]]:
        """Suggest basket size categories based on data"""
        if 'order_id' in df.columns:
            basket_sizes = df.groupby('order_id').size()
            
            # Use percentiles to define categories
            p33 = int(basket_sizes.quantile(0.33))
            p66 = int(basket_sizes.quantile(0.66))
            
            return {
                'small': {'min': 1, 'max': max(p33, 2)},
                'medium': {'min': max(p33, 2) + 1, 'max': p66},
                'large': {'min': p66 + 1, 'max': 1000}
            }
        
        # Default categories
        return {
            'small': {'min': 1, 'max': 3},
            'medium': {'min': 4, 'max': 8},
            'large': {'min': 9, 'max': 1000}
        }
    
    def _suggest_age_boundaries(self) -> Dict[str, Dict[str, int]]:
        """Suggest age group boundaries - standard across all datasets"""
        return {
            'teen': {'min': 0, 'max': 17},
            'young_adult': {'min': 18, 'max': 24},
            'adult': {'min': 25, 'max': 59},
            'senior': {'min': 60, 'max': 120}
        }
    
    def _suggest_lift_threshold(self, df: pd.DataFrame) -> float:
        """Suggest lift threshold for association rules"""
        # Lift > 1.0 indicates positive correlation
        # Suggestion: 1.0 (neutral, captures any positive correlation)
        return 1.0
    
    def set_user_thresholds(self, thresholds: Dict[str, Any]) -> None:
        """
        Store user-configured thresholds
        
        Args:
            thresholds: Dictionary with user-configured threshold values
        """
        self.user_thresholds = thresholds
        logger.info(f"User thresholds set: {thresholds}")
    
    def get_active_thresholds(self) -> Dict[str, Any]:
        """
        Get active thresholds (user-defined or suggested defaults)
        
        Returns:
            Dictionary with active threshold values
        """
        if self.user_thresholds:
            return self.user_thresholds
        return self.suggested_thresholds
    
    def export_threshold_config(self) -> Dict[str, Any]:
        """Export complete threshold configuration for logging/auditing"""
        return {
            'data_analysis': self.data_analysis,
            'suggested_thresholds': self.suggested_thresholds,
            'user_thresholds': self.user_thresholds,
            'active_thresholds': self.get_active_thresholds(),
            'timestamp': pd.Timestamp.now().isoformat()
        }