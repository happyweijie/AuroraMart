# Recommendation Governance Analysis & Fixes

## Current Status

### ✅ **ACCURATE Placements:**

1. **`homepage_trending`** (Homepage)
   - Strategy: `association_rules` ✅
   - Implementation: Uses `get_product_recommendations()` based on popular products ✅
   - Status: **CORRECT**

2. **`product_detail_also_bought`** (Product Detail Page)
   - Strategy: `association_rules` ✅
   - Implementation: Uses `get_product_recommendations([product.sku])` ✅
   - Status: **CORRECT**

3. **`cart_upsell`** (Cart)
   - Strategy: `association_rules` ✅
   - Implementation: Uses `get_product_recommendations(product_skus)` from cart items ✅
   - Status: **CORRECT**

### ❌ **INACCURATE Placement:**

4. **`category_explore`** (Category Listing)
   - Strategy in seed: `decision_tree` ❌
   - Implementation: Only checks for `association_rules` ❌
   - **ISSUE:** Code will NOT show recommendations because strategy mismatch
   - **FIX NEEDED:** Change strategy to `association_rules` in seed command

## Implementation Details

### What Each Strategy Should Do:

- **`association_rules`**: Uses ML model to find products frequently bought together
  - Implemented via `get_product_recommendations()` function
  - Uses `b2c_products_500_transactions_50k.joblib` model
  - Falls back to category-based recommendations if model unavailable

- **`decision_tree`**: Should use customer's preferred category (from decision tree ML)
  - **NOT YET IMPLEMENTED** in category view
  - Would need to use `customer.preferred_category_fk` to show products from that category

- **`manual`**: Admin-curated recommendations
  - **NOT YET IMPLEMENTED**

## Recommendations

1. **Fix `category_explore` strategy** to `association_rules` (matches current implementation)
2. **Slug column**: Keep it but make it less prominent (it's useful for debugging)
3. **Future enhancement**: Implement `decision_tree` strategy for category pages if needed

