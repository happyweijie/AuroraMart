import joblib
import logging
from pathlib import Path
from django.apps import apps
from storefront.models import Product

logger = logging.getLogger(__name__)

_PRODUCT_RECOMMENDATIONS = None

def load_recommendations_rules():
    """Load association rules model lazily (only when needed)"""
    global _PRODUCT_RECOMMENDATIONS
    if _PRODUCT_RECOMMENDATIONS is None:
        try:
            # Get app path dynamically to avoid import-time issues
            app_path = Path(apps.get_app_config('admin_panel').path)
            model_path = app_path / 'mlmodels' / 'b2c_products_500_transactions_50k.joblib'
            
            if not model_path.exists():
                logger.warning(f"ML model file not found at: {model_path}")
                return None
            _PRODUCT_RECOMMENDATIONS = joblib.load(model_path)
        except Exception as e:
            logger.error(f"Error loading ML model: {e}")
            return None
    return _PRODUCT_RECOMMENDATIONS

def get_recommendations(loaded_rules, items, metric='confidence', top_n=5):

    recommendations = set()

    for item in items:

        # Find rules where the item is in the antecedents
        matched_rules = loaded_rules[loaded_rules['antecedents'].apply(lambda x: item in x)]
        # Sort by the specified metric and get the top N
        top_rules = matched_rules.sort_values(by=metric, ascending=False).head(top_n)

        for _, row in top_rules.iterrows():

            recommendations.update(row['consequents'])

    # Remove items that are already in the input list
    recommendations.difference_update(items)
    
    return list(recommendations)[:top_n]

def get_product_recommendations(product_skus, top_n=5):
    """Get product recommendations using ML association rules, with fallback"""
    if not product_skus:
        # If no products provided, return popular products across all categories
        return Product.objects.filter(
            is_active=True, 
            archived=False,
            stock__gte=0
        ).order_by('-rating', '-created_at')[:top_n]
    
    # Load rules lazily
    loaded_rules = load_recommendations_rules()
    
    if loaded_rules is None:
        # Fallback if model can't be loaded
        logger.warning("ML model not available, using category-based fallback")
        return _get_category_based_recommendations(product_skus, top_n)
    
    recommendations = get_recommendations(loaded_rules=loaded_rules, items=product_skus, metric='lift', top_n=top_n)

    if recommendations:
        return Product.objects.filter(sku__in=recommendations, is_active=True, archived=False)
    else:
        logger.debug("No recommendations found from ML model, falling back to category-based recommendations.")
        return _get_category_based_recommendations(product_skus, top_n)

def _get_category_based_recommendations(product_skus, top_n=5):
    """Fallback: Get popular products from same categories as input products"""
    try:
        input_products = Product.objects.filter(sku__in=product_skus, is_active=True)
        input_categories = input_products.values_list('category', flat=True).distinct()
        
        if input_categories:
            return Product.objects \
                .filter(category__in=input_categories, is_active=True, archived=False, stock__gte=0) \
                .exclude(sku__in=product_skus) \
                .order_by('-rating', '-created_at')[:top_n]
        else:
            # Ultimate fallback: return popular products
            return Product.objects.filter(
                is_active=True, 
                archived=False,
                stock__gte=0
            ).order_by('-rating', '-created_at')[:top_n]
    except Exception as e:
        logger.error(f"Error in category-based recommendations: {e}")
        return Product.objects.filter(
            is_active=True, 
            archived=False,
            stock__gte=0
        ).order_by('-rating', '-created_at')[:top_n]
