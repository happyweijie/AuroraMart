from django.contrib import admin

from .models import (
	AuditLog,
	DataTransferJob,
	RecommendationPlacement,
	AnalyticsMetric,
)


class AuditLogAdmin(admin.ModelAdmin):
	list_display = ("actor", "action", "entity_type", "entity_id", "created_at")
	list_filter = ("action",)
	search_fields = ("actor__username", "entity_type", "summary")
	readonly_fields = ("created_at",)


class DataTransferJobAdmin(admin.ModelAdmin):
	list_display = ("job_type", "target_model", "status", "initiated_by", "created_at")
	list_filter = ("job_type", "status")
	search_fields = ("target_model", "initiated_by__username")
	readonly_fields = ("created_at",)


class RecommendationPlacementAdmin(admin.ModelAdmin):
	list_display = ("slug", "placement", "title", "strategy", "is_active", "updated_at")
	list_filter = ("placement", "strategy", "is_active")
	search_fields = ("slug", "title")


class AnalyticsMetricAdmin(admin.ModelAdmin):
	list_display = ("metric", "value", "captured_at")
	list_filter = ("metric",)
	search_fields = ("metric",)
	readonly_fields = ("captured_at",)


admin.site.register(AuditLog, AuditLogAdmin)
admin.site.register(DataTransferJob, DataTransferJobAdmin)
admin.site.register(RecommendationPlacement, RecommendationPlacementAdmin)
admin.site.register(AnalyticsMetric, AnalyticsMetricAdmin)
