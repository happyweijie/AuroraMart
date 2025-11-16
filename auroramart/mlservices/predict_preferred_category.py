import pandas as pd
import joblib
from pathlib import Path
from django.apps import apps
from users.models import Customer
from storefront.models import Category
from threading import Lock

_CATEGORY_PREDICTION = None
_load_lock = Lock()

def load_category_prediction_model():
    """Load model lazily on first access."""
    global _CATEGORY_PREDICTION
    
    if _CATEGORY_PREDICTION is None:
        with _load_lock:  # Prevent double loading under concurrency
            if _CATEGORY_PREDICTION is None:
                app_path = Path(apps.get_app_config('admin_panel').path)
                model_path = app_path / 'mlmodels' / 'b2c_customers_100.joblib'
                
                _CATEGORY_PREDICTION = joblib.load(model_path)
    
    return _CATEGORY_PREDICTION

def predict_preferred_category(customer_data: dict):

    columns = {
        'age':'int64', 'household_size':'int64', 'has_children':'int64', 'monthly_income_sgd':'float64',
        'gender_Female':'bool', 'gender_Male':'bool', 'employment_status_Full-time':'bool',
        'employment_status_Part-time':'bool', 'employment_status_Retired':'bool',
        'employment_status_Self-employed':'bool', 'employment_status_Student':'bool',
        'occupation_Admin':'bool', 'occupation_Education':'bool', 'occupation_Sales':'bool',
        'occupation_Service':'bool', 'occupation_Skilled Trades':'bool', 'occupation_Tech':'bool',
        'education_Bachelor':'bool', 'education_Diploma':'bool', 'education_Doctorate':'bool',
        'education_Master':'bool', 'education_Secondary':'bool'
    }

    df = pd.DataFrame({col: pd.Series(dtype=dtype) for col, dtype in columns.items()})
    customer_df = pd.DataFrame([customer_data])
    customer_encoded = pd.get_dummies(customer_df, columns=['gender', 'employment_status', 'occupation', 'education'])    

    for col in df.columns:

        if col not in customer_encoded.columns:

            # Use False for bool columns, 0 for numeric
            if df[col].dtype == bool:
                df[col] = False
            else:
                df[col] = 0
        
        else:

            df[col] = customer_encoded[col]
    
    # load model lazily
    if not _CATEGORY_PREDICTION:
        load_category_prediction_model()

    # Now input_encoded can be used for prediction
    prediction = _CATEGORY_PREDICTION.predict(df)    

    return prediction[0]

def get_preferred_category(customer: Customer):
    customer_data = {
                'age': customer.age,
                'household_size': customer.household_size,
                'has_children': int(customer.has_children),
                'monthly_income_sgd': float(customer.monthly_income_sgd),
                'gender': customer.gender,
                'employment_status': customer.employment_status,
                'occupation': customer.occupation,
                'education': customer.education
            }
    
    preferred_category = predict_preferred_category(customer_data)
    try:
        preferred_category_fk = Category.objects.get(name=preferred_category)
    except Category.DoesNotExist:
        preferred_category_fk = None 

    return preferred_category, preferred_category_fk
