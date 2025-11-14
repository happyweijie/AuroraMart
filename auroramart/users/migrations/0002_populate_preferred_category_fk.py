from django.db import migrations

def populate_preferred_category_fk(apps, schema_editor):
    Customer = apps.get_model('users', 'Customer')
    Category = apps.get_model('storefront', 'Category')

    for c in Customer.objects.all():
        if c.preferred_category:
            try:
                category_obj = Category.objects.get(name=c.preferred_category)
                c.preferred_category_fk = category_obj
                c.save()
            except Category.DoesNotExist:
                # If the ML-generated string doesn't match any category, skip
                pass

class Migration(migrations.Migration):

    dependencies = [
        ('storefront', '0001_initial'),  # adjust to your latest storefront migration
        ('users', '0001_initial'),  # replace with your latest users migration
    ]

    operations = [
        migrations.RunPython(populate_preferred_category_fk),
    ]
