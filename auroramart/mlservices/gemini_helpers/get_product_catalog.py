from django.core.cache import cache
from storefront.models import Product 
from storefront.utils.caching import CACHE_KEY_PRODUCT_CATALOG, CACHE_TIMEOUT
from django.db.models import F

def get_product_catalog() -> list:
    """
    Retrieves the list of all product names/SKUs, using cache if available.
    """
    # 1. Try to get the list from the cache
    product_catalog = cache.get(CACHE_KEY_PRODUCT_CATALOG) 

    if product_catalog is None:
        # 2. Cache Miss: Query the database
        print("Cache MISS: Rebuilding product catalog from database.")
        
        # Optimize the query: only select the 'name' and 'sku' fields
        # Using values_list('field', flat=True) returns a list of strings directly, 
        # which is ideal for keyword matching.
        product_catalog = list(
            Product.objects.all().values_list('name', flat=True)
        )
        
        # Include SKUs if they are separate fields
        # sku_list = list(Product.objects.all().values_list('sku', flat=True))
        # product_catalog.extend(sku_list)

        # 3. Store the result in the cache for next time
        cache.set(CACHE_KEY_PRODUCT_CATALOG, product_catalog, CACHE_TIMEOUT) 
        
    return product_catalog
