import re

def extract_order_id(user_message: str) -> str | None:
    """
    Extracts an Order ID (a number) that may optionally be preceded by a '#' or 'order'.
    """
    # 1. Normalize the message to ensure consistent processing
    normalized_msg = user_message.lower()
    
    # 2. Define regex pattern to capture order ID
    pattern = r'(?:order\s*#?\s*|#\s*)?(\d+)'
    
    # Search the entire string for the pattern
    match = re.search(pattern, normalized_msg)
    
    if match:
        # The captured group (1) is the actual number (the ID)
        return match.group(1)
    
    return None