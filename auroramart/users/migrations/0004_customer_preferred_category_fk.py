# Generated migration to add preferred_category_fk column

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('storefront', '0001_initial'),
        ('users', '0003_alter_customer_preferred_category'),
    ]

    operations = [
        migrations.AddField(
            model_name='customer',
            name='preferred_category_fk',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='customers_preferred', to='storefront.category'),
        ),
    ]
