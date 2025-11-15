from django import template

register = template.Library()

# Mapping of category names/slugs to gradient color schemes
CATEGORY_COLORS = {
    'accessories': 'from-purple-400 to-pink-400',
    'tops': 'from-blue-400 to-cyan-400',
    'outerwear': 'from-gray-500 to-gray-600',
    'footwear': 'from-orange-400 to-red-400',
    'bottoms': 'from-indigo-400 to-purple-400',
    'textbooks': 'from-yellow-400 to-orange-400',
    'fiction': 'from-pink-400 to-rose-400',
    'personal care': 'from-cyan-400 to-blue-400',
    'personal-care': 'from-cyan-400 to-blue-400',
    'makeup': 'from-pink-500 to-rose-500',
    'bedding': 'from-green-400 to-emerald-400',
    'electronics': 'from-blue-500 to-indigo-500',
    'fashion': 'from-purple-500 to-pink-500',
    'home': 'from-amber-400 to-orange-400',
    'home & kitchen': 'from-amber-400 to-orange-400',
    'home-kitchen': 'from-amber-400 to-orange-400',
    'books': 'from-yellow-400 to-amber-400',
    'health': 'from-green-500 to-emerald-500',
    'sports': 'from-red-500 to-orange-500',
    'kitchen': 'from-orange-500 to-red-500',
}

@register.filter
def category_gradient(category):
    """
    Returns a gradient background class for a category.
    Checks both name and slug for matches.
    """
    if not category:
        return 'from-gray-400 to-gray-500'
    
    # Check slug first (lowercase)
    slug = category.slug.lower() if hasattr(category, 'slug') else ''
    if slug in CATEGORY_COLORS:
        return CATEGORY_COLORS[slug]
    
    # Check name (lowercase)
    name = category.name.lower() if hasattr(category, 'name') else ''
    if name in CATEGORY_COLORS:
        return CATEGORY_COLORS[name]
    
    # Check if any part of the name matches
    for key, gradient in CATEGORY_COLORS.items():
        if key in name or key in slug:
            return gradient
    
    # Default gradient
    return 'from-gray-400 to-gray-500'

