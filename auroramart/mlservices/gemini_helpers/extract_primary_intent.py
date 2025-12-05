def extract_primary_intent(user_message: str) -> str:
    """
    Analyzes the user's message to determine the primary context retrieval intent.

    Args:
        user_message: The raw text input from the user.

    Returns:
        A string representing the primary intent ('price', 'stock', 'delivery', 'general'),
        or 'general' if no specific intent keywords are found.
    """
    # Normalize the message for case-insensitive matching
    normalized_msg = user_message.lower()

    # Define the mapping of intents to their keywords
    intent_map = {
        'price': ["how much", "cost", "price", "cheap", "expensive", "discount", "sale"],
        'stock': ["in stock", "available", "out of stock", "inventory", "have it"],
        'delivery': ["where is", "track", "delivered", "eta", "when will", "shipping", "tracking number"],
        # Add 'order_status' if you want a separate category for checking history/details
        'order_status': ["order #", "order number", "my order", "history", "recent purchase"],
    }

    # Iterate through the map to find the best match
    # Checks for the first matching intent and returns it immediately for speed
    for intent, keywords in intent_map.items():
        for keyword in keywords:
            if keyword in normalized_msg:
                # We found a match, return the intent name
                return intent

    # If no specific keywords were found, treat it as a general product/information query
    return 'general'
