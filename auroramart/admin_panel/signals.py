from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from storefront.models import Product, Order
from users.models import Customer
from .models import AuditLog

User = get_user_model()


@receiver(post_save, sender=Product)
def log_product_save(sender, instance, created, **kwargs):
    """Log product create/update"""
    action = 'create' if created else 'update'
    actor = None
    
    # Try to get the current user from thread-local storage
    # This is a simplified approach - in production, you might want to use middleware
    from django.contrib.auth.signals import user_logged_in
    try:
        import threading
        thread_locals = threading.local()
        if hasattr(thread_locals, 'user'):
            actor = thread_locals.user
    except:
        pass
    
    AuditLog.objects.create(
        actor=actor,
        action=action,
        entity_type='Product',
        entity_id=str(instance.sku),
        summary=f'{action.capitalize()}d product: {instance.name}'
    )


@receiver(pre_delete, sender=Product)
def log_product_delete(sender, instance, **kwargs):
    """Log product deletion"""
    actor = None
    try:
        import threading
        thread_locals = threading.local()
        if hasattr(thread_locals, 'user'):
            actor = thread_locals.user
    except:
        pass
    
    AuditLog.objects.create(
        actor=actor,
        action='delete',
        entity_type='Product',
        entity_id=str(instance.sku),
        summary=f'Deleted product: {instance.name}'
    )


@receiver(post_save, sender=Order)
def log_order_status_change(sender, instance, created, **kwargs):
    """Log order status changes"""
    if not created:
        # Only log status changes, not creation
        # Check if status actually changed
        if 'update_fields' in kwargs and 'status' in kwargs['update_fields']:
            actor = None
            try:
                import threading
                thread_locals = threading.local()
                if hasattr(thread_locals, 'user'):
                    actor = thread_locals.user
            except:
                pass
            
            AuditLog.objects.create(
                actor=actor,
                action='update',
                entity_type='Order',
                entity_id=str(instance.id),
                summary=f'Order #{instance.id} status changed to {instance.get_status_display()}'
            )


@receiver(post_save, sender=Customer)
def log_customer_update(sender, instance, created, **kwargs):
    """Log customer demographic updates"""
    if not created:
        # Only log updates, not creation
        actor = None
        try:
            import threading
            thread_locals = threading.local()
            if hasattr(thread_locals, 'user'):
                actor = thread_locals.user
        except:
            pass
        
        AuditLog.objects.create(
            actor=actor,
            action='update',
            entity_type='Customer',
            entity_id=str(instance.id),
            summary=f'Updated customer: {instance.user.username}'
        )

