from django import template

register = template.Library()

# Mapping of category names/slugs to Lucide icon names
CATEGORY_ICONS = {
    'accessories': 'watch',
    'tops': 'shirt',
    'outerwear': 'shirt',  # Using shirt as outerwear icon
    'footwear': 'shoe',  # Using shoe icon for footwear
    'bottoms': 'shirt',
    'textbooks': 'book-open',
    'fiction': 'book',
    'personal care': 'sparkles',
    'personal-care': 'sparkles',
    'makeup': 'palette',
    'bedding': 'bed',
    'electronics': 'smartphone',
    'fashion': 'shirt',
    'home': 'home',
    'home & kitchen': 'home',
    'home-kitchen': 'home',
    'books': 'book-open',
    'health': 'heart-pulse',
    'sports': 'dumbbell',
    'kitchen': 'chef-hat',
}

@register.filter
def category_icon(category):
    """
    Returns the appropriate Lucide icon name for a category.
    Checks both name and slug for matches.
    """
    if not category:
        return 'package'
    
    # Check slug first (lowercase)
    slug = category.slug.lower() if hasattr(category, 'slug') else ''
    if slug in CATEGORY_ICONS:
        return CATEGORY_ICONS[slug]
    
    # Check name (lowercase)
    name = category.name.lower() if hasattr(category, 'name') else ''
    if name in CATEGORY_ICONS:
        return CATEGORY_ICONS[name]
    
    # Check if any part of the name matches
    for key, icon in CATEGORY_ICONS.items():
        if key in name or key in slug:
            return icon
    
    # Default icon
    return 'package'

