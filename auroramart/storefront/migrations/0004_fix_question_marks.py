from django.db import migrations

def replace_question_marks(apps, schema_editor):
    Category = apps.get_model('storefront', 'Category')
    Product = apps.get_model('storefront', 'Product')

    for model, fields in ((Category, ('name','description')), (Product, ('name','description'))):
        qs = model.objects.all()
        for obj in qs:
            changed = False
            for field in fields:
                val = getattr(obj, field, None)
                if val and '?' in val:
                    setattr(obj, field, val.replace('?', '-'))
                    changed = True
            if changed:
                # Only save the fields we changed
                obj.save()

class Migration(migrations.Migration):
    dependencies = [
        ('storefront', '0003_remove_promotion_preferred_category'),
    ]

    operations = [
        migrations.RunPython(replace_question_marks, reverse_code=migrations.RunPython.noop),
    ]
