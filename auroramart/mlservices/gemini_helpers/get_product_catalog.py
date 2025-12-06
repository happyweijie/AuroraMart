from django.core.cache import cache
from storefront.models import Product 
from storefront.utils.caching import CACHE_KEY_PRODUCT_CATALOG, CACHE_TIMEOUT

def get_product_catalog() -> list:
    """
    Retrieves the list of all products from the database, using cache if available.
    Each product dict contains: name, sku, category, and inferred brand (first 1-2 words of the name).
    """
    # 1. Try to get the list from the cache
    product_catalog = cache.get(CACHE_KEY_PRODUCT_CATALOG) 

    if product_catalog is None:
        # 2. Cache Miss: Query the database
        print("Cache MISS: Rebuilding product catalog from database.")
        product_catalog = []
        for product in Product.objects.all():
            name = product.name.strip()
            brand = " ".join(name.split()[:2])  # first 1-2 words
            product_catalog.append({
                "name": name,
                "sku": product.sku,
                "category": product.category.name,
                "brand": brand
            })

        # 3. Store the result in the cache for next time
        cache.set(CACHE_KEY_PRODUCT_CATALOG, product_catalog, CACHE_TIMEOUT) 
        
    return product_catalog
