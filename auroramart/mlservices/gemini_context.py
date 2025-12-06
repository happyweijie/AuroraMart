from storefront.models import Order, Product
from .gemini_helpers.extract_primary_intent import extract_primary_intent
from .gemini_helpers.extract_order_id import extract_order_id
from .gemini_helpers.extract_product_names import extract_entities_from_catalog
from .gemini_helpers.get_product_catalog import get_product_catalog

system_persona = "You are Aurora, a friendly and concise e-commerce shopping assistant. Your goal is to answer questions only about products, shipping, and existing orders. If the question is outside these topics, politely redirect the user back to chat with human staff through the Support Chat Page."

shipping_policy = "A general shipping policy is that standard delivery takes **5 to 7 business days** across the region. Use this fact when answering general delivery questions."

def create_gemini_context(session , user_message_text):
    # 1. Initialize Context with System Instructions
    initial_context = (
        f"SYSTEM INSTRUCTION: {system_persona} {shipping_policy}"
        f"\n---\n"
        f"The following is the conversation history and the new query. Stick to the SYSTEM INSTRUCTION at all times."
    )
    
    # Initialize Context with the instructions under the 'user' role
    context = [
            {
                "role": "user",
                "parts": [{"text": initial_context}]
            }
        ] 

    # 2. Add Conversation History
    ROLE_MAP = {
        'user': 'user',
        'assistant': 'model',  
        'ai': 'model',         
    }
    for msg in session.messages.all():
        # Map your Django sender roles to the Gemini API roles
        gemini_role = ROLE_MAP.get(msg.sender, 'user')
        
        context.append({
            "role": gemini_role,
            "parts": [{"text": f"{msg.timestamp} {msg.content}"}]
        })

    # 3. Inject External Data -> order and product details if applicable
    new_user_content = user_message_text
    primary_intent = extract_primary_intent(user_message_text)
    if primary_intent in ('order_status', 'shipping'):
        order_id = extract_order_id(user_message_text)
        if order_id:
            try:
                order = Order.objects.get(pk=int(order_id), customer=session.customer)
            except Order.DoesNotExist:
                order = None
        else:
            order = None
        
        # Create a detailed, factual prompt about the order
        if order:
            order_items = [str(item) for item in order.items.all()]
            order_details_text = (
                f"\nCURRENT ORDER CONTEXT: Order #{order.id}, Status: {order.status}, "
                f"Items: {','.join(order_items)}, Shipping Address: {order.shipping_address}, Order Last Updated: {order.updated_at}. "
                f"The user's query must be answered using this factual context."
            )
            # Prepend facts to the new user message
            new_user_content = order_details_text + "\n---\n" + new_user_content
    else:
        # Extract entities from user message
        entities = extract_entities_from_catalog(user_message_text, get_product_catalog())

        # Start with all active products
        queryset = Product.objects.filter(is_active=True, archived=False)

        # Filter by product names if any
        if entities['products']:
            queryset = queryset.filter(name__in=entities['products'])

        # Filter by brands if any
        if entities['brands']:
            # Use __icontains for case-insensitive match
            brand_filters = queryset.none()
            for brand in entities['brands']:
                brand_filters |= queryset.filter(name__icontains=brand)
            queryset = brand_filters

        # Filter by categories if any
        if entities['categories']:
            queryset = queryset.filter(category__name__in=entities['categories'])

        # Limit the number of results for fallback
        if not queryset.exists():
            queryset = Product.objects.filter(is_active=True, archived=False)[:5]

        products = queryset
              
        if products.exists():
            product_details = []
            for product in products:
                    detail = f"Product Name: {product.name}, SKU: {product.sku}, Description: {product.description}, Price: {product.price}, Stock: {product.stock}."
                    product_details.append(detail)
                
            product_details_text = (
                "CURRENT PRODUCT CONTEXT: " + " ".join(product_details) +
                " The user's query must be answered using this factual context."
            )
            # Prepend facts to the new user message
            new_user_content = product_details_text + "\n---\n" + new_user_content

    context.append({
        "role": "user",
        "parts": [{"text": new_user_content}]
    })

    print(context)
    return context
