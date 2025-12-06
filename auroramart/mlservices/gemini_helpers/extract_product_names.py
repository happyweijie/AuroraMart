from .get_product_catalog import get_product_catalog
from rapidfuzz import fuzz

def extract_entities_from_catalog(user_message: str, product_catalog: list, threshold: int = 80) -> dict:
    """
    Extracts products, inferred brands, and categories from a user's message.
    
    Args:
        user_message: Raw user input string.
        product_catalog: List of product dictionaries:
            [{'name': 'L’Oreal UltraShine Lipstick – Red Velvet', 'category': 'Beauty & Personal Care'}, ...]
        threshold: Fuzzy match threshold (0-100).
    
    Returns:
        Dictionary with keys: 'products', 'brands', 'categories'.
    """
    # print(product_catalog)
    normalized_msg = user_message.lower()
    results = {'products': [], 'brands': [], 'categories': []}

    for product in product_catalog:
        name = product['name']
        category = product.get('category', '')
        
        if fuzz.partial_ratio(name.lower(), normalized_msg) >= threshold:
            results['products'].append(name)
            
            # Infer brand from first 1-2 words of the product name
            brand_words = name.split()[:1]
            brand = ' '.join(brand_words)
            results['brands'].append(brand)
            
            if category:
                results['categories'].append(category)

    # Remove duplicates
    results['products'] = list(set(results['products']))
    results['brands'] = list(set(results['brands']))
    results['categories'] = list(set(results['categories']))

    # print(results)
    return results
