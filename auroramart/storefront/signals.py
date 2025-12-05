from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import Product 
from .utils.caching import CACHE_KEY_PRODUCT_CATALOG

@receiver([post_save, post_delete], sender=Product)
def clear_product_catalog_cache(sender, instance, **kwargs):
    """Deletes the catalog cache whenever a Product is created, updated, or deleted."""
    cache.delete(CACHE_KEY_PRODUCT_CATALOG) 
    print(f"Cache INVALIDATED for {CACHE_KEY_PRODUCT_CATALOG} due to {sender.__name__} change.")
    