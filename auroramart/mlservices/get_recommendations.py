import joblib
from django.apps import apps
from .predict_preferred_category import APP_PATH

def load_recommendations_rules():
    model_path = APP_PATH / 'mlmodels' / 'b2c_products_500_transactions_50k.joblib'
    
    return joblib.load(model_path)

_PRODUCT_RECOMMENDATIONS = load_recommendations_rules() # load once at startup

def get_recommendations(items, metric='confidence', top_n=5, loaded_rules=_PRODUCT_RECOMMENDATIONS):

    recommendations = set()

    for item in items:

        # Find rules where the item is in the antecedents
        matched_rules = loaded_rules[loaded_rules['antecedents'].apply(lambda x: item in x)]
        # Sort by the specified metric and get the top N
        top_rules = matched_rules.sort_values(by=metric, ascending=False).head(top_n)

        for _, row in top_rules.iterrows():

            recommendations.update(row['consequents'])

    # Remove items that are already in the input list
    recommendations.difference_update(items)
    
    return list(recommendations)[:top_n]
