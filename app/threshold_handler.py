"""
Threshold Configuration Handler
Manages threshold workflow: analysis → suggestions → configuration → storage
"""

import logging
from typing import Dict, Any
from app.threshold_configurator import ThresholdConfigurator

logger = logging.getLogger(__name__)


class ThresholdHandler:
    """Handles threshold configuration workflow"""
    
    def __init__(self):
        self.configurator = ThresholdConfigurator()
    
    def analyze_and_suggest(self, df) -> Dict[str, Any]:
        """
        Analyze data and generate threshold suggestions
        
        Args:
            df: DataFrame with uploaded data
            
        Returns:
            Dictionary with analysis and suggestions
        """
        try:
            result = self.configurator.suggest_thresholds(df)
            logger.info("Threshold suggestions generated successfully")
            return result
        except Exception as e:
            logger.error(f"Error suggesting thresholds: {e}")
            return {
                'analysis': {'error': str(e)},
                'suggestions': self._get_default_thresholds()
            }
    
    def form_to_config(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert form submission to threshold configuration
        
        Args:
            form_data: Dictionary from form submission
            
        Returns:
            Standardized threshold configuration
        """
        config = {
            'budget_thresholds': {
                'low': float(form_data.get('budget_low', 25.0)),
                'medium': float(form_data.get('budget_medium', 75.0))
            },
            'association_rules': {
                'min_support': float(form_data.get('min_support', 0.05)),
                'min_confidence': float(form_data.get('min_confidence', 0.3)),
                'min_lift': float(form_data.get('min_lift', 1.0))
            },
            'basket_size_categories': {
                'small': {'max': int(form_data.get('basket_small_max', 3))},
                'medium': {'max': int(form_data.get('basket_medium_max', 8))}
            },
            'age_group_boundaries': {
                'teen': {'max': int(form_data.get('age_teen_max', 17))},
                'young_adult': {'max': int(form_data.get('age_young_adult_max', 24))},
                'adult': {'max': int(form_data.get('age_adult_max', 59))}
            }
        }
        
        logger.debug(f"Form converted to config: {config}")
        return config
    
    def generate_recommendations(self, data_analysis: Dict[str, Any], 
                                suggestions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate recommendations for threshold adjustments based on data characteristics
        
        Args:
            data_analysis: Data analysis results
            suggestions: Suggested thresholds
            
        Returns:
            Dictionary with recommendations and reasoning
        """
        recommendations = {
            'budget_recommendations': [],
            'association_recommendations': [],
            'basket_size_recommendations': [],
            'age_group_recommendations': [],
            'overall_quality': 'good'
        }
        
        try:
            spending = data_analysis.get('spending_analysis', {})
            basket = data_analysis.get('basket_analysis', {})
            transactions = data_analysis.get('total_transactions', 0)
            quality_score = data_analysis.get('data_quality_score', 0.5)
            
            # Budget recommendations
            if spending.get('mean', 0) > 100:
                recommendations['budget_recommendations'].append({
                    'type': 'info',
                    'message': 'Your average order value is high (KES %.2f). Consider adjusting budget thresholds upward.' % spending.get('mean', 0)
                })
            
            # Association rules recommendations
            if transactions < 50:
                recommendations['association_recommendations'].append({
                    'type': 'warning',
                    'message': f'Limited data ({transactions} transactions). Lower support/confidence thresholds recommended for meaningful rules.'
                })
                recommendations['overall_quality'] = 'limited'
            elif transactions < 100:
                recommendations['association_recommendations'].append({
                    'type': 'info',
                    'message': f'Moderate data size ({transactions} transactions). Current suggestions are appropriate.'
                })
            else:
                recommendations['association_recommendations'].append({
                    'type': 'success',
                    'message': f'Excellent data volume ({transactions} transactions). You can use stricter thresholds for higher quality rules.'
                })
            
            # Basket size recommendations
            avg_basket = basket.get('mean', 3)
            if avg_basket < 2:
                recommendations['basket_size_recommendations'].append({
                    'type': 'info',
                    'message': f'Low average basket size ({avg_basket:.1f} items). Small basket threshold is appropriate.'
                })
            elif avg_basket > 10:
                recommendations['basket_size_recommendations'].append({
                    'type': 'info',
                    'message': f'High average basket size ({avg_basket:.1f} items). Consider increasing basket size thresholds.'
                })
            
            # Data quality recommendations
            if quality_score < 0.6:
                recommendations['overall_quality'] = 'limited'
                recommendations['budget_recommendations'].append({
                    'type': 'warning',
                    'message': 'Data quality is below optimal. Verify your CSV format and data completeness.'
                })
            
            logger.info(f"Recommendations generated. Quality: {recommendations['overall_quality']}")
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
        
        return recommendations
    
    def _get_default_thresholds(self) -> Dict[str, Any]:
        """Get default threshold configuration"""
        return {
            'budget_thresholds': {'low': 25.0, 'medium': 75.0},
            'association_rules': {'min_support': 0.05, 'min_confidence': 0.3, 'min_lift': 1.0},
            'basket_size_categories': {
                'small': {'max': 3},
                'medium': {'max': 8}
            },
            'age_group_boundaries': {
                'teen': {'max': 17},
                'young_adult': {'max': 24},
                'adult': {'max': 59}
            }
        }
    
    def get_display_suggestions(self, suggestions: Dict[str, Any]) -> Dict[str, Any]:
        """Format suggestions for display in UI"""
        try:
            s = suggestions.get('suggestions', {})
            return {
                'budget_low': s.get('budget_thresholds', {}).get('low', 25.0),
                'budget_medium': s.get('budget_thresholds', {}).get('medium', 75.0),
                'min_support': s.get('association_rules', {}).get('min_support', 0.05),
                'min_confidence': s.get('association_rules', {}).get('min_confidence', 0.3),
                'min_lift': s.get('association_rules', {}).get('min_lift', 1.0),
                'basket_small_max': s.get('basket_size_categories', {}).get('small', {}).get('max', 3),
                'basket_medium_max': s.get('basket_size_categories', {}).get('medium', {}).get('max', 8),
                'age_teen_max': s.get('age_group_boundaries', {}).get('teen', {}).get('max', 17),
                'age_young_adult_max': s.get('age_group_boundaries', {}).get('young_adult', {}).get('max', 24),
                'age_adult_max': s.get('age_group_boundaries', {}).get('adult', {}).get('max', 59)
            }
        except Exception as e:
            logger.error(f"Error formatting suggestions: {e}")
            return self._get_default_display_suggestions()
    
    def _get_default_display_suggestions(self) -> Dict[str, Any]:
        """Get default display suggestions"""
        return {
            'budget_low': 25.0,
            'budget_medium': 75.0,
            'min_support': 0.05,
            'min_confidence': 0.3,
            'min_lift': 1.0,
            'basket_small_max': 3,
            'basket_medium_max': 8,
            'age_teen_max': 17,
            'age_young_adult_max': 24,
            'age_adult_max': 59
        }