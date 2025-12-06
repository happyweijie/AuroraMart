from .get_product_catalog import get_product_catalog

def extract_product_name(user_message: str, product_catalog=get_product_catalog()) -> list:
    """
    Checks the user's message against a cached list of known product names.
    
    Args:
        user_message: The raw text input from the user.
        product_catalog: A list of known product names/SKUs (e.g., ['PureGlow Makeup Glow', 'UltraShine Lipstick']).
        
    Returns:
        A list of matching product names found in the message.
    """
    normalized_msg = user_message.lower()
    found_products = []
    
    # Iterate through the official product names
    for product_name in product_catalog:
        # Use .lower() for case-insensitive comparison
        if product_name.lower() in normalized_msg:
            # Append the original, correctly capitalized product name
            found_products.append(product_name)
            
    # Handle multiple mentions of the same product (keep unique names)
    return list(set(found_products))
