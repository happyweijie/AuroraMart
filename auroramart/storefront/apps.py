from django.apps import AppConfig


class StorefrontConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'storefront'

    def ready(self):
        import storefront.signals  # Ensure signals are imported and registered
