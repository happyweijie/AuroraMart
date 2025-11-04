from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL


class AuditLog(models.Model):
    """
    ADM014 – Tracks all admin actions for compliance and debugging.
    """
    ACTION_CHOICES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('archive', 'Archive'),
        ('login', 'Login'),
    ]

    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    entity_type = models.CharField(max_length=100)
    entity_id = models.CharField(max_length=64, blank=True)
    summary = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        actor_name = self.actor.username if self.actor else "System"
        return f"{self.action} {self.entity_type} by {actor_name}"


class DataTransferJob(models.Model):
    """
    ADM006 – Tracks import/export operations for catalogue and customer data.
    """
    JOB_TYPE_CHOICES = [
        ('import', 'Import'),
        ('export', 'Export'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
    ]

    job_type = models.CharField(max_length=10, choices=JOB_TYPE_CHOICES)
    target_model = models.CharField(max_length=100)
    source_file_path = models.CharField(max_length=255, blank=True)
    initiated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='data_jobs')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.job_type} {self.target_model} ({self.status})"


class RecommendationPlacement(models.Model):
    """
    ADM007 & ADM008 – Configure where and how ML recommendations appear.
    """
    PLACEMENT_CHOICES = [
        ('product_detail', 'Product Detail Page'),
        ('cart', 'Cart'),
        ('category', 'Category Listing'),
        ('homepage', 'Homepage'),
    ]
    STRATEGY_CHOICES = [
        ('association_rules', 'Association Rules'),
        ('decision_tree', 'Decision Tree'),
        ('manual', 'Manual'),
    ]

    slug = models.SlugField(max_length=50, unique=True)
    placement = models.CharField(max_length=50, choices=PLACEMENT_CHOICES)
    title = models.CharField(max_length=100)
    strategy = models.CharField(max_length=30, choices=STRATEGY_CHOICES)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['slug']

    def __str__(self):
        return f"{self.slug} ({self.placement})"


class AnalyticsMetric(models.Model):
    """
    ADM009 – Store KPI snapshots for admin analytics dashboard.
    """
    METRIC_CHOICES = [
        ('attach_rate', 'Attach Rate'),
        ('aov', 'Average Order Value'),
        ('low_stock_count', 'Low-Stock Count'),
        ('conversion_rate', 'Conversion Rate'),
    ]

    metric = models.CharField(max_length=50, choices=METRIC_CHOICES)
    value = models.DecimalField(max_digits=12, decimal_places=2)
    captured_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-captured_at']

    def __str__(self):
        return f"{self.metric}: {self.value}"
