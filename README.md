# AuroraMart – Personalised E-commerce Platform

AuroraMart is a full-stack B2C e-commerce web application built with **Python**, **Django**, and integrated **machine learning models**.  
It was developed as part of the IS2108 (Full-stack Software Engineering for AI Solutions I) pair project.

---

## 🚀 Project Objectives

AuroraMart aims to validate a core business hypothesis:

> **Win the first session. Keep the second.**  
> Deliver hyper-relevant products within 90 seconds and encourage return visits within 14–21 days.

To achieve this, the application integrates:

- A **cold-start personalisation model** (Decision Tree)
- **Association rule–based recommendations**
- A clean, maintainable Django architecture
- A functional admin + storefront experience

---

## ✨ Features

### 🎛 Admin Panel
- Manage the product catalogue (500 SKUs)  
- Update stock and inventory  
- Maintain customer profiles  
- Predict new users’ preferred categories using ML  

### 🛒 Customer Storefront
- Browse curated categories & subcategories  
- View product details with ratings, stock, and pricing  
- Add items to cart and update quantities  
- AI-powered recommendations:  
  - **Frequently Bought Together**  
  - **Complete the Set** (cart suggestions)  
  - **Next Best Action** (category-page nudges)  

### 🤖 AI Integration

#### Cold-Start Personalisation
- Inputs: demographics (age, gender, income range, etc.)  
- Output: predicted preferred product category  
- Redirects new users to a personalised landing page  

#### Association Rules
- Derived from 50,000 historical transactions  
- Provides context-aware cross-sell and upsell suggestions  

---

## 📦 Tech Stack

**Backend:**  
- Python 3.x  
- Django  
- SQLite (default)

**Machine Learning:**  
- joblib  
- scikit-learn  
- Apriori/association rules (pre-computed)

**Frontend:**  
- HTML, CSS, JavaScript  
- Django templates  

---