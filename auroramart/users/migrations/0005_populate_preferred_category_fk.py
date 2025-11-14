# Generated migration to populate preferred_category_fk from preferred_category

from django.db import migrations


def forward_populate_preferred_category_fk(apps, schema_editor):
    Customer = apps.get_model('users', 'Customer')
    Category = apps.get_model('storefront', 'Category')

    for cust in Customer.objects.all():
        pref = getattr(cust, 'preferred_category', None)
        if pref:
            try:
                cat = Category.objects.filter(name=pref).first()
                if cat:
                    cust.preferred_category_fk = cat
                    cust.save(update_fields=['preferred_category_fk'])
            except Exception:
                # Skip on any lookup/save errors to avoid blocking migration
                continue


def reverse_clear_preferred_category_fk(apps, schema_editor):
    Customer = apps.get_model('users', 'Customer')
    for cust in Customer.objects.all():
        if getattr(cust, 'preferred_category_fk', None) is not None:
            cust.preferred_category_fk = None
            cust.save(update_fields=['preferred_category_fk'])


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_customer_preferred_category_fk'),
    ]

    operations = [
        migrations.RunPython(forward_populate_preferred_category_fk, reverse_clear_preferred_category_fk),
    ]
