from django.db.models.signals import post_save, pre_save, pre_delete
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
        # Determine whether status changed. If `update_fields` is provided use it,
        # otherwise fall back to the value cached on the instance by `pre_save`.
        update_fields = kwargs.get('update_fields', None)
        status_changed = False
        if update_fields is not None:
            status_changed = 'status' in update_fields
        else:
            status_changed = getattr(instance, '_old_status', None) != getattr(instance, 'status', None)

        if status_changed:
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



@receiver(pre_save, sender=Order)
def cache_order_status(sender, instance, **kwargs):
    """Cache the existing order status on the instance before save so post_save
    can determine whether the status changed when update_fields isn't provided.
    """
    if instance.pk:
        try:
            old = Order.objects.get(pk=instance.pk)
            instance._old_status = old.status
        except Order.DoesNotExist:
            instance._old_status = None


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

